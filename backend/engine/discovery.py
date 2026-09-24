import socket
import subprocess
import concurrent.futures
import platform
import os
import re
from typing import List, Dict, Any

def get_local_subnet_prefix() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        parts = ip.split('.')
        return f"{parts[0]}.{parts[1]}.{parts[2]}"
    except Exception:
        return "192.168.1"

def scan_network_printers(subnet_prefix: str = None) -> List[Dict[str, Any]]:
    """Scan local subnet for network printers with open IPP/RAW/LPD ports (631, 9100, 515)."""
    if not subnet_prefix:
        subnet_prefix = get_local_subnet_prefix()

    discovered = []

    def probe_ip(ip: str):
        # Quick port check for 631 (IPP), 9100 (RAW JetDirect), 515 (LPD)
        for port in [631, 9100, 515]:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.35)
                if s.connect_ex((ip, port)) == 0:
                    s.close()
                    return ip, port
                s.close()
            except:
                pass
        return None, None

    ips = [f"{subnet_prefix}.{i}" for i in range(1, 255)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=60) as ex:
        results = list(ex.map(probe_ip, ips))

    for ip, port in results:
        if ip:
            if port == 631:
                ptype = "IPP / AirPrint (Wi-Fi/Ağ)"
                uri = f"ipp://{ip}:631/ipp/print"
            elif port == 9100:
                ptype = "RAW JetDirect (Port 9100)"
                uri = f"socket://{ip}:9100"
            else:
                ptype = "LPD Ağ Yazıcısı"
                uri = f"lpd://{ip}/queue"

            discovered.append({
                "ip": ip,
                "port": port,
                "name": f"Ağ_Yazıcısı_{ip.replace('.', '_')}",
                "display_name": f"Ağ Yazıcısı ({ip}:{port})",
                "type": ptype,
                "device_type": "network",
                "uri": uri,
                "icon": "fa-solid fa-wifi"
            })

    # Also try ippfind on Linux/macOS
    if platform.system().lower() != 'windows':
        try:
            res_ipp = subprocess.run(['ippfind'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
            for line in res_ipp.stdout.splitlines():
                uri = line.strip()
                if uri and not any(d['uri'] == uri for d in discovered):
                    m = re.search(r'ipp://([^.]+)', uri)
                    raw_name = m.group(1) if m else "Bonjour_IPP_Printer"
                    clean_name = raw_name.replace("%20", " ")
                    discovered.append({
                        "ip": "mDNS",
                        "port": 631,
                        "name": raw_name,
                        "display_name": f"{clean_name} (AirPrint/IPP)",
                        "type": "Apple AirPrint / IPP (Wi-Fi)",
                        "device_type": "network",
                        "uri": uri,
                        "icon": "fa-solid fa-wifi"
                    })
        except Exception:
            pass

    return discovered

def scan_usb_hardware() -> List[Dict[str, Any]]:
    """Scan for connected USB printers."""
    usb_devices = []
    is_windows = platform.system().lower() == 'windows'

    if not is_windows:
        # 1. lpinfo -v for direct USB
        try:
            res = subprocess.run(['lpinfo', '-v'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=4)
            for line in res.stdout.splitlines():
                line = line.strip()
                if line.startswith('direct usb://') or 'usb://' in line:
                    uri = line.split(maxsplit=1)[-1]
                    m = re.search(r'usb://([^/?]+)', uri)
                    raw_name = m.group(1) if m else "USB_Printer"
                    usb_devices.append({
                        "name": raw_name.replace('%20', '_'),
                        "display_name": raw_name.replace('%20', ' ').replace('_', ' '),
                        "uri": uri,
                        "type": "USB / Kablolu Bağlantı",
                        "device_type": "usb",
                        "icon": "fa-solid fa-plug"
                    })
        except Exception:
            pass

        # 2. Raw device nodes
        for i in range(4):
            dev = f"/dev/usb/lp{i}"
            if os.path.exists(dev):
                usb_devices.append({
                    "name": f"USB_Port_lp{i}",
                    "display_name": f"USB Port {i} (/dev/usb/lp{i})",
                    "uri": f"file://{dev}",
                    "type": "USB Doğrudan Kablo Portu",
                    "device_type": "usb",
                    "icon": "fa-solid fa-plug"
                })
    else:
        # Windows PnP USB Printers
        try:
            ps_cmd = 'Get-PnpDevice -Class "Printer", "USB" -Status OK | Select-Object FriendlyName, InstanceId | ConvertTo-Json'
            res = subprocess.run(['powershell', '-NoProfile', '-Command', ps_cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            import json
            if res.stdout.strip():
                data = json.loads(res.stdout)
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    fname = item.get('FriendlyName', '')
                    if fname and any(kw in fname.lower() for kw in ['printer', 'usb', 'laser', 'deskjet', 'pos', 'dcp']):
                        usb_devices.append({
                            "name": fname,
                            "display_name": fname,
                            "uri": item.get('InstanceId', ''),
                            "type": "Windows USB Kablolu Aygıt",
                            "device_type": "usb",
                            "icon": "fa-solid fa-plug"
                        })
        except Exception:
            pass

    return usb_devices

def scan_all_devices() -> Dict[str, Any]:
    """Combines USB & Network scanner."""
    return {
        "usb_printers": scan_usb_hardware(),
        "network_printers": scan_network_printers()
    }
