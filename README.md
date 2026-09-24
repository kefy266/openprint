# 🖨️ OpenPrint (Kolay Yazıcı) — Universal Driverless Cloud & Local Print Server

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/CUPS-IPP%20Universal-blue?style=for-the-badge&logo=linux&logoColor=white" alt="CUPS">
  <img src="https://img.shields.io/badge/Windows-Spooler%20Support-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows">
  <img src="https://img.shields.io/badge/Tunnel-Zero--Delay%20HTTPS-success?style=for-the-badge" alt="Tunnel">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License">
</p>

**OpenPrint (Kolay Yazıcı)**, USB kablolu, Wi-Fi veya ağa bağlı tüm marka/model yazıcılarınızı tek bir sürücüsüz (driverless) web arayüzüne ve güvenli internet tüneline dönüştüren açık kaynaklı kişisel yazdırma sunucusudur.

---

## 🌟 Öne Çıkan Özellikler

- 🔌 **Kablolu (USB / Paralel / Seri) Desteği**: USB kablosuyla bilgisayara bağlı tüm yazıcıları otomatik algılar ve kuyruğa ekler.
- 📡 **Kablosuz (Wi-Fi / Ethernet / AirPrint)**: Ağdaki IPP, Bonjour/mDNS ve RAW JetDirect (Port 9100) yazıcıları otomatik keşfeder.
- 🖨️ **Tüm Marka & Model Desteği**: Brother, HP, Canon, Epson, Samsung, Xerox, Pantum, Kyocera, Lexmark, Zebra (Barkod/Etiket) ve ESC/POS Termal Fiş Yazıcıları (80mm/58mm).
- 🌐 **Sıfır Beklemeli Güvenli İnternet Tüneli**: Port açmaya, statik IP'ye veya modem ayarına gerek olmadan anında canlı HTTPS linki ve mobil QR kod üretir.
- 📱 **Sürücüsüz & Mobil Uyumlu Web Arayüzü**: Telefon, tablet veya bilgisayardan sürücü kurmadan doğrudan tarayıcı üzerinden dosya/fotoğraf seçip yazdırın.
- 📸 **Kamera ile Tara & Yazdır**: Mobil cihazlardan anında belge fotoğrafı çekip yazdırma desteği.
- 📄 **Gelişmiş Baskı Seçenekleri**:
  - **Kağıt Boyutları**: A4, A3, A5, Letter, Legal, Fotoğraf (10x15 cm / 4x6 inç), B5, Termal Fiş (80mm / 58mm).
  - **Renk Modları**: Renkli (RGB) ve Siyah-Beyaz (Monochrome / Toner tasarrufu).
  - **Çift Taraflı Baskı (Duplex)**: Tek taraflı, Uzun kenar (Kitapçık), Kısa kenar (Takvim).
  - **Medya Türü**: Düz Kağıt, Parlak Fotoğraf Kağıdı (Glossy), Mat Kağıt, Zarf / Etiket.
  - **Sayfa Yönü**: Dikey (Portrait) / Yatay (Landscape).
  - **Baskı Kalitesi**: Normal Standart, Yüksek Çözünürlük (Fotoğraf), Hızlı Taslak.
  - **Sayfa Aralığı & Kopya Sayısı**: İsteğe göre sayfa seçimi ve çoklu kopya.

---

## 🚀 Hızlı Başlangıç (1-Tık Kurulum)

### 🐧 Linux / macOS / Raspberry Pi

```bash
# 1. Depoyu klonlayın
git clone https://github.com/kefy266/openprint.git
cd openprint

# 2. Kurulum ve Başlatma (Tüm bağımlılıklar otomatik kurulur)
chmod +x install.sh run.sh
./install.sh
```

> **Sonraki çalıştırmalarda:**
> ```bash
> ./run.sh
> ```

---

### 🪟 Windows (10 / 11 / Server)

1. Depoyu indirin veya klonlayın.
2. Klasör içindeki `baslat.bat` veya `run.bat` dosyasına **çift tıklayın**.
3. Sistem otomatik olarak Python ortamını hazırlar ve sunucuyu başlatır.

---

## 📦 Docker ile Çalıştırma

```bash
docker compose up -d --build
```

---

## 🔌 Donanım & Bağlantı Tipleri

| Bağlantı Türü | Desteklenen Protokoller / Portlar | Tanınan Cihazlar |
| :--- | :--- | :--- |
| **🔌 USB / Kablolu** | USB Direct, `/dev/usb/lp*`, `usb://`, `DOT4`, `LPT`, `COM` | Tüm USB kablolu yazıcılar, POS fiş yazıcıları, barkod makineleri |
| **📡 Wi-Fi / Ağ** | IPP (631), AirPrint, JetDirect (9100), LPD (515), mDNS/Bonjour | Ağ yazıcıları, çok fonksiyonlu kablosuz cihazlar |
| **📄 Sanal / PDF** | CUPS-PDF, Microsoft Print to PDF | Dijital arşivleme ve test çıktısı |

---

## 🛠️ GitHub'a Kendi Hesabınızdan Yükleme

Bu projeyi kişisel GitHub hesabınıza yüklemek için terminalden şu adımları izleyin:

```bash
# 1. Kendi GitHub hesabınızda 'openprint' adında yeni bir boş repo oluşturun.
# 2. Yerel projenizin içindeyken kendi GitHub adresinizi ekleyin:
git remote add origin https://github.com/KULLANICI_ADINIZ/openprint.git

# 3. Kodu kendi GitHub reponuza push edin:
git branch -M main
git push -u origin main
```

---

## 📂 Proje Mimarisi

```
openprint/
├── backend/
│   ├── engine/
│   │   ├── printer_base.py       # Soyut yazıcı motoru
│   │   ├── printer_linux.py      # Linux & CUPS USB/Ağ motoru
│   │   ├── printer_windows.py    # Windows Spooler & USB motoru
│   │   └── discovery.py          # USB & Ağ donanım tarayıcısı
│   ├── converters.py             # PDF, Resim, DOCX dönüştürücü
│   └── app.py                    # Flask REST API & Çoklu Tünel Yöneticisi
├── frontend/
│   ├── templates/
│   │   └── index.html            # TailwindCSS & FontAwesome Web Paneli
│   └── static/
│       ├── manifest.json         # PWA Manifest
│       └── sw.js                 # Service Worker
├── install.sh                    # Linux tek tık kurulum betiği
├── run.sh                        # Linux hızlı başlatıcı
├── install.bat                   # Windows kurulum betiği
├── baslat.bat                    # Windows tek tık başlatıcı
├── docker-compose.yml            # Docker yapılandırması
├── Dockerfile                    # Container imajı
├── requirements.txt              # Python bağımlılıkları
└── README.md                     # Dokümantasyon
```

---

## 📄 Lisans

Bu proje [MIT Lisansı](LICENSE) altında lisanslanmıştır. Kişisel ve ticari kullanım için tamamen özgürdür.
