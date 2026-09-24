import os
import subprocess
import time
import json
from typing import List, Dict, Any, Optional
from .printer_base import BasePrinterEngine

class WindowsPrinterEngine(BasePrinterEngine):
    def __init__(self):
        pass

    def _classify_windows_printer(self, name: str, port_name: str, driver_name: str) -> Dict[str, str]:
        p_name = (name or "").lower()
        port = (port_name or "").lower()
        driver = (driver_name or "").lower()

        if any(usb_kw in port for usb_kw in ['usb', 'dot4', 'lpt', 'com']) or 'usb' in driver:
            return {
                "connection_type": "USB / Kablolu",
                "device_type": "usb",
                "badge_color": "blue",
                "icon": "fa-solid fa-plug"
            }
        elif any(net_kw in port for net_kw in ['ip_', 'wsd', 'tcp', '192.', '10.', '172.', '\\\\']) or 'network' in port:
            return {
                "connection_type": "Wi-Fi / Ağ",
                "device_type": "network",
                "badge_color": "indigo",
                "icon": "fa-solid fa-wifi"
            }
        elif any(virt_kw in p_name for virt_kw in ['pdf', 'xps', 'onenote', 'fax', 'cute', 'foxit']) or 'portprompt' in port:
            return {
                "connection_type": "Sanal / PDF",
                "device_type": "virtual",
                "badge_color": "slate",
                "icon": "fa-solid fa-file-pdf"
            }
        else:
            return {
                "connection_type": "Kablolu / Yerel",
                "device_type": "local",
                "badge_color": "emerald",
                "icon": "fa-solid fa-print"
            }

    def list_printers(self) -> List[Dict[str, Any]]:
        printers = []
        try:
            # Use PowerShell Get-Printer with PortName and DriverName
            ps_cmd = 'Get-Printer | Select-Object Name, Type, PrinterStatus, Default, PortName, DriverName | ConvertTo-Json'
            res = subprocess.run(['powershell', '-NoProfile', '-Command', ps_cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=8)
            if res.stdout.strip():
                data = json.loads(res.stdout)
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    name = item.get('Name', 'Bilinmeyen')
                    is_def = bool(item.get('Default', False))
                    status_code = item.get('PrinterStatus', 3)
                    port_name = item.get('PortName', '')
                    driver_name = item.get('DriverName', '')
                    state = "ready" if status_code == 3 else ("busy" if status_code == 4 else "offline")
                    
                    conn_info = self._classify_windows_printer(name, port_name, driver_name)

                    printers.append({
                        "name": name,
                        "display_name": name,
                        "is_default": is_def,
                        "state": state,
                        "status_text": "Hazır" if state == "ready" else "Meşgul/Çevrimdışı",
                        "port": port_name,
                        "connection_type": conn_info["connection_type"],
                        "device_type": conn_info["device_type"],
                        "badge_color": conn_info["badge_color"],
                        "icon": conn_info["icon"]
                    })
        except Exception as e:
            print(f"[WindowsEngine] list_printers error: {e}")
        return printers

    def scan_unconfigured_hardware(self) -> List[Dict[str, Any]]:
        """Scan unconfigured USB / PNP devices in Windows."""
        found = []
        try:
            ps_cmd = 'Get-PnpDevice -Class "Printer", "PrintQueue", "USB" -Status OK | Select-Object FriendlyName, InstanceId | ConvertTo-Json'
            res = subprocess.run(['powershell', '-NoProfile', '-Command', ps_cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=8)
            if res.stdout.strip():
                data = json.loads(res.stdout)
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    name = item.get('FriendlyName', '')
                    if name and ('print' in name.lower() or 'usb' in name.lower() or 'dcp' in name.lower() or 'laser' in name.lower()):
                        found.append({
                            "name": name,
                            "uri": item.get('InstanceId', ''),
                            "type": "USB / Kablolu Cihaz",
                            "device_type": "usb",
                            "icon": "fa-solid fa-plug",
                            "configured": True
                        })
        except Exception:
            pass
        return found

    def get_printer_status(self, printer_name: str) -> Dict[str, Any]:
        try:
            ps_cmd = f'Get-Printer -Name "{printer_name}" | Select-Object Name, PrinterStatus, JobCount, PortName, DriverName | ConvertTo-Json'
            res = subprocess.run(['powershell', '-NoProfile', '-Command', ps_cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            if res.stdout.strip():
                data = json.loads(res.stdout)
                port_name = data.get('PortName', '')
                driver_name = data.get('DriverName', '')
                conn_info = self._classify_windows_printer(printer_name, port_name, driver_name)
                return {
                    "name": printer_name,
                    "state": "ready",
                    "status": "Hazır (Windows)",
                    "job_count": data.get('JobCount', 0),
                    "connection_type": conn_info["connection_type"],
                    "device_type": conn_info["device_type"],
                    "supports_color": True,
                    "supports_duplex": True
                }
        except Exception:
            pass
        return {
            "name": printer_name,
            "state": "ready",
            "status": "Windows Yazıcı Hazır",
            "connection_type": "Kablolu / Yerel",
            "supports_color": True,
            "supports_duplex": True
        }

    def print_file(self, printer_name: str, file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        abs_path = os.path.abspath(file_path).replace('/', '\\')
        copies = int(options.get('copies', 1))

        # Check if PDFtoPrinter or SumatraPDF exists for precise multi-copy & duplex
        try:
            # Standard Windows Shell PrintTo execution
            for _ in range(copies):
                ps_cmd = f'Start-Process -FilePath "{abs_path}" -Verb PrintTo -ArgumentList "\"{printer_name}\"" -PassThru | Wait-Process'
                subprocess.run(['powershell', '-NoProfile', '-Command', ps_cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20)
            
            return {
                "success": True,
                "job_id": f"win-{int(time.time())}",
                "message": f"Belge {printer_name} yazıcısına gönderildi."
            }
        except Exception as e:
            return {"success": False, "message": f"Windows Yazdırma Hatası: {str(e)}"}

    def get_jobs(self, printer_name: Optional[str] = None) -> List[Dict[str, Any]]:
        jobs = []
        try:
            cmd = f'Get-PrintJob -PrinterName "{printer_name}" | Select-Object Id, DocumentName, JobStatus | ConvertTo-Json' if printer_name else 'Get-PrintJob | Select-Object Id, PrinterName, DocumentName, JobStatus | ConvertTo-Json'
            res = subprocess.run(['powershell', '-NoProfile', '-Command', cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            if res.stdout.strip():
                data = json.loads(res.stdout)
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    jobs.append({
                        "id": str(item.get('Id', '')),
                        "user": item.get('DocumentName', ''),
                        "status": str(item.get('JobStatus', ''))
                    })
        except Exception:
            pass
        return jobs

    def cancel_job(self, job_id: str) -> bool:
        try:
            cmd = f'Remove-PrintJob -ID {job_id}'
            res = subprocess.run(['powershell', '-NoProfile', '-Command', cmd], timeout=5)
            return res.returncode == 0
        except Exception:
            return False
