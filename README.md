# Techfour Discord Bot 🤖

Bot Discord berbasis **AI multi-engine** dengan integrasi **Google Gemini**, dirancang khusus untuk mendukung **pembelajaran, diskusi akademik, dan manajemen komunitas** di Discord.

📍 **Kelas 01TPLE04 – Teknik Informatika, Universitas Pamulang**

---

## 📋 Daftar Isi
- [🚀 Overview](#-overview)
- [✨ Fitur Utama](#-fitur-utama)
- [🏗️ Struktur Proyek](#-struktur-proyek)
- [🛠️ Teknologi](#-teknologi)
- [📦 Instalasi & Setup](#-instalasi--setup)
- [⚙️ Konfigurasi Environment](#-konfigurasi-environment)
- [🎯 Cara Menggunakan](#-cara-menggunakan)
- [📁 Dokumentasi Service](#-dokumentasi-service)
- [🚀 Deployment](#-deployment)
- [📝 Kontribusi](#-kontribusi)

---

## 🚀 Overview

Techfour Discord Bot adalah solusi AI terpadu yang memudahkan mahasiswa dan dosen untuk:
- ❓ **Tanya Jawab Akademik** - Menjawab pertanyaan dengan context yang sesuai
- 💻 **Bantuan Coding** - Debugging dan penjelasan konsep programming
- 📐 **Problem Solving** - Diskusi matematika dan logika
- 🗓️ **Manajemen Jadwal** - Pengingat otomatis jadwal kuliah
- 💰 **Tracking Keuangan** - Manajemen uang kas kelas yang transparan
- 📸 **OCR & Analisis Gambar** - Ekstraksi teks dari gambar/PDF

---

## ✨ Fitur Utama

| 🎯 Fitur | 📝 Deskripsi |
|---------|-----------|
| **🧠 AI Multi-Engine** | Routing cerdas ke model terbaik sesuai pertanyaan |
| **🔢 Matematika (Wolfram)** | Perhitungan kompleks & visualisasi grafik |
| **💾 Coding (CodeGemma)** | Analisis & debugging code |
| **📖 General (Gemini)** | Q&A umum & diskusi akademik |
| **📸 OCR Gambar/PDF** | Ekstraksi teks otomatis dari visual |
| **🕐 Jadwal Kuliah** | Reminder otomatis (Jumat & Minggu 08.00 WIB) |
| **💰 Uang Kas System** | Integrasi Google Spreadsheet, tracking real-time |
| **⚡ Rate Limiting** | 5 req/hari (user), 10 req/hari (admin), cooldown 60s |
| **📊 Health Check** | Endpoint `/health` untuk monitoring |
| **🪝 Webhook Logging** | Logging otomatis error & aktivitas |

---

## 🏗️ Struktur Proyek

```
discord-bot/
│
├── main.py                          # Bot Core - Discord Event Handler
│
├── services/                        # Business Logic Layer
│   ├── __init__.py
│   ├── ai_bot_service.py           # Multi-engine AI Service
│   ├── uang_kas_service.py         # Finance Management Service  
│   └── spreadsheet_service.js      # Google Apps Script (Backend)
│
├── config/                         # Reference Configuration Files
│   ├── requirements.txt            # (Reference copy)
│   └── runtime.txt                 # (Reference copy)
│
├── requirements.txt                # 📌 Dependencies (Root - for Deployment)
├── runtime.txt                     # 📌 Python Version (Root - for Deployment)
├── jadwal_kuliah.txt              # Schedule Data (Text Format)
├── .env                           # Environment Variables (Git Ignored)
├── .gitignore                     # Git Ignore Rules
├── Procfile                       # Deployment Config (Heroku/Railway)
└── README.md                      # This File

```

**⚠️ Deployment Notes:**
- `requirements.txt` & `runtime.txt` **HARUS** di root directory untuk Railway/Heroku
- Folder `config/` adalah reference copy untuk development


### 📂 Service Breakdown

#### **services/ai_bot_service.py** 🧠
Intelligent AI routing engine yang memilih model terbaik untuk setiap pertanyaan.

**Fitur:**
- Multi-model LLM routing (Gemini, Wolfram, CodeGemma)
- Response caching (300s) untuk optimasi
- Image/PDF processing dengan OCR
- Token limit management

**Kelas Utama:** `SmartAIService`

---

#### **services/uang_kas_service.py** 💰
Service untuk manajemen uang kas kelas dengan integrasi Google Spreadsheet via Apps Script.

**Fitur:**
- CRUD operations untuk data keuangan
- Real-time sync dengan Google Sheets
- Caching untuk performa
- Error handling & logging

**Kelas Utama:** `UangKasService`

---

#### **services/spreadsheet_service.js** 📊
Google Apps Script backend untuk integrasi spreadsheet dengan Discord Bot.

**Fungsi Utama:**
- `doGet()` - REST API handler
- `getStudentsData()` - Ambil semua data siswa
- `getDashboardData()` - Dashboard summary
- `getSingleStudentData()` - Data siswa spesifik

---

## 🛠️ Teknologi

| Komponen | Detail |
|----------|--------|
| **Backend** | Python 3.10+ |
| **Framework Bot** | discord.py 2.3+ |
| **AI/ML** | Google Gemini, Wolfram Alpha, Hugging Face CodeGemma |
| **Database** | Google Spreadsheet (via Apps Script) |
| **HTTP Client** | aiohttp (async) |
| **Scheduling** | discord.py tasks |
| **Logging** | Python logging + Discord Webhook |
| **Deployment** | Railway / Heroku |

---

## 📦 Instalasi & Setup

### 1️⃣ Clone Repository
```bash
git clone https://github.com/Techfourma/discord-bot.git
cd discord-bot
```

### 2️⃣ Setup Python Environment
```bash
# Buat virtual environment
python3 -m venv venv

# Aktivasi virtual environment
# Linux/Mac:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

### 3️⃣ Install Dependencies
```bash
pip install -r config/requirements.txt
```

### 4️⃣ Konfigurasi Environment File
Buat file `.env` di root project:
```bash
cp .env.example .env  # Jika ada template
# atau buat manual
```

---

## ⚙️ Konfigurasi Environment

Buat file `.env` dengan variabel berikut:

```env
# Discord
DISCORD_TOKEN=your_discord_bot_token_here

# AI APIs
GEMINI_API_KEY=your_gemini_api_key
WOLFRAM_APP_ID=your_wolfram_app_id
HF_TOKEN=your_hugging_face_token

# Google Integration
GOOGLE_APPS_SCRIPT_URL=https://script.google.com/macros/d/{SCRIPT_ID}/usercss
SPREADSHEET_ID=your_spreadsheet_id

# Logging (Optional)
WEBHOOK_URL=your_discord_webhook_url

# Server
PORT=8080  # Default untuk health check
```

### 📖 Cara Mendapatkan Credentials

**Discord Bot Token:**
1. Buka Discord Developer Portal: https://discord.com/developers/applications
2. Create New Application → Buat bot
3. Copy token di "TOKEN" section

**Gemini API Key:**
1. Pergi ke Google AI Studio: https://ai.google.dev/
2. Click "Get API Key" dan copy

**Wolfram Alpha:**
1. Register di: https://developer.wolframalpha.com/
2. Get AppID dari dashboard

**Hugging Face Token:**
1. Daftar/Login: https://huggingface.co/
2. Settings → Access Tokens → New token

---

## 🎯 Cara Menggunakan

### Command Format

#### 1. **AI Question**
```
@Techfour Bot Apa itu machine learning?
```
Bot akan otomatis route ke model terbaik dan memberikan jawaban kontekstual.

#### 2. **Matematika**
```
@Techfour Bot Hitung integral dari x^2 + 2x dari 0 sampai 5
```
Akan di-route ke Wolfram Alpha untuk perhitungan presisi.

#### 3. **Coding Help**
```
@Techfour Bot Jelaskan code ini: 
def factorial(n):
    return 1 if n <= 1 else n * factorial(n-1)
```

#### 4. **Image Analysis**
```
@Techfour Bot [Attach image/PDF]
Apa yang tertulis di gambar ini?
```

### Rate Limiting
- User Regular: 5 request/hari
- Admin: 10 request/hari
- Cooldown antar request: 60 detik

---

## 📁 Dokumentasi Service

### SmartAIService (ai_bot_service.py)

```python
from services.ai_bot_service import SmartAIService

service = SmartAIService()

# Get AI response
response = await service.get_response(
    prompt="Jelaskan konsep OOP",
    user_id="123456789",
    image_bytes=None  # Optional untuk OCR
)
```

### UangKasService (uang_kas_service.py)

```python
from services.uang_kas_service import UangKasService

service = UangKasService()

# Initialize
await service.initialize()

# Get data
students = await service.get_all_students()
dashboard = await service.get_dashboard_data()
student = await service.get_student_data("John Doe")
```

---

## 🚀 Deployment

### Option 1: Railway (Recommended)
```bash
# 1. Push ke GitHub
git push origin main

# 2. Connect GitHub repo ke Railway.app
# 3. Deploy otomatis saat ada push

# 4. Set environment variables di Railway dashboard
```

### Option 2: Heroku
```bash
# 1. Install Heroku CLI
# 2. Login & create app
heroku create your-bot-name

# 3. Set environment variables
heroku config:set DISCORD_TOKEN=xxx

# 4. Deploy
git push heroku main
```

### Health Check
Bot menyediakan health endpoint:
```bash
curl http://localhost:8080/health
# Response: OK
```

---

## 🔄 Workflow Development

### 1. Setup Branch Baru
```bash
git checkout -b feature/nama-fitur
```

### 2. Buat/Edit Code
```bash
# Edit file di services/
# Test locally
python3 main.py
```

### 3. Commit & Push
```bash
git add .
git commit -m "feat: deskripsi feature"
git push origin feature/nama-fitur
```

### 4. Create Pull Request
- Buka GitHub
- Create PR dengan deskripsi jelas
- Request review dari maintainer

### 5. Merge & Deploy
```bash
# Setelah approve
git checkout main
git merge feature/nama-fitur
git push origin main
```

---

## 📝 Kontribusi

Kami terbuka untuk kontribusi! 🎉

### Pedoman Kontribusi

1. **Fork** repository
2. **Clone** fork ke lokal
3. **Buat branch** fitur baru: `git checkout -b feature/amazing-feature`
4. **Commit** perubahan: `git commit -m 'Add amazing feature'`
5. **Push** ke branch: `git push origin feature/amazing-feature`
6. **Buka Pull Request** dengan deskripsi lengkap

### Coding Standards
- Gunakan **docstring** untuk setiap fungsi
- Follow **PEP 8** untuk Python
- Naming convention: `snake_case` untuk function/variable
- Tambahkan error handling & logging

---

## 🐛 Troubleshooting

### Bot Not Responding
```
✓ Cek DISCORD_TOKEN valid
✓ Cek Message Content Intent aktif
✓ Restart bot
```

### API Error
```
✓ Cek semua API keys di .env
✓ Check quota limits
✓ Lihat logs di console
```

### Import Error
```bash
# Re-install dependencies
pip install -r config/requirements.txt --force-reinstall
```

---

## 📞 Support & Contact

- **Issues**: Buka di GitHub Issues
- **Discussion**: GitHub Discussions
- **Email**: techfour@example.com

---

## 📄 License

Proyek ini dilisensikan di bawah [MIT License](LICENSE) - silakan gunakan dengan bebas untuk tujuan akademik maupun komersial.

---

## 🙏 Terima Kasih

Terima kasih kepada:
- Discord.py Community
- Google DevRel team
- Mahasiswa 01TPLE04 yang berkontribusi

**Made with ❤️ by Techfour Team**

Last Updated: March 2026