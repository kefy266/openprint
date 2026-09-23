#!/bin/bash
set -e

echo "====================================================="
echo "        🖨️ OpenPrint One-Click Installer"
echo "====================================================="

# Check sudo
if [ "$EUID" -ne 0 ]; then
  echo "Lütfen bu betiği root veya sudo yetkisiyle çalıştırın."
  exit 1
fi

echo "[1/4] Gerekli sistem paketleri yükleniyor (CUPS, Python)..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv cups cups-client cups-ipp-utils cups-filters curl

echo "[2/4] Python sanal ortamı kuruluyor..."
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

python3 -m venv venv
./venv/bin/pip install --upgrade pip -qq
./venv/bin/pip install -r requirements.txt -qq

echo "[3/4] Systemd servisleri yapılandırılıyor..."
cat << EOF > /etc/systemd/system/openprint.service
[Unit]
Description=OpenPrint Cloud Printing Server
After=network.target cups.service

[Service]
User=$SUDO_USER
WorkingDirectory=$DIR
ExecStart=$DIR/venv/bin/gunicorn -w 2 -b 0.0.0.0:5050 backend.app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now openprint.service

echo "[4/4] Kurulum tamamlandı! 🎉"
echo "OpenPrint yerel erişim adresi: http://$(hostname -I | awk '{print $1}'):5050"
echo "Bulut tüneli ile dışarı açmak için: cloudflared tunnel --url http://127.0.0.1:5050"
echo "====================================================="
