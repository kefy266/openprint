import subprocess
import time
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

    def list_printers(self) -> List[Dict[str, Any]]:
        printers = []
        try:
            res = subprocess.run(['lpstat', '-p', '-d'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            default_printer = ""
            for line in res.stdout.splitlines():
                if "system default destination:" in line:
                    default_printer = line.split("system default destination:")[-1].strip()

            for line in res.stdout.splitlines():
                if line.startswith("printer "):
                    parts = line.split()
                    p_name = parts[1]
                    is_idle = "idle" in line
                    state = "ready" if is_idle else ("busy" if "printing" in line or "processing" in line else "paused")
                    
                    printers.append({
                        "name": p_name,
                        "display_name": p_name.replace("_", " "),
                        "is_default": (p_name == default_printer),
                        "state": state,
                        "status_text": "Hazır" if is_idle else ("Yazdırılıyor" if state == "busy" else "Duraklatıldı")
                    })
        except Exception as e:
            print(f"[LinuxEngine] list_printers error: {e}")

        # If no printers found via lpstat, return empty
        return printers

    def get_printer_status(self, printer_name: str) -> Dict[str, Any]:
        try:
            res = subprocess.run(['lpstat', '-p', printer_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            out = res.stdout.strip()
            if "idle" in out:
                state = "ready"
                status = "Hazır (Boşta)"
            elif "processing" in out or "printing" in out:
                state = "busy"
                status = "Yazdırılıyor..."
            elif "disabled" in out:
                state = "paused"
                status = "Duraklatıldı"
            else:
                state = "unknown"
                status = out or "Bilinmiyor"

            # Query options/media
            opts_res = subprocess.run(['lpoptions', '-p', printer_name, '-l'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            options_text = opts_res.stdout

            return {
                "name": printer_name,
                "state": state,
                "status": status,
                "raw": out,
                "supports_color": "ColorModel" in options_text or "RGB" in options_text,
                "supports_duplex": "Duplex" in options_text or "Sides" in options_text
            }
        except Exception as e:
            return {
                "name": printer_name,
                "state": "offline",
                "status": "Bağlantı Hatası",
                "raw": str(e),
                "supports_color": True,
                "supports_duplex": False
            }

    def print_file(self, printer_name: str, file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        copies = int(options.get('copies', 1))
        color_mode = options.get('color_mode', 'RGB') # RGB or Gray
        page_size = options.get('page_size', 'A4')
        media_type = options.get('media_type', 'Stationery')
        orientation = options.get('orientation', 'portrait')
        quality = options.get('quality', 'Normal')
        scaling = options.get('scaling', 'fit')
        page_ranges = options.get('page_ranges', '').strip()
        duplex = options.get('duplex', 'None') # None, TwoSidedLongEdge, TwoSidedShortEdge

        lp_cmd = [
            'lp',
            '-d', printer_name,
            '-n', str(copies),
            '-o', f'ColorModel={color_mode}',
            '-o', f'PageSize={page_size}',
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
                "message": "Belge CUPS yazdırma kuyruğuna iletildi.",
                "raw": out_msg
            }
        except subprocess.CalledProcessError as e:
            err = e.stderr.strip() or e.stdout.strip()
            return {"success": False, "message": f"CUPS Yazdırma Hatası: {err}"}
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
