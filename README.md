# 🛡 SHATS.KIBER v3.0 — To'liq O'rnatish Qo'llanmasi

**"O'rgan, Amaliyot Qil, Professional Bo'l"**

---

## ⚡ Tezkor Ishga Tushirish (PyCharm)

### 1-qadam: Paketlarni o'rnatish
```bash
pip install -r requirements.txt
```

### 2-qadam: .env faylini sozlash
```bash
cp .env.example .env
```
Keyin `.env` faylini oching va quyidagilarni to'ldiring:
- `SECRET_KEY` — kamida 32 ta tasodifiy belgi
- `SUPERADMIN_PASSWORD` — kuchli parol
- `ANTHROPIC_API_KEY` — https://console.anthropic.com dan oling (AI uchun)
- `TELEGRAM_BOT_TOKEN` — @BotFather dan yarating (ixtiyoriy)

### 3-qadam: Ishga tushirish
**PyCharm da:** `run.py` → ▶ Run

**Terminalda:**
```bash
python run.py
```

### 4-qadam: Brauzerda ochish
- 🌐 Sayt: http://localhost:5000
- 👑 Admin: http://localhost:5000/admin.html
- 🔐 Login: `superadmin` | Parol: `.env`dagi `SUPERADMIN_PASSWORD`

---

## 📁 Loyiha Tuzilmasi

```
shats_kiber/
├── run.py                ← PyCharm da bu faylni ishga tushiring
├── .env                  ← .env.example dan nusxa oling (GITga yuklamang!)
├── .env.example          ← Muhit o'zgaruvchilari namunasi
├── requirements.txt      ← Python paketlari
├── README.md
│
├── backend/
│   ├── app.py            ← Asosiy Flask server (barcha API endpointlar)
│   ├── auth.py           ← Login, JWT, IP bloklash
│   ├── database.py       ← SQLite, 19 jadval
│   ├── telegram_bot.py   ← Telegram bot integratsiyasi
│   └── knowledge_base.md ← AI uchun bilim bazasi (o'zgartirish mumkin)
│
├── frontend/
│   ├── login.html        ← Kirish sahifasi
│   ├── register.html     ← Ro'yxatdan o'tish
│   ├── dashboard.html    ← Foydalanuvchi paneli
│   └── admin.html        ← Superadmin paneli
│
└── database/
    └── shats.db          ← Avtomatik yaratiladi (GITga yuklamang!)
```

---

## 🔌 API Endpointlar

### Auth
| Method | URL | Tavsif |
|--------|-----|--------|
| POST | `/api/login` | Kirish (JWT token olish) |
| POST | `/api/logout` | Chiqish (token bekor qilish) |
| POST | `/api/register` | Ro'yxatdan o'tish so'rovi |
| GET | `/api/me` | Joriy foydalanuvchi ma'lumotlari |

### FREE asboblar
| Method | URL | Tavsif |
|--------|-----|--------|
| POST | `/api/scan/ping` | Ping test |
| POST | `/api/scan/dns` | DNS lookup |
| POST | `/api/scan/ports` | Port scanner (FREE: 20 port) |

### PRO asboblar
| Method | URL | Tavsif |
|--------|-----|--------|
| POST | `/api/ai/cyber` | SHATS Cyber AI |
| POST | `/api/ai/code` | SHATS Code AI |
| POST | `/api/pro/generate-hash` | Hash generatsiya |
| POST | `/api/pro/hash-crack` | Hash crack (wordlist) |
| POST | `/api/pro/jwt-analyze` | JWT tahlil |
| POST | `/api/pro/rsa-generate` | RSA kalit yaratish |
| POST | `/api/pro/subdomain-scan` | Subdomain scanner |
| GET | `/api/pro/xss-payloads` | XSS payloadlar |
| POST | `/api/pro/osint/email` | Email OSINT |

