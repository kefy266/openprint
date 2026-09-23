# 🖨️ OpenPrint

> **Self-Hosted Private Cloud Printing Server** — Print documents and photos from anywhere in the world to your local home/office printer with zero port-forwarding and driverless ease.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-brightgreen.svg)](https://python.org)
[![Platform: Linux | Windows | Docker](https://img.shields.io/badge/Platform-Linux%20%7C%20Windows%20%7C%20Docker-orange.svg)](#)
[![PWA: Ready](https://img.shields.io/badge/PWA-Ready-purple.svg)](#)

---

## ✨ Features

- 🌐 **True Cloud Printing:** Secure end-to-end printing from mobile phones, laptops, and tablets anywhere in the world via Cloudflare Tunnels (no static IP or router port forwarding required).
- 🪟 **Cross-Platform:** Native support for **Linux** (CUPS/IPP), **Raspberry Pi**, **Windows** (Win32 Spooler), and **Docker**.
- 📱 **PWA Mobile App:** Installable as a native app on iOS & Android directly from Safari/Chrome with a single tap.
- 📷 **Camera Document Scanner:** Snap pictures of homework, contracts, or invoices with your smartphone camera; OpenPrint auto-crops, sharpens, and converts them into crystal-clear 300 DPI PDF prints.
- 🎨 **Rich Print Customization:**
  - Full Color vs. High-Yield Black & White
  - Paper Size (A4, A5, 4x6" Photo, Letter)
  - Plain Paper vs. Glossy Photo Paper
  - Portrait vs. Landscape orientation
  - Multi-copy counter & custom page range selection (e.g. `1-3, 5`)
- 🏷️ **QR Code Generator:** Print a sleek QR poster to stick directly onto your physical printer. Guests simply scan the QR to print instantly.
- 🔐 **Optional Security PIN:** Protect your printer with a customizable 4-digit access PIN or guest mode.
- 🔍 **Auto-Discovery:** Automatically scans and detects network printers (Brother, HP, Canon, Epson, Xerox, etc.) via IPP/mDNS and RAW ports.

---

## 🚀 Quick Start

### 1. Using Docker Compose (Recommended)

```bash
git clone https://github.com/your-username/openprint.git
cd openprint
docker compose up -d
```

### 2. Linux / Raspberry Pi (One-Line Installer)

```bash
git clone https://github.com/your-username/openprint.git
cd openprint
sudo bash scripts/install.sh
```

### 3. Windows (1-Click)

Double-click `scripts\install_windows.bat` or run in PowerShell:
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python -m backend.app
```

---

## 🏛️ Architecture

```mermaid
flowchart LR
    A["📱 Smartphone / PC<br/>(Remote / Anywhere)"] -->|HTTPS / Upload| B["☁️ Cloudflare Tunnel<br/>(Zero-Trust / No Port Open)"]
    B --> C["🖥️ OpenPrint Server<br/>(FastAPI / Flask Engine)"]
    C -->|Auto 300DPI Converter| D["📄 Optimized Print Job"]
    D --> E["🖨️ Local Printer<br/>(Brother, HP, Canon, Epson)"]
```

---

## 📄 License

OpenPrint is open-source software licensed under the [MIT License](LICENSE).
