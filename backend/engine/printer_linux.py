import subprocess
import shutil
import time
import re
import os
from typing import List, Dict, Any, Optional
from .printer_base import BasePrinterEngine

class LinuxPrinterEngine(BasePrinterEngine):
    def __init__(self):
        self._ensure_cups_running()

    def _ensure_cups_running(self):
        try:
            subprocess.run(['systemctl', 'is-active', '--quiet', 'cups'], check=False)
        except Exception:
            pass

    def _get_printer_device_uris(self) -> Dict[str, str]:
        """Fetch device URI for each configured printer via lpstat -v."""
        uris = {}
        try:
            res = subprocess.run(['lpstat', '-v'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5, env={'LC_ALL': 'C', 'PATH': '/usr/bin:/bin:/usr/sbin:/sbin'})
            for line in res.stdout.splitlines():
                # Format: device for DCP-T520W: ipp://Brother%20DCP-T520W._ipp._tcp.local/
                m = re.match(r'device\s+for\s+([^:]+):\s+(.+)', line.strip(), re.IGNORECASE)
                if m:
                    p_name = m.group(1).strip()
                    p_uri = m.group(2).strip()
                    uris[p_name] = p_uri
        except Exception as e:
            print(f"[LinuxEngine] lpstat -v error: {e}")
        return uris

    def _classify_connection(self, name: str, uri: str) -> Dict[str, str]:
        """Classify printer connection type into USB/Kablolu, Wi-Fi/Ağ, or Sanal/PDF."""
        uri_lower = uri.lower()
        name_lower = name.lower()

        if uri_lower.startswith('usb:') or 'usb' in uri_lower or uri_lower.startswith('parallel:') or uri_lower.startswith('serial:') or '/dev/usb/lp' in uri_lower:
            return {
                "connection_type": "USB / Kablolu",
                "device_type": "usb",
                "badge_color": "blue",
                "icon": "fa-solid fa-plug"
            }
        elif uri_lower.startswith(('ipp:', 'ipps:', 'dnssd:', 'socket:', 'http:', 'https:', 'lpd:', 'smb:', 'beh:')) or '._tcp.local' in uri_lower:
            return {
                "connection_type": "Wi-Fi / Ağ",
                "device_type": "network",
                "badge_color": "indigo",
                "icon": "fa-solid fa-wifi"
            }
        elif uri_lower.startswith(('cups-pdf:', 'file:')) or 'pdf' in name_lower:
            return {
                "connection_type": "Sanal / PDF",
                "device_type": "virtual",
                "badge_color": "slate",
                "icon": "fa-solid fa-file-pdf"
            }
        else:
            return {
                "connection_type": "Yerel / Yazıcı",
                "device_type": "local",
                "badge_color": "emerald",
                "icon": "fa-solid fa-print"
            }

    def list_printers(self) -> List[Dict[str, Any]]:
        printers_dict = {}
        default_printer = ""
        device_uris = self._get_printer_device_uris()

        # Strategy 1: lpstat -p -d
        try:
            res = subprocess.run(['lpstat', '-p', '-d'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5, env={'LC_ALL': 'C', 'PATH': '/usr/bin:/bin:/usr/sbin:/sbin'})
            for line in res.stdout.splitlines():
                line_str = line.strip()
                if "system default destination:" in line_str.lower():
                    default_printer = line_str.split(":")[-1].strip()

                if line_str.lower().startswith("printer "):
                    parts = line_str.split()
                    if len(parts) > 1:
                        p_name = parts[1]
                        is_idle = "idle" in line_str.lower()
                        state = "ready" if is_idle else ("busy" if "printing" in line_str.lower() or "processing" in line_str.lower() else "paused")
                        
                        uri = device_uris.get(p_name, "")
                        conn_info = self._classify_connection(p_name, uri)

                        printers_dict[p_name] = {
                            "name": p_name,
                            "display_name": p_name.replace("_", " "),
                            "is_default": False,
                            "state": state,
                            "status_text": "Hazır" if is_idle else ("Yazdırılıyor" if state == "busy" else "Duraklatıldı"),
                            "uri": uri,
                            "connection_type": conn_info["connection_type"],
                            "device_type": conn_info["device_type"],
                            "badge_color": conn_info["badge_color"],
                            "icon": conn_info["icon"]
                        }
        except Exception as e:
            print(f"[LinuxEngine] lpstat -p -d error: {e}")

        # Strategy 2: lpstat -e (lists all destination names)
        try:
            res_e = subprocess.run(['lpstat', '-e'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            for line in res_e.stdout.splitlines():
                p_name = line.strip()
                if p_name and p_name not in printers_dict:
                    uri = device_uris.get(p_name, "")
                    conn_info = self._classify_connection(p_name, uri)
                    printers_dict[p_name] = {
                        "name": p_name,
                        "display_name": p_name.replace("_", " "),
                        "is_default": False,
                        "state": "ready",
                        "status_text": "Hazır",
                        "uri": uri,
                        "connection_type": conn_info["connection_type"],
                        "device_type": conn_info["device_type"],
                        "badge_color": conn_info["badge_color"],
                        "icon": conn_info["icon"]
                    }
        except Exception:
            pass

        # Strategy 3: lpstat -a
        try:
            res_a = subprocess.run(['lpstat', '-a'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            for line in res_a.stdout.splitlines():
                if line.strip():
                    parts = line.strip().split()
                    p_name = parts[0]
                    if p_name not in printers_dict:
                        uri = device_uris.get(p_name, "")
                        conn_info = self._classify_connection(p_name, uri)
                        printers_dict[p_name] = {
                            "name": p_name,
                            "display_name": p_name.replace("_", " "),
                            "is_default": False,
                            "state": "ready",
                            "status_text": "Hazır",
                            "uri": uri,
                            "connection_type": conn_info["connection_type"],
                            "device_type": conn_info["device_type"],
                            "badge_color": conn_info["badge_color"],
                            "icon": conn_info["icon"]
                        }
        except Exception:
            pass

        # Strategy 4: IPP / ippfind auto-detection for unconfigured network printers
        if not printers_dict:
            try:
                res_ipp = subprocess.run(['ippfind'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
                for line in res_ipp.stdout.splitlines():
                    uri = line.strip()
                    if uri:
                        match = re.search(r'ipp://([^.]+)', uri)
                        p_name = match.group(1) if match else "Network_Printer"
                        conn_info = self._classify_connection(p_name, uri)
                        printers_dict[p_name] = {
                            "name": p_name,
                            "display_name": p_name.replace("_", " "),
                            "is_default": True,
                            "state": "ready",
                            "status_text": "Hazır (Ağ Yazıcısı)",
                            "uri": uri,
                            "connection_type": conn_info["connection_type"],
                            "device_type": conn_info["device_type"],
                            "badge_color": conn_info["badge_color"],
                            "icon": conn_info["icon"]
                        }
            except Exception:
                pass

        # Mark default
        if default_printer and default_printer in printers_dict:
            printers_dict[default_printer]["is_default"] = True
        elif printers_dict:
            first_key = list(printers_dict.keys())[0]
            printers_dict[first_key]["is_default"] = True

        return list(printers_dict.values())

    def scan_unconfigured_hardware(self) -> List[Dict[str, Any]]:
        """Scan for connected USB and Network printers that might not yet be in CUPS."""
        found = []
        configured_uris = set(self._get_printer_device_uris().values())

        # 1. Scan USB & direct devices via lpinfo -v
        try:
            res_info = subprocess.run(['lpinfo', '-v'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            for line in res_info.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = line.split(maxsplit=1)
                if len(parts) == 2:
                    kind, uri = parts[0], parts[1]
                    if kind in ['direct', 'network'] and uri not in configured_uris:
                        if uri.startswith(('usb://', 'parallel://', 'serial://', 'socket://', 'ipp://', 'dnssd://')):
                            # Parse a user-friendly name from URI
                            raw_name = uri.split('://')[-1].split('?')[0].replace('/', '_').replace('%20', ' ')
                            is_usb = 'usb' in uri.lower() or kind == 'direct'
                            found.append({
                                "uri": uri,
                                "name": raw_name,
                                "type": "USB / Kablolu" if is_usb else "Wi-Fi / Ağ",
                                "device_type": "usb" if is_usb else "network",
                                "icon": "fa-solid fa-plug" if is_usb else "fa-solid fa-wifi",
                                "configured": False
                            })
        except Exception:
            pass

        # 2. Scan Linux raw USB character devices (/dev/usb/lp*)
        for i in range(4):
            dev_path = f"/dev/usb/lp{i}"
            if os.path.exists(dev_path):
                found.append({
                    "uri": f"file://{dev_path}",
                    "name": f"USB_Direct_Port_{i}",
                    "type": "USB / Kablolu (Doğrudan Port)",
                    "device_type": "usb",
                    "icon": "fa-solid fa-plug",
                    "configured": False
                })

        return found

    def auto_add_printer(self, name: str, uri: str) -> Dict[str, Any]:
        """Automatically create a CUPS queue for a USB or Network printer without manual drivers."""
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name).strip('_')
        try:
            # lpadmin -p <name> -E -v <uri> -m everywhere
            cmd = ['lpadmin', '-p', safe_name, '-E', '-v', uri, '-m', 'everywhere']
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
            if res.returncode == 0:
                # Set as accepting and enable
                subprocess.run(['cupsenable', safe_name], check=False)
                subprocess.run(['cupsaccept', safe_name], check=False)
                return {"success": True, "message": f"{safe_name} başarıyla sisteme eklendi ve hazır."}
            else:
                # Fallback to generic raw
                cmd_raw = ['lpadmin', '-p', safe_name, '-E', '-v', uri]
                res_raw = subprocess.run(cmd_raw, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
                if res_raw.returncode == 0:
                    subprocess.run(['cupsenable', safe_name], check=False)
                    subprocess.run(['cupsaccept', safe_name], check=False)
                    return {"success": True, "message": f"{safe_name} genel yazıcı olarak eklendi."}
                return {"success": False, "message": f"Yazıcı eklenemedi: {res.stderr}"}
        except Exception as e:
            return {"success": False, "message": f"Hata: {str(e)}"}

    def get_printer_status(self, printer_name: str) -> Dict[str, Any]:
        try:
            res = subprocess.run(['lpstat', '-p', printer_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5, env={'LC_ALL': 'C', 'PATH': '/usr/bin:/bin:/usr/sbin:/sbin'})
            out = res.stdout.strip()
            if "idle" in out.lower() or not out:
                state = "ready"
                status = "Hazır"
            elif "processing" in out.lower() or "printing" in out.lower():
                state = "busy"
                status = "Yazdırılıyor..."
            elif "disabled" in out.lower():
                state = "paused"
                status = "Duraklatıldı"
            else:
                state = "ready"
                status = "Hazır"

            # Query options/media
            options_text = ""
            try:
                opts_res = subprocess.run(['lpoptions', '-p', printer_name, '-l'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
                options_text = opts_res.stdout
            except Exception:
                pass

            device_uris = self._get_printer_device_uris()
            uri = device_uris.get(printer_name, "")
            conn_info = self._classify_connection(printer_name, uri)

            return {
                "name": printer_name,
                "display_name": printer_name.replace("_", " "),
                "state": state,
                "status": status,
                "raw": out,
                "uri": uri,
                "connection_type": conn_info["connection_type"],
                "device_type": conn_info["device_type"],
                "supports_color": "ColorModel" in options_text or "RGB" in options_text or True,
                "supports_duplex": "Duplex" in options_text or "Sides" in options_text
            }
        except Exception as e:
            return {
                "name": printer_name,
                "display_name": printer_name.replace("_", " "),
                "state": "ready",
                "status": "Hazır",
                "raw": str(e),
                "connection_type": "Bilinmeyen",
                "supports_color": True,
                "supports_duplex": False
            }

    def print_file(self, printer_name: str, file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        copies = int(options.get('copies', 1))
        color_mode = options.get('color_mode', 'RGB')
        page_size = options.get('page_size', 'A4')
        media_type = options.get('media_type', 'Stationery')
        orientation = options.get('orientation', 'portrait')
        quality = options.get('quality', 'Normal')
        scaling = options.get('scaling', 'fit')
        page_ranges = options.get('page_ranges', '').strip()
        duplex = options.get('duplex', 'None')

        # Map paper sizes to CUPS standards
        size_map = {
            'A4': 'A4',
            'A3': 'A3',
            'A5': 'A5',
            'Letter': 'Letter',
            'Legal': 'Legal',
            'Photo_10x15': '4x6',
            'Photo_4x6': '4x6',
            'B5': 'ISOB5',
            'Receipt_80mm': 'Custom.80x297mm',
            'Receipt_58mm': 'Custom.58x297mm'
        }
        cups_page_size = size_map.get(page_size, page_size)

        lp_cmd = [
            'lp',
            '-d', printer_name,
            '-n', str(copies),
            '-o', f'ColorModel={color_mode}',
            '-o', f'PageSize={cups_page_size}',
            '-o', f'MediaType={media_type}',
            '-o', f'cupsPrintQuality={quality}',
            '-o', f'print-scaling={scaling}'
        ]

        if orientation == 'landscape':
            lp_cmd.extend(['-o', 'orientation-requested=4'])
        else:
            lp_cmd.extend(['-o', 'orientation-requested=3'])

        if duplex in ['TwoSidedLongEdge', 'TwoSidedShortEdge']:
            lp_cmd.extend(['-o', f'sides={duplex}'])

        if page_ranges:
            lp_cmd.extend(['-o', f'page-ranges={page_ranges}'])

        lp_cmd.append(file_path)

        try:
            res = subprocess.run(lp_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True, timeout=15)
            out_msg = res.stdout.strip()
            job_id = out_msg.split(' ')[-2] if 'request id is' in out_msg else f"job-{int(time.time())}"
            return {
                "success": True,
                "job_id": job_id,
                "message": f"Belge {printer_name} yazıcısına başarıyla gönderildi.",
                "raw": out_msg
            }
        except subprocess.CalledProcessError as e:
            # Fallback direct raw print
            try:
                raw_res = subprocess.run(['lpr', '-P', printer_name, file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
                if raw_res.returncode == 0:
                    return {"success": True, "job_id": f"job-{int(time.time())}", "message": "Belge yazıcıya iletildi."}
            except Exception:
                pass
            err = e.stderr.strip() or e.stdout.strip()
            return {"success": False, "message": f"Yazdırma Hatası: {err}"}
        except Exception as e:
            return {"success": False, "message": f"Hata: {str(e)}"}

    def get_jobs(self, printer_name: Optional[str] = None) -> List[Dict[str, Any]]:
        jobs = []
        try:
            cmd = ['lpstat', '-o']
            if printer_name:
                cmd.append(printer_name)
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            for line in res.stdout.splitlines():
                if line.strip():
                    parts = line.split()
                    job_id = parts[0]
                    user = parts[1] if len(parts) > 1 else ""
                    size = parts[2] if len(parts) > 2 else ""
                    jobs.append({
                        "id": job_id,
                        "user": user,
                        "size": size,
                        "raw": line
                    })
        except Exception:
            pass
        return jobs

    def cancel_job(self, job_id: str) -> bool:
        try:
            res = subprocess.run(['cancel', job_id], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            return res.returncode == 0
        except Exception:
            return False
