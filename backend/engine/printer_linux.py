import subprocess
import shutil
import time
import re
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
        printers_dict = {}
        default_printer = ""

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
                        printers_dict[p_name] = {
                            "name": p_name,
                            "display_name": p_name.replace("_", " "),
                            "is_default": False,
                            "state": state,
                            "status_text": "Hazır" if is_idle else ("Yazdırılıyor" if state == "busy" else "Duraklatıldı")
                        }
        except Exception as e:
            print(f"[LinuxEngine] lpstat -p -d error: {e}")

        # Strategy 2: lpstat -e (lists all destination names directly)
        try:
            res_e = subprocess.run(['lpstat', '-e'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            for line in res_e.stdout.splitlines():
                p_name = line.strip()
                if p_name and p_name not in printers_dict:
                    printers_dict[p_name] = {
                        "name": p_name,
                        "display_name": p_name.replace("_", " "),
                        "is_default": False,
                        "state": "ready",
                        "status_text": "Hazır"
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
                        printers_dict[p_name] = {
                            "name": p_name,
                            "display_name": p_name.replace("_", " "),
                            "is_default": False,
                            "state": "ready",
                            "status_text": "Hazır"
                        }
        except Exception:
            pass

        # Strategy 4: IPP / ippfind auto-detection
        if not printers_dict:
            try:
                res_ipp = subprocess.run(['ippfind'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
                for line in res_ipp.stdout.splitlines():
                    uri = line.strip()
                    if uri:
                        match = re.search(r'ipp://([^.]+)', uri)
                        p_name = match.group(1) if match else "Network_Printer"
                        printers_dict[p_name] = {
                            "name": p_name,
                            "display_name": p_name.replace("_", " "),
                            "is_default": True,
                            "state": "ready",
                            "status_text": "Hazır (Ağ Yazıcısı)"
                        }
            except Exception:
                pass

        # Mark default
        if default_printer and default_printer in printers_dict:
            printers_dict[default_printer]["is_default"] = True
        elif printers_dict:
            first_key = list(printers_dict.keys())[0]
            printers_dict[first_key]["is_default"] = True

        result = list(printers_dict.values())
        return result

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

            return {
                "name": printer_name,
                "display_name": printer_name.replace("_", " "),
                "state": state,
                "status": status,
                "raw": out,
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
                "message": "Belge başarıyla yazıcıya iletildi.",
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
