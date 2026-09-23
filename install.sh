#!/usr/bin/env bash
# ==============================================================================
#  🖨️ OpenPrint / Kolay Yazıcı — Tek Komutla Kurulum ve Başlatma Betiği
#  Desteklenen Sistemler: Ubuntu, Debian, Raspberry Pi OS, Fedora, Arch, macOS
# ==============================================================================

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "=================================================================="
echo "    🖨️  OpenPrint (Kolay Yazıcı) Otomatik Kurulum ve Başlatıcı"
echo "        Sürücüsüz & PWA Destekli Kişisel Bulut Yazdırma Sunucusu"
echo "=================================================================="
echo -e "${NC}"

# Find script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Check & Install System Dependencies
echo -e "${YELLOW}[1/4] Sistem paketleri kontrol ediliyor...${NC}"

if [ -f /etc/debian_version ]; then
    if [ "$EUID" -ne 0 ]; then
        SUDO_CMD="sudo"
    else
        SUDO_CMD=""
    fi
    $SUDO_CMD apt-get update -qq
    $SUDO_CMD apt-get install -y -qq python3 python3-pip python3-venv cups cups-client cups-bsd curl >/dev/null 2>&1 || true
elif [ -f /etc/redhat-release ]; then
    sudo dnf install -y python3 python3-pip cups cups-client curl >/dev/null 2>&1 || true
elif [ -f /etc/arch-release ]; then
    sudo pacman -Sy --noconfirm python python-pip cups cups-filters curl >/dev/null 2>&1 || true
fi

# 2. Setup Python Virtual Environment
echo -e "${YELLOW}[2/4] Python sanal ortamı (venv) ve kütüphaneler kuruluyor...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

./venv/bin/pip install --upgrade pip -qq
./venv/bin/pip install -r requirements.txt -qq

# 3. Systemd Service Option (Optional daemon)
if [ "$1" == "--service" ] || [ "$1" == "-s" ]; then
    echo -e "${YELLOW}[3/4] Systemd arka plan servisi yapılandırılıyor...${NC}"
    SERVICE_USER="${SUDO_USER:-$USER}"
    cat << EOF | sudo tee /etc/systemd/system/openprint.service > /dev/null
[Unit]
Description=OpenPrint Cloud Printing Server
After=network.target cups.service

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$SCRIPT_DIR
Environment="PORT=5050"
ExecStart=$SCRIPT_DIR/venv/bin/python3 -m backend.app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable --now openprint.service
    echo -e "${GREEN}✓ OpenPrint servisi arka planda başlatıldı (Port: 5050)!${NC}"
fi

# 4. Get Local IP Address
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")
if [ -z "$LOCAL_IP" ]; then
    LOCAL_IP="127.0.0.1"
fi

echo ""
echo -e "${GREEN}==================================================================${NC}"
echo -e "${GREEN}  🎉 KURULUM TAMAMLANDI! OpenPrint kullanıma hazır!${NC}"
echo -e "${GREEN}==================================================================${NC}"
echo ""
echo -e "  🌐 ${CYAN}Yerel Ağdan Erişim:${NC}   http://${LOCAL_IP}:5050"
echo -e "  💻 ${CYAN}Bu Cihazdan:${NC}          http://localhost:5050"
echo ""
echo -e "  ☁️ ${YELLOW}İnternete Açmak İçin (Port açmadan & Ücretsiz):${NC}"
echo -e "     cloudflared tunnel --url http://127.0.0.1:5050"
echo ""

if [ "$1" != "--service" ] && [ "$1" != "-s" ]; then
    echo -e "${CYAN}Sunucu başlatılıyor... (Durdurmak için CTRL+C)${NC}"
    echo ""
    ./venv/bin/python3 -m backend.app
fi