### Admin (superadmin only)
| Method | URL | Tavsif |
|--------|-----|--------|
| GET | `/api/admin/dashboard` | Statistika |
| GET | `/api/admin/users` | Barcha foydalanuvchilar |
| GET | `/api/admin/requests` | Kutayotgan so'rovlar |
| POST | `/api/admin/approve` | Tasdiqlash + login/parol berish |
| POST | `/api/admin/reject` | Rad etish |
| POST | `/api/admin/block-user` | Bloklash |
| POST | `/api/admin/unblock-user` | Blokdan chiqarish |
| POST | `/api/admin/upgrade-pro` | PRO ga o'tkazish |
| POST | `/api/admin/downgrade-free` | FREE ga tushirish |
| GET | `/api/admin/pro-users` | PRO foydalanuvchilar |
| GET | `/api/admin/blocked-ips` | Bloklangan IP lar |
| POST | `/api/admin/unblock-ip` | IP blokdan chiqarish |
| GET | `/api/admin/logs` | Audit loglar |
| GET | `/api/admin/monitor` | Real vaqt monitoring |
| POST | `/api/admin/announce` | E'lon yuborish (WebSocket) |
| GET | `/api/admin/telegram-messages` | Telegram xabarlar |
| POST | `/api/admin/telegram-reply` | Telegram javob |

---

## 💰 Versiyalar

| | FREE | PRO (150,000 so'm/oy) |
|--|------|----------------------|
| Ping, DNS, Port scanner | ✅ 20 port | ✅ 65535 port |
| Nazariy darslar | ✅ | ✅ |
| SHATS Cyber AI | ❌ | ✅ |
| SHATS Code AI | ❌ | ✅ |
| AI xotira (8 ta savol) | ❌ | ✅ |
| Hash yaratish/crack | ❌ | ✅ |
| JWT tahlil | ❌ | ✅ |
| RSA kalit yaratish | ❌ | ✅ |
| Subdomain scanner | ❌ | ✅ |
| XSS payloadlar | ❌ | ✅ |
| OSINT email | ❌ | ✅ |

---

## 🔐 Xavfsizlik Xususiyatlari

- **JWT + revoke:** Logout qilganda token bekor qilinadi
- **bcrypt:** Parollar bcrypt bilan hash qilingan
- **IP bloklash:** 3 marta xato → avtomatik blok
- **Input sanitizatsiya:** bleach orqali XSS himoya
- **CORS:** Faqat `ALLOWED_ORIGINS` ga ruxsat
- **Security headers:** CSP, X-Frame-Options, HSTS, Referrer-Policy
- **SQLite WAL + Foreign Keys:** Ma'lumotlar yaxlitligi
- **Host injection himoya:** Regex bilan xavfli belgilar bloklash

---

## 📱 Telegram Bot Sozlash

1. @BotFather ga `/newbot` yozing → token oling
2. `.env` faylida `TELEGRAM_BOT_TOKEN` ga token yozing
3. Sizning Telegram ID ni bilib oling: @userinfobot → `/start`
4. `TELEGRAM_ADMIN_ID` ga ID yozing
5. Serverni qayta ishga tushiring

---

## ⚠️ Tuzatilgan Xatolar (v3.0)

1. **`admin_pro_users()`** — `@app.route` dekoratori yo'q edi → qo'shildi
2. **eventlet monkey_patch** — WebSocket to'g'ri ishlashi uchun birinchi qo'shildi
3. **`async_mode='threading'` → `'eventlet'`** — eventlet bilan mos keltirildi
4. **`connect-src wss: ws:`** — CSP headerda ws: qo'shildi (lokal WebSocket uchun)
5. **`run.py`** — PyCharm uchun alohida ishga tushirish fayli
6. **`python-dotenv`** — `.env` fayli avtomatik yuklanadi

---

## 🚀 Deploy (Ishlab Chiqarish)

```bash
# .env ni sozlang
SECRET_KEY=<32+ tasodifiy belgi>
SUPERADMIN_PASSWORD=<kuchli parol>
FLASK_DEBUG=false
ALLOWED_ORIGINS=https://yourdomain.com

# Gunicorn + eventlet
pip install gunicorn
gunicorn --worker-class eventlet -w 1 -b 0.0.0.0:5000 backend.app:app
```

> ⚠️ Ishlab chiqarishda HTTPS (TLS/SSL) SHART. Let's Encrypt bepul sertifikat beradi.

---

*SHATS.KIBER © 2026 — O'zbekiston kiberxavfsizlik platformasi*
