import os
import sys
import time
import json
import uuid
import platform
import threading
import subprocess
import shutil
import re
import socket
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from .engine.printer_linux import LinuxPrinterEngine
from .engine.printer_windows import WindowsPrinterEngine
from .engine.discovery import scan_all_devices, scan_usb_hardware, scan_network_printers
from .converters import process_file_for_print

app = Flask(
    __name__,
    static_folder='../frontend/static',
    template_folder='../frontend/templates'
)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, '..', 'uploads')
CONFIG_FILE = os.path.join(BASE_DIR, '..', 'config.json')
HISTORY_FILE = os.path.join(BASE_DIR, '..', 'history.json')

os.makedirs(UPLOAD_DIR, exist_ok=True)

# Select Engine
IS_WINDOWS = platform.system().lower() == 'windows'
engine = WindowsPrinterEngine() if IS_WINDOWS else LinuxPrinterEngine()

# Global State for Live Public Tunnel
TUNNEL_STATE = {
    "url": None,
    "provider": "LHR (Instant HTTPS)",
    "status": "starting",
    "started_at": None,
    "proc": None
}

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def tunnel_supervisor(port=5050):
    global TUNNEL_STATE

    while True:
        # Provider 1: LHR SSH Tunnel (Instant Worldwide HTTPS, No DNS Delay)
        try:
            print(f"[Tunnel] Anında HTTPS tüneli açılıyor (Port {port})...")
            ssh_bin = shutil.which("ssh") or "ssh"
            cmd = [
                ssh_bin,
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "ServerAliveInterval=20",
                "-o", "ServerAliveCountMax=3",
                "-R", f"80:127.0.0.1:{port}",
                "nokey@localhost.run"
            ]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            TUNNEL_STATE["proc"] = proc
            TUNNEL_STATE["started_at"] = datetime.now().isoformat()

            for line in iter(proc.stdout.readline, ''):
                if not line:
                    break
                # Match https://...lhr.life or https://...localhost.run
                m = re.search(r'https://[a-zA-Z0-9.-]+\.lhr\.life', line) or re.search(r'https://[a-zA-Z0-9.-]+\.localhost\.run', line)
                if m:
                    tunnel_url = m.group(0)
                    TUNNEL_STATE["url"] = tunnel_url
                    TUNNEL_STATE["status"] = "active"
                    TUNNEL_STATE["provider"] = "LHR Cloud (Anında Bağlantı)"
                    print("")
                    print("=" * 66)
                    print("  🎉 İNTERNET TÜNELİ AKTİF (DNS BEKLEME YOK)!")
                    print(f"  🌐 Canlı Erişim Linki: {tunnel_url}")
                    print("  (Telefonunuzdan veya ev dışından hemen açıp yazdırabilirsiniz)")
                    print("=" * 66)
                    print("")

            proc.wait()
        except Exception as e:
            print(f"[Tunnel LHR] Hata: {e}")

        # Fallback to Cloudflare if SSH fails
        try:
            cloudflared_bin = shutil.which("cloudflared") or "/usr/local/bin/cloudflared"
            if os.path.exists(cloudflared_bin) or shutil.which("cloudflared"):
                print("[Tunnel] Cloudflare tüneli deneniyor...")
                cmd_cf = [cloudflared_bin, 'tunnel', '--protocol', 'http2', '--url', f'http://127.0.0.1:{port}']
                proc_cf = subprocess.Popen(cmd_cf, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, bufsize=1)
                TUNNEL_STATE["proc"] = proc_cf
                
                for line in iter(proc_cf.stderr.readline, ''):
                    if not line:
                        break
                    if 'trycloudflare.com' in line:
                        match_cf = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
                        if match_cf:
                            tunnel_url = match_cf.group(0)
                            TUNNEL_STATE["url"] = tunnel_url
                            TUNNEL_STATE["status"] = "active"
                            TUNNEL_STATE["provider"] = "Cloudflare Tunnel"
                            print("")
                            print("=" * 66)
                            print(f"  🌐 Cloudflare Erişim Linki: {tunnel_url}")
                            print("=" * 66)
                            print("")
                proc_cf.wait()
        except Exception as e:
            print(f"[Tunnel CF] Hata: {e}")

        print("[Tunnel] Tünel koptu, 3 saniye sonra yeniden bağlanılıyor...")
        time.sleep(3)

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "server_name": "Kolay Yazıcı",
        "pin_code": "",
        "default_printer": "",
        "allow_guest": True,
        "max_file_size_mb": 50
    }

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(history):
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history[-100:], f, ensure_ascii=False, indent=2)
    except Exception:
        pass

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/tunnel', methods=['GET'])
def get_tunnel():
    return jsonify({
        "tunnel_url": TUNNEL_STATE.get("url"),
        "status": TUNNEL_STATE.get("status"),
        "provider": TUNNEL_STATE.get("provider"),
        "local_ip": get_local_ip()
    })

@app.route('/api/printers', methods=['GET'])
def get_printers():
    printers = engine.list_printers()
    return jsonify({
        "os": "Windows" if IS_WINDOWS else "Linux/Unix",
        "printers": printers
    })

