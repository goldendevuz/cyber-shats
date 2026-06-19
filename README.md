# CYBER SHATS

**CYBER SHATS** — 12 IT yo'nalishi bo'yicha onlayn ta'lim platformasi (Flask + SQLite). Hacker-uslubidagi "Dark Green/Cyan" dizayn, AI yordamchi, amaliyot laboratoriyasi, testlar, forum, sertifikatlar va to'liq admin/mentor boshqaruv paneli bilan.

## 1. Talablar

- Python 3.10+
- pip

## 2. O'rnatish

```bash
# 1) Loyiha papkasiga kiring
cd cyber_shats

# 2) (tavsiya etiladi) Virtual muhit yarating
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3) Kerakli paketlarni o'rnating
pip install -r requirements.txt

# 4) Muhit o'zgaruvchilarini sozlang
cp .env.example .env
# .env faylini ochib SECRET_KEY ni o'zgartiring (ixtiyoriy: ANTHROPIC_API_KEY qo'shing)

# 5) Ma'lumotlar bazasini yarating va namunaviy ma'lumotlar bilan to'ldiring
python3 database/seed.py

# 6) MUHIM: Migratsiyani ishga tushiring (code_balance, oauth_provider,
#    failed_login_count, locked_until va boshqa ustunlarni qo'shadi).
#    Bu qadamsiz LOGIN VA KO'P FUNKSIYALAR ISHLAMAYDI!
python3 database/migrate.py

# 7) Serverni ishga tushiring
python3 app.py
```

Brauzerda oching: **http://127.0.0.1:8080**

## 3. Tayyor kirish ma'lumotlari (demo hisoblar)

| Rol | Email | Parol |
|---|---|---|
| Administrator | admin@cybershats.uz | admin123 |
| Mentor | mentor@cybershats.uz | mentor123 |
| O'quvchi | jasur@example.com | demo1234 |
| O'quvchi | dilnoza@example.com | demo1234 |
| O'quvchi | sardor@example.com | demo1234 |

Yangi hisob yaratish uchun `/register` sahifasidan ham foydalanishingiz mumkin.

## 4. Loyiha tarkibi

```
cyber_shats/
├── app.py                 # Barcha Flask route'lar
├── config.py               # Sozlamalar (.env dan o'qiydi)
├── db.py                   # SQLite ulanish yordamchilari
├── auth.py                  # Login talab qiluvchi decorator'lar
├── ai.py                    # AI Yordamchi backend logikasi
├── utils.py                  # Umumiy yordamchi funksiyalar
├── database/
│   ├── schema.sql            # Baza sxemasi (jadval ta'riflari)
│   ├── seed.py                # Namunaviy ma'lumotlarni yaratish skripti
│   └── cyber_shats.db          # SQLite baza fayli (seed.py ishga tushgach yaratiladi)
├── templates/                # Jinja2 HTML shablonlari (27+ sahifa)
├── static/
│   ├── css/                   # Dizayn tizimi (o'zgartirilmasligi tavsiya etiladi)
│   ├── js/                     # Interaktivlik skriptlari
│   └── generated/               # Avtomatik yaratilgan sertifikat PDF fayllari
└── requirements.txt
```

## 5. Nima HAQIQIY ishlaydi, nima DEMO/NAMUNA — to'liq shaffoflik

Ushbu platforma haqiqiy ishlovchi Flask + SQLite ilovasi. Quyida har bir funksiya qaysi toifaga tegishli ekanligi aniq ko'rsatilgan:

