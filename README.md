# Techfour Discord Bot 🤖

Bot Discord berbasis **AI multi-engine** dengan integrasi **Google Gemini**, dirancang untuk mendukung **pembelajaran dan manajemen komunitas**.  
📍 **Kelas 01TPLE04 – Teknik Informatika, Universitas Pamulang**

---

## 🚀 Deskripsi Singkat

Techfour Discord Bot adalah bot AI modular yang mampu:
- Menjawab pertanyaan akademik secara kontekstual
- Membantu diskusi coding & matematika
- Mengelola pengingat jadwal dan tugas-tugas kuliah
- Mendukung manajemen komunitas Discord berbasis AI

---

## 🌟 Fitur Utama

| Fitur | Deskripsi |
|-----|-----------|
| **AI Multi-Engine Routing** | Otomatis memilih model AI terbaik: matematika → Wolfram Alpha, coding → CodeGemma, OCR/gambar → Gemini, umum → Gemini |
| **OCR Gambar & PDF** | Ekstraksi teks dari gambar/PDF melalui mention bot + attachment |
| **Pengingat Jadwal Kuliah** | Notifikasi otomatis setiap **Jumat & Minggu pukul 08.00 WIB** |
| **Rate Limiting** | 5 request/hari (user), 10 request/hari (admin), cooldown 60 detik |
| **Sistem Jadwal Dinamis** | Parsing file `jadwal_kuliah.txt` berbasis teks |
| **Webhook Logging (Opsional)** | Logging error & aktivitas ke Discord Webhook |
| **Health Check Endpoint** | Endpoint `/health` untuk monitoring (Railway / Render) |

---

## 🧱 Teknologi yang Digunakan

- **Bahasa**: Python 3.10+
- **Framework**: discord.py
- **AI Engine**:
  - Google Gemini (LLM & OCR)
  - Wolfram Alpha (Matematika)
  - Hugging Face – CodeGemma (Coding)
- **Deployment**: Railway

---

## ⚙️ Prasyarat

Pastikan Anda telah menyiapkan:

- Python **3.10 atau lebih baru**
- Discord Bot Token (**Message Content Intent aktif**)
- File `jadwal_kuliah.txt`
- API Key:
  - Google Gemini → https://ai.google.dev/
  - Wolfram Alpha → https://developer.wolframalpha.com/
  - Hugging Face → https://huggingface.co/settings/tokens

---

### Clone Repository
```bash
git clone https://github.com/JundiLesmana/DiscordBot.git
cd DiscordBot
```

---

## 🏗️ Diagram Arsitektur
```text
┌──────────────┐
│   Discord    │
│   User       │
└──────┬───────┘
       │ Mention / Message
       ▼
┌──────────────────────┐
│   Discord Bot Core   │
│  (discord.py)       │
└──────┬──────────────┘
       │ Context Routing
       ▼
┌─────────────────────────────────────┐
│           AI Router                  │
│─────────────────────────────────────│
│ • Gemini        → General / OCR      │
│ • WolframAlpha  → Math               │
│ • CodeGemma     → Coding             │
└──────┬──────────────────────────────┘
       │
       ▼
┌──────────────────────┐
│   Response Handler   │
└──────┬──────────────┘
       │
       ▼
┌──────────────┐
│   Discord    │
│   Channel    │
└──────────────┘

Additional Services:
- Scheduler → Pengingat Kuliah
- Webhook → Logging
- /health  → Monitoring