@app.route('/api/printers/scan', methods=['POST', 'GET'])
def scan_hardware():
    """Live scan for connected USB and Network printers."""
    try:
        unconfigured = engine.scan_unconfigured_hardware() if hasattr(engine, 'scan_unconfigured_hardware') else []
        all_found = scan_all_devices()
        return jsonify({
            "success": True,
            "configured": engine.list_printers(),
            "unconfigured": unconfigured,
            "usb_hardware": all_found.get("usb_printers", []),
            "network_hardware": all_found.get("network_printers", [])
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/printers/auto-setup', methods=['POST'])
def auto_setup_printer():
    """Automatically add a detected USB or Network printer to the system."""
    data = request.json or {}
    name = data.get('name', 'New_Printer')
    uri = data.get('uri', '')
    if not uri:
        return jsonify({"success": False, "message": "URI parametresi zorunludur."}), 400

    if hasattr(engine, 'auto_add_printer'):
        res = engine.auto_add_printer(name, uri)
        return jsonify(res)
    return jsonify({"success": False, "message": "Bu işletim sisteminde otomatik kuyruk ekleme desteklenmiyor."}), 400

@app.route('/api/status', methods=['GET'])
def get_status():
    printers = engine.list_printers()
    selected_printer = request.args.get('printer')
    if not selected_printer and printers:
        selected_printer = next((p['name'] for p in printers if p.get('is_default')), printers[0]['name'])

    printer_status = engine.get_printer_status(selected_printer) if selected_printer else {"status": "Yazıcı Hazır", "state": "ready"}
    active_jobs = engine.get_jobs(selected_printer) if selected_printer else []
    history = load_history()
    config = load_config()

    return jsonify({
        "selected_printer": selected_printer,
        "printers": printers,
        "status": printer_status,
        "active_jobs": active_jobs,
        "history": history,
        "tunnel_url": TUNNEL_STATE.get("url"),
        "local_ip": get_local_ip()
    })

@app.route('/api/jobs/<job_id>/cancel', methods=['POST'])
def cancel_print_job(job_id):
    success = engine.cancel_job(job_id)
    return jsonify({"success": success})

@app.route('/api/print', methods=['POST'])
def print_document():
    config = load_config()
    required_pin = config.get("pin_code", "")
    
    if required_pin:
        user_pin = request.form.get("pin", "")
        if user_pin != required_pin:
            return jsonify({"success": False, "message": "Geçersiz Güvenlik PIN Kodu!"}), 403

    if 'file' not in request.files:
        return jsonify({"success": False, "message": "Lütfen bir dosya seçin."}), 400

    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({"success": False, "message": "Dosya adı boş olamaz."}), 400

    printer_name = request.form.get('printer', '')
    if not printer_name:
        printers = engine.list_printers()
        if printers:
            printer_name = printers[0]['name']
        else:
            printer_name = "Default_Printer"

    options = {
        'copies': int(request.form.get('copies', 1)),
        'color_mode': request.form.get('color_mode', 'RGB'),
        'page_size': request.form.get('page_size', 'A4'),
        'media_type': request.form.get('media_type', 'Stationery'),
        'orientation': request.form.get('orientation', 'portrait'),
        'quality': request.form.get('quality', 'Normal'),
        'scaling': request.form.get('scaling', 'fit'),
        'page_ranges': request.form.get('page_ranges', '').strip(),
        'duplex': request.form.get('duplex', 'None')
    }

    job_uuid = str(uuid.uuid4())[:8]
    raw_path = os.path.join(UPLOAD_DIR, f"{job_uuid}_{file.filename}")
    file.save(raw_path)

    # Process file to high-res printable format
    try:
        printable_path = process_file_for_print(raw_path, UPLOAD_DIR, job_uuid, options['orientation'])
    except Exception:
        printable_path = raw_path

    # Dispatch to Engine
    result = engine.print_file(printer_name, printable_path, options)

    if result.get("success"):
        history_item = {
            "id": result.get("job_id", f"job-{int(time.time())}"),
            "printer": printer_name.replace("_", " "),
            "filename": file.filename,
            "copies": options['copies'],
            "color": "Renkli" if options['color_mode'] == 'RGB' else "Siyah-Beyaz",
            "paper": options['page_size'],
            "media": "Fotoğraf Kağıdı" if options['media_type'] == 'PhotographicGlossy' else "Normal Kağıt",
            "orientation": "Yatay" if options['orientation'] == 'landscape' else "Dikey",
            "duplex": "Çift Taraflı" if options['duplex'] != 'None' else "Tek Taraflı",
            "timestamp": datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
            "status": "Tamamlandı"
        }
        history = load_history()
        history.append(history_item)
        save_history(history)

        return jsonify({
            "success": True,
            "message": f"Belge {printer_name.replace('_', ' ')} yazıcısına başarıyla gönderildi! 🖨️",
            "job_id": result.get("job_id"),
            "details": history_item
        })
    else:
        return jsonify({
            "success": False,
            "message": result.get("message", "Yazdırma işlemi başarısız.")
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5050))
    # Start Multi-Tunnel Supervisor in background thread
    t = threading.Thread(target=tunnel_supervisor, args=(port,), daemon=True)
    t.start()

    local_ip = get_local_ip()
    print("=" * 66)
    print("  🖨️  OpenPrint (Kolay Yazıcı) Başlatıldı!")
    print(f"  💻 Yerel Erişim:      http://localhost:{port}")
    print(f"  🌐 Yerel Ağ Erişimi:  http://{local_ip}:{port}")
    print("=" * 66)

    app.run(host='0.0.0.0', port=port, debug=False)
