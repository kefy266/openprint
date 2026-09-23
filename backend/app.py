import os
import sys
import time
import json
import uuid
import platform
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

# Select OS Engine
IS_WINDOWS = platform.system().lower() == 'windows'
engine = WindowsPrinterEngine() if IS_WINDOWS else LinuxPrinterEngine()

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "server_name": "OpenPrint Server",
        "pin_code": "",  # Optional 4-digit PIN protection
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

@app.route('/uploads/<filename>')
def serve_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename)

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
        # Default or first printer
        selected_printer = next((p['name'] for p in printers if p.get('is_default')), printers[0]['name'])

    printer_status = engine.get_printer_status(selected_printer) if selected_printer else {"status": "Yazıcı Yok", "state": "offline"}
    active_jobs = engine.get_jobs(selected_printer) if selected_printer else []
    history = load_history()
    config = load_config()

    return jsonify({
        "selected_printer": selected_printer,
        "printers": printers,
        "status": printer_status,
        "active_jobs": active_jobs,
        "history": history,
        "requires_pin": bool(config.get("pin_code"))
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
            return jsonify({"success": False, "message": "Sistemde tanımlı yazıcı bulunamadı."}), 400

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
    except Exception as e:
        return jsonify({"success": False, "message": f"Dosya dönüştürme hatası: {str(e)}"}), 500

    # Dispatch to Engine
    result = engine.print_file(printer_name, printable_path, options)

    if result.get("success"):
        history_item = {
            "id": result.get("job_id", f"job-{int(time.time())}"),
            "printer": printer_name,
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

@app.route('/api/cancel', methods=['POST'])
def cancel_print_job():
    job_id = request.json.get('job_id') if request.json else None
    if not job_id:
        return jsonify({"success": False, "message": "Job ID gerekli."}), 400
    ok = engine.cancel_job(job_id)
    return jsonify({"success": ok})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5050))
    app.run(host='0.0.0.0', port=port, debug=False)
