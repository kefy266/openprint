import os
import subprocess
import time
from typing import List, Dict, Any, Optional
from .printer_base import BasePrinterEngine

class WindowsPrinterEngine(BasePrinterEngine):
    def __init__(self):
        pass

    def list_printers(self) -> List[Dict[str, Any]]:
        printers = []
        try:
            # Use PowerShell Get-Printer
            ps_cmd = 'Get-Printer | Select-Object Name, Type, PrinterStatus, Default | ConvertTo-Json'
            res = subprocess.run(['powershell', '-NoProfile', '-Command', ps_cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=8)
            import json
            if res.stdout.strip():
                data = json.loads(res.stdout)
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    name = item.get('Name', 'Bilinmeyen')
                    is_def = bool(item.get('Default', False))
                    status_code = item.get('PrinterStatus', 3)
                    state = "ready" if status_code == 3 else ("busy" if status_code == 4 else "offline")
                    
                    printers.append({
                        "name": name,
                        "display_name": name,
                        "is_default": is_def,
                        "state": state,
                        "status_text": "Hazır" if state == "ready" else "Meşgul/Çevrimdışı"
                    })
        except Exception as e:
            print(f"[WindowsEngine] list_printers error: {e}")
        return printers

    def get_printer_status(self, printer_name: str) -> Dict[str, Any]:
        try:
            ps_cmd = f'Get-Printer -Name "{printer_name}" | Select-Object Name, PrinterStatus, JobCount | ConvertTo-Json'
            res = subprocess.run(['powershell', '-NoProfile', '-Command', ps_cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            import json
            if res.stdout.strip():
                data = json.loads(res.stdout)
                return {
                    "name": printer_name,
                    "state": "ready",
                    "status": "Hazır (Windows Spooler)",
                    "job_count": data.get('JobCount', 0),
                    "supports_color": True,
                    "supports_duplex": True
                }
        except Exception as e:
            pass
        return {
            "name": printer_name,
            "state": "ready",
            "status": "Windows Yazıcı Hazır",
            "supports_color": True,
            "supports_duplex": True
        }

    def print_file(self, printer_name: str, file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        abs_path = os.path.abspath(file_path).replace('/', '\\')
        # Use PowerShell Start-Process with -Verb PrintTo or PDFtoPrinter if present
        try:
            # Check if PDFtoPrinter utility exists for exact copies/tray management
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
            import json
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
