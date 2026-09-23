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
from .engine.discovery import scan_local_printers
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

# Global State for Cloudflare Tunnel
TUNNEL_STATE = {
    "url": None,
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
    cloudflared_bin = shutil.which("cloudflared")
    if not cloudflared_bin:
        for possible in ["/usr/local/bin/cloudflared", "/usr/bin/cloudflared", os.path.expanduser("~/.local/bin/cloudflared"), os.path.join(BASE_DIR, '..', 'cloudflared.exe')]:
            if os.path.exists(possible):
                cloudflared_bin = possible
                break

    if not cloudflared_bin:
        print("[Tunnel] cloudflared bulunamadı. Yerel ağ üzerinden çalışılıyor.")
        TUNNEL_STATE["status"] = "not_installed"
        return

    while True:
        try:
            print(f"[Tunnel] Cloudflare tüneli başlatılıyor (Port {port})...")
            cmd = [cloudflared_bin, 'tunnel', '--url', f'http://127.0.0.1:{port}']
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, bufsize=1)
            TUNNEL_STATE["proc"] = proc
            TUNNEL_STATE["started_at"] = datetime.now().isoformat()
            
            # Continuously drain stderr and extract URL
            for line in iter(proc.stderr.readline, ''):
                if not line:
                    break
                if 'trycloudflare.com' in line:
                    match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
                    if match:
                        tunnel_url = match.group(0)
                        TUNNEL_STATE["url"] = tunnel_url
                        TUNNEL_STATE["status"] = "active"
                        print("")
                        print("=" * 64)
                        print("  🎉 CLOUDFLARE TÜNELİ AKTİF!")
                        print(f"  🌐 İnternet Erişim Linki: {tunnel_url}")
                        print("  (Ev dışından & cep telefonundan doğrudan açabilirsiniz)")
                        print("=" * 64)
                        print("")

            proc.wait()
            print("[Tunnel] Tünel kapandı, 5 saniye sonra yeniden bağlanılıyor...")
            time.sleep(5)
        except Exception as e:
            print(f"[Tunnel] Hata: {e}")
            TUNNEL_STATE["status"] = "error"
            time.sleep(5)

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
        "local_ip": get_local_ip()
    })

@app.route('/api/printers', methods=['GET'])
def get_printers():
    printers = engine.list_printers()
    return jsonify({
        "os": "Windows" if IS_WINDOWS else "Linux/Unix",
        "printers": printers
    })

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

@app.route('/api/scan', methods=['POST'])
def discover_network_printers():
    subnet = request.json.get('subnet', '192.168.0') if request.json else '192.168.0'
    found = scan_local_printers(subnet)
    return jsonify({"success": True, "discovered": found})

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
            "timestamp": datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
            "status": "Tamamlandı"
        }
        history = load_history()
        history.append(history_item)
        save_history(history)

        return jsonify({
            "success": True,
            "message": "Belge başarıyla yazıcıya gönderildi! 🖨️",
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
    # Start Cloudflare Tunnel Supervisor in background thread
    t = threading.Thread(target=tunnel_supervisor, args=(port,), daemon=True)
    t.start()

    local_ip = get_local_ip()
    print("=" * 64)
    print("  🖨️  OpenPrint (Kolay Yazıcı) Başlatıldı!")
    print(f"  💻 Yerel Erişim:      http://localhost:{port}")
    print(f"  🌐 Yerel Ağ Erişimi:  http://{local_ip}:{port}")
    print("=" * 64)

    app.run(host='0.0.0.0', port=port, debug=False)