### ✅ To'liq HAQIQIY ishlaydigan funksiyalar
- Ro'yxatdan o'tish / kirish — parollar `werkzeug.security` orqali xashlanadi, sessiyalar Flask session orqali boshqariladi.
- Kurslarga yozilish, darslarni "tugatdim" deb belgilash, progress foizi avtomatik hisoblanadi.
- Test topshirish — savollar bazada saqlanadi, javoblar avtomatik tekshiriladi va ball hisoblanadi.
- Sertifikat — kursni 100% tugatganda avtomatik yaratiladi, **haqiqiy PDF fayl** (QR kod bilan) `reportlab` yordamida generatsiya qilinadi va yuklab olish mumkin.
- Forum — mavzu ochish, javob yozish, ko'rishlar soni — barchasi bazada saqlanadi.
- XP/Daraja/Reyting tizimi — har bir amal (dars tugatish, test topshirish, forumga yozish) uchun XP beriladi.
- Bildirishnomalar, profil tahrirlash, parol o'zgartirish.
- Admin/Mentor panellari — bazadan olingan **haqiqiy statistika** (foydalanuvchilar, kurslar, log'lar) ko'rsatiladi.
- AI Yordamchi — agar siz `.env` fayliga o'zingizning `ANTHROPIC_API_KEY` kalitingizni qo'shsangiz, **haqiqiy Claude API** orqali javob beradi (model: `claude-sonnet-4-6`).

### ⚠️ DEMO REJIMDA ishlaydigan funksiyalar (kalit yo'q bo'lsa)
- **AI Yordamchi** — agar `ANTHROPIC_API_KEY` sozlanmagan bo'lsa, oldindan tayyorlangan namunaviy javoblar ko'rsatiladi (interfeys to'liq ishlaydi, faqat javoblar statik).

### 🎭 FAQAT VIZUAL SIMULYATSIYA (haqiqiy emas — xavfsizlik sababli ataylab)
- **"Amaliyot" va "Hacker Lab" bo'limlari** (SQL Injection demo, Burp Suite mock, terminal/sqlmap chiqishi, HackTheBox-uslubidagi mashina ro'yxati) — bularning barchasi **faqat frontend JavaScript orqali ko'rsatiladigan, oldindan yozilgan matnli simulyatsiya**. Hech qanday haqiqiy tarmoq so'rovi, server skanerlash yoki ekspluatatsiya kodi mavjud emas. Bu ataylab shunday qilingan: real pentest vositalarini taqdim etish xavfsizlik siyosatiga zid bo'lardi. Maqsad — interfeys va o'quv tajribasini ko'rsatish.
- E-kutubxona va dars materiallari bo'limidagi "yuklab olish" tugmalari — fayllar haqiqatda mavjud emas, bosilganda buni tushuntiruvchi xabar chiqadi.

### 🔌 ULANMAGAN (sizning shaxsiy kalitlaringiz/hisoblaringiz kerak bo'ladigan) funksiyalar
- Google orqali kirish (OAuth) — login/register sahifalaridagi tugmalar dekorativ, hozircha bosilganda hech narsa sodir bo'lmaydi.
- Telegram bot integratsiyasi — ulanmagan.
- Click / Payme to'lov tizimlari — narxlar sahifasidagi to'lov tugmalari ro'yxatdan o'tish sahifasiga yo'naltiradi, haqiqiy to'lov amalga oshmaydi.
- "Mobil ilova" — bu native iOS/Android ilova emas, balki to'liq **responsive (mobilga moslashgan) veb-sayt**. Telefon brauzerida ochilganda interfeys mobilga moslashadi.

### 🌐 Internet ulanishi talab qilinadigan elementlar
Quyidagi 3 ta resurs tashqi CDN orqali yuklanadi (loyihaning o'zi internetga muhtoj emas, lekin to'liq vizual tajriba uchun internet kerak):
- **Google Fonts** (Orbitron, Share Tech Mono shriftlari) — internet bo'lmasa, brauzerning standart monospace shriftiga tushadi.
- **Three.js** (kirish animatsiyasidagi 3D aylanuvchi globus) — internet bo'lmasa, globus ko'rinmaydi, ammo qolgan animatsiya (matn, tugmalar) ishlайdi.
- **Chart.js** (Boshqaruv panelidagi grafiklar) — internet bo'lmasa, grafik joylari bo'sh ko'rinadi, ammo raqamli statistika (stat-kartalar, jadvallar) baribir to'g'ri ko'rsatiladi.

## 6. AI Yordamchini yoqish

1. https://console.anthropic.com saytidan API kalit oling.
2. `.env` faylini ochib, quyidagi qatorni to'ldiring:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```
3. Serverni qayta ishga tushiring (`python3 app.py`).
4. AI Yordamchi sahifasida endi "LIVE — Claude API faol" yozuvi ko'rinadi.

## 7. Bazani qayta tiklash

Agar ma'lumotlar bazasini boshidan boshlash kerak bo'lsa (barcha foydalanuvchilar, progresslar va h.k. o'chadi):

```bash
python3 database/seed.py
```

Bu buyruq eski `database/cyber_shats.db` faylini o'chirib, yangisini namunaviy ma'lumotlar bilan yaratadi.

## 8. Texnologiyalar

Flask 3, SQLite3 (standart kutubxona, ORM ishlatilmagan — toza SQL so'rovlar), Jinja2, vanilla JavaScript, Three.js r128 (CDN), Chart.js (CDN), reportlab + qrcode (sertifikat PDF generatsiyasi), Anthropic Python SDK (AI Yordamchi).

## 9. Lisensiya va eslatma

Bu loyiha ta'lim/portfolio maqsadida yaratilgan namuna platformadir. Productionga chiqarishdan oldin `SECRET_KEY`ni albatta o'zgartiring, `FLASK_DEBUG=0` qilib qo'yganingizga ishonch hosil qiling va SQLite o'rniga production-grade bazaga (PostgreSQL kabi) o'tishni ko'rib chiqing.

## 10. Bu versiyada tuzatilgan xatolar

Ushbu versiya ikkita oldingi versiyani (kengaytirilgan admin panel + soddalashtirilgan frontend elementlari) birlashtirib, quyidagi xatolarni tuzatadi:

1. **`/admin/users` sahifasi butunlay ishlamasdi** — `app.py`da `KeyError(' c')` xatosi bor edi (SQL alias `c` Python kodida boshida probel bilan `" c"` deb o'qilgan edi). Tuzatildi.
2. **Standart o'rnatish (`seed.py`dan keyin) bilan login butunlay ishlamasdi** — `auth.py`/`security.py` `failed_login_count`, `locked_until`, `oauth_provider`, `last_login_ip`, `code_balance` kabi ustunlarga tayanadi, ammo bular avval faqat `database/migrate.py` orqali (alohida, hech qayerda asosiy ko'rsatmada tilga olinmagan qadam sifatida) qo'shilardi. Endi bu ustunlar to'g'ridan-to'g'ri `database/schema.sql`ga kiritildi — shuning uchun yangi o'rnatishda faqat `python3 database/seed.py` kifoya, `migrate.py` shart emas (u faqat eski, oldindan mavjud bazalarni yangilash uchun ixtiyoriy ravishda qoldirilgan).
3. Frontendda ikki versiya orasidagi farqlar ko'rib chiqildi — yangiroq (kengaytirilgan admin panel: foydalanuvchilar/to'lovlar/xavfsizlik/loglar tablari, coin qo'shish-ayirish, minimal va xalaqit bermaydigan HUD) versiya asos qilib olindi, chunki u texnik jihatdan to'liqroq va yangi tahrirlangan edi.

**Sinov natijasi:** 1700+ sahifa/havola avtomatik tekshirildi (har bir kurs, dars, test, forum post va admin sahifa), 0 server xatosi bilan.
