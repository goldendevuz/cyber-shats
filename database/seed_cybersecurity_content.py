# -*- coding: utf-8 -*-
"""
CYBER SHATS V1.3 — Cyber Security kurslari uchun chuqur ta'lim materiali.

TryHackMe (https://tryhackme.com) va OverTheWire (https://overthewire.org/wargames/)
uslubidagi yondashuv: nazariy tushuntirish + amaliy mashqlar + "flag" topish
mantig'iga o'xshash bosqichma-bosqich o'rganish.

Bu skript 4 ta Cyber Security kursi (75 dars) uchun to'liq matn material yaratadi.
Video YO'Q — faqat chuqur yozma material.

Ishga tushirish: python database/seed_cybersecurity_content.py
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyber_shats.db")

# =================================================================
# KURS 9: ETHICAL HACKER (33 dars, 8 modul)
# Modul nomlari: Network Basics, Linux Fundamentals, Web Security,
# Penetration Testing, Wireless Hacking, Malware Analysis,
# Social Engineering, Final Project
# =================================================================

ETHICAL_HACKER = {
    # --- MODUL 1: Network Basics (darslar 1-4) ---
    1: """## Tarmoq Asoslari — Nima uchun xavfsizlik tarmoqdan boshlanadi

Har qanday kiberxavfsizlik mutaxassisi avvalo tarmoq qanday ishlashini tushunishi shart.
TryHackMe'dagi "Network Fundamentals" yo'li xuddi shu tartibda boshlanadi — sababi oddiy:
**hujum ham, himoya ham tarmoq orqali sodir bo'ladi.**

### OSI va TCP/IP modellari

Ma'lumot tarmoq orqali yuborilganda, u 7 ta qatlamdan (OSI) yoki amalda 4 ta qatlamdan
(TCP/IP) o'tadi:

1. **Physical** — kabel, signal
2. **Data Link** — MAC manzil, switch
3. **Network** — IP manzil, router
4. **Transport** — TCP/UDP, port
5. **Session/Presentation/Application** — HTTP, DNS, SSH va h.k.

Xavfsizlik mutaxassisi uchun eng muhim qatlamlar — **Network** (IP) va **Transport** (port),
chunki deyarli barcha skanerlash va hujum vositalari shu qatlamlarda ishlaydi.

### Nima uchun bu muhim?

Agar siz IP manzil va port nima ekanini tushunmasangiz, `nmap` natijasini o'qiy olmaysiz,
firewall qoidasini yoza olmaysiz. Keyingi darsda IP manzillash va portlar bilan chuqurroq
tanishamiz.
""",
    2: """## IP manzillash va Subnetting

### IPv4 manzil tuzilishi

IP manzil — `192.168.1.1` kabi 4 ta oktetdan (0-255) iborat. Tarmoqlar ikki turga bo'linadi:

- **Public IP** — internetda noyob, to'g'ridan-to'g'ri ko'rinadi
- **Private IP** — lokal tarmoq ichida (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`)

### Subnet mask va CIDR

`192.168.1.0/24` — bu yozuv "birinchi 24 bit tarmoq qismi, qolgan 8 bit host qismi"
degani. Bu sizga 254 ta host manzili beradi (`192.168.1.1` dan `192.168.1.254` gacha).

### Amaliy mashq (TryHackMe uslubida)

Hacker Lab panelidagi terminal orqali quyidagilarni sinab ko'ring:

```
ifconfig        # (Linux) — o'z IP manzilingizni ko'rish
ip addr show    # zamonaviy muqobil
ping 8.8.8.8    # Google DNS serverigacha bog'lanishni tekshirish
```

**Savol:** Agar sizning IP manzilingiz `192.168.1.50/24` bo'lsa, shu tarmoqdagi
boshqa qurilmalar qanday IP diapazonida bo'ladi? (Javob: `192.168.1.1` — `192.168.1.254`)
""",
    3: """## Portlar va Protokollar

### Eng muhim portlar (yodlab oling!)

| Port | Protokol | Vazifasi |
|------|----------|----------|
| 21   | FTP      | Fayl uzatish |
| 22   | SSH      | Xavfsiz masofaviy kirish |
| 23   | Telnet   | Shifrlanmagan masofaviy kirish (eski, xavfli) |
| 25   | SMTP     | Email yuborish |
| 53   | DNS      | Domen nomlarini IP'ga aylantirish |
| 80   | HTTP     | Veb-sayt (shifrlanmagan) |
| 443  | HTTPS    | Veb-sayt (shifrlangan) |
| 3306 | MySQL    | Ma'lumotlar bazasi |
| 3389 | RDP      | Windows masofaviy ish stoli |

### Nima uchun port skanerlash muhim?

Penetration tester birinchi navbatda **qaysi portlar ochiq** ekanini biladi — bu unga
qaysi xizmatlar ishlayotganini va potentsial zaifliklarni ko'rsatadi. Keyingi modulda
(Linux Fundamentals) buni amaliy tarzda Hacker Lab terminali orqali sinab ko'rasiz.

### TCP 3-tomonlama qo'l siqish (handshake)

```
Client  --SYN-->        Server
Client  <--SYN-ACK--    Server
Client  --ACK-->        Server
```

Bu jarayonni tushunish — `nmap -sS` (SYN scan) qanday ishlashini tushunish uchun zarur.
""",
    4: """## 1-Modul Amaliyoti: Tarmoq diagnostikasi

### Mashq: Hacker Lab terminali orqali

Endi o'rganganlaringizni sinab ko'ramiz. Hacker Lab panelidagiga o'ting va quyidagi
buyruqlarni ketma-ket bajaring:

```
whoami              # joriy foydalanuvchi
ping demo-lab.local # masofaviy xostga ulanish (simulyatsiya)
nmap -sV demo-lab.local   # ochiq portlarni va xizmatlarni aniqlash
```

### Kutilgan natija

`nmap` natijasida siz 22 (SSH), 80 (HTTP), 443 (HTTPS) portlarini ko'rishingiz kerak.
Bu — odatiy veb-server konfiguratsiyasi.

### Modul yakuni — bilim tekshiruvi

- OSI modelining nechta qatlami bor? (7 ta)
- `192.168.1.0/24` tarmog'ida nechta host manzili bor? (254 ta)
- HTTPS qaysi portda ishlaydi? (443)

Keyingi modul — **Linux Fundamentals**: penetration testing uchun Linux buyruqlar
qatorini chuqur o'rganasiz.
""",

    # --- MODUL 2: Linux Fundamentals (darslar 5-9) ---
    5: """## Linux Fundamentals — Nima uchun Kali Linux?

Deyarli barcha professional penetration testerlar **Linux** asosida ishlaydi, chunki:

1. Aksariyat xavfsizlik vositalari (nmap, Metasploit, Burp Suite) Linux uchun
   optimallashtirilgan
2. Buyruqlar qatori (terminal) orqali avtomatlashtirish ancha oson
3. Kali Linux — 600+ tayyor vosita bilan keladi (Offensive Security tomonidan)

### Fayl tizimi tuzilishi

```
/            — ildiz
/home        — foydalanuvchi papkalari
/etc         — konfiguratsiya fayllari
/var/log     — log fayllar (xavfsizlik tahlili uchun muhim!)
/root        — administrator (root) uy papkasi
```

### Eng zarur buyruqlar

```
ls -la       # fayllarni ko'rish (yashirinlari bilan)
cd /path     # papka almashtirish
pwd          # joriy joylashuv
cat file.txt # fayl mazmunini ko'rish
```
""",
    6: """## Fayl ruxsatlari va foydalanuvchi boshqaruvi

### chmod va ruxsatlar tizimi

Linux'da har bir fayl uchta toifa uchun ruxsatga ega: **egasi (owner)**, **guruh (group)**,
**boshqalar (others)**. Har biri uchun: **read (r)**, **write (w)**, **execute (x)**.

```
-rwxr-xr--  1 root root 1234 fayl.sh
```

Bu yozuvni o'qish: egasi (rwx — hammasi), guruh (r-x — o'qish+bajarish), boshqalar
(r-- — faqat o'qish).

### Nega bu xavfsizlik uchun muhim?

Noto'g'ri sozlangan ruxsatlar (masalan `chmod 777`) — **eng keng tarqalgan zaiflik**.
Agar fayl hammaga yozish huquqini bersa, har qanday foydalanuvchi uni zararli kod bilan
almashtirib qo'yishi mumkin.

### Amaliy mashq

```
ls -la /etc/passwd     # bu fayl kimga tegishli, kim o'qiy oladi?
whoami                 # joriy foydalanuvchi
id                     # foydalanuvchi va guruh ID'lari
```
""",
    7: """## Bash skriptlash asoslari

Avtomatlashtirish — penetration testing'ning ajralmas qismi. Oddiy bash skript:

```bash
#!/bin/bash
echo "Skanerlash boshlandi..."
for port in 21 22 80 443; do
    echo "Port $port tekshirilmoqda"
done
```

### Nega skriptlash kerak?

100 ta xostni qo'lda tekshirish soatlab vaqt oladi. Skript bilan bir necha soniyada
bajariladi. Professional pentesterlar deyarli har doim o'z avtomatlashtirish
skriptlariga ega.

### Hacker Lab'da sinab ko'ring

Terminalda `help` yozib, qaysi buyruqlar mavjudligini ko'ring va ularni birma-bir
sinab ko'ring.
""",
    8: """## Tizim monitoring va process boshqaruvi

```
ps aux          # ishlayotgan barcha jarayonlar
top             # real-vaqt resurs monitoring
netstat -tulpn  # ochiq portlar va ularga bog'liq jarayonlar
```

### Xavfsizlik nuqtai nazaridan

Agar tizimingizda kutilmagan jarayon ishlayotgan bo'lsa (masalan, noma'lum nom bilan,
yuqori CPU sarflovchi), bu **malware** belgisi bo'lishi mumkin. `netstat` orqali
qaysi dastur qaysi portda "tinglayotganini" ko'rish — backdoor'larni aniqlashning
asosiy usuli.
""",
    9: """## 2-Modul Amaliyoti: Linux orqali tizim tahlili

### OverTheWire uslubidagi mashq

OverTheWire'ning mashhur "Bandit" wargame'i xuddi shu ko'nikmalarni sinaydi: har bir
bosqichda fayl tizimini o'rganib, keyingi darajaga o'tish uchun kerakli ma'lumotni
(parolni) topish kerak bo'ladi.

Hacker Lab terminalida:
```
ls -la
cat /etc/passwd
whoami
id
```

### Modul yakuni

- `chmod 644` qanday ruxsat beradi? (egasi: o'qish+yozish, qolganlar: faqat o'qish)
- Nima uchun `chmod 777` xavfli? (hamma yoza oladi — zararli kod joylashi mumkin)

Keyingi modul — **Web Security**: veb-ilovalardagi eng keng tarqalgan zaifliklar
(SQL Injection, XSS) bilan tanishasiz.
""",

    # --- MODUL 3: Web Security (darslar 10-15) ---
    10: """## Web Security — OWASP Top 10 bilan tanishuv

Veb-ilovalar xavfsizligi sohasida **OWASP Top 10** — eng nufuzli va keng qabul qilingan
zaifliklar ro'yxati. Bu ro'yxat har necha yilda yangilanadi va deyarli barcha
penetration testing sertifikatlari (OSCP, eJPT) shunga asoslanadi.

### Eng muhim 5 tasi:

1. **Broken Access Control** — foydalanuvchi o'ziga tegishli bo'lmagan ma'lumotga kirishi
2. **Injection (SQL, Command)** — foydalanuvchi kiritgan ma'lumot orqali kod bajarish
3. **Cross-Site Scripting (XSS)** — boshqa foydalanuvchi brauzerida skript ishga tushirish
4. **Security Misconfiguration** — noto'g'ri sozlangan server/dastur
5. **Vulnerable Components** — eskirgan, zaif kutubxonalar ishlatish

Keyingi darslarda har birini chuqur o'rganamiz.
""",
    11: """## SQL Injection — eng mashhur veb-zaiflik

### Qanday ishlaydi?

Agar veb-sayt foydalanuvchi kiritgan ma'lumotni to'g'ridan-to'g'ri SQL so'roviga
qo'shsa (filtrlashsiz), hujumchi maxsus belgilar orqali so'rovni o'zgartirib,
ma'lumotlar bazasidan ruxsatsiz ma'lumot ololadi.

### Klassik misol (faqat tushunish uchun, HAQIQIY HUJUM EMAS):

```sql
SELECT * FROM users WHERE username='admin' AND password='parol123'
```

Agar parol maydoniga `' OR '1'='1` kiritilsa va filtrlanmasa:

```sql
SELECT * FROM users WHERE username='admin' AND password='' OR '1'='1'
```

`'1'='1'` har doim TO'G'RI bo'lgani uchun, autentifikatsiya chetlab o'tiladi.

### Himoya: Parametrlangan so'rovlar (Prepared Statements)

```python
# XAVFLI:
query = f"SELECT * FROM users WHERE username='{username}'"

# XAVFSIZ:
cursor.execute("SELECT * FROM users WHERE username=?", (username,))
```

### Muhim eslatma

Bu bilim **faqat ta'lim va o'z tizimingizni himoya qilish** uchun. Ruxsatsiz boshqa
tizimga kirishga urinish — jinoiy javobgarlikka olib keladi.
""",
    12: """## Cross-Site Scripting (XSS)

### XSS turlari

1. **Reflected XSS** — zararli skript URL orqali yuboriladi, server uni
   "aks ettiradi" (qaytaradi), brauzer bajaradi
2. **Stored XSS** — zararli skript serverga saqlanadi (masalan forum izohida) va
   har bir tashrif buyuruvchi brauzerida ishga tushadi
3. **DOM-based XSS** — to'liq client-side, server hech qachon zararli ma'lumotni
   ko'rmaydi

### Nega xavfli?

XSS orqali hujumchi: foydalanuvchi cookie'sini o'g'irlashi, sahifani o'zgartirishi,
yoki foydalanuvchi nomidan amallar bajarishi mumkin.

### Himoya

- Foydalanuvchi kiritgan har qanday ma'lumotni HTML chiqarishdan oldin **escape** qilish
- Content Security Policy (CSP) header sozlash
- Zamonaviy freymvorklar (React, Vue) avtomatik escape qiladi — lekin `dangerouslySetInnerHTML`
  kabi "qochish yo'llari"dan ehtiyot bo'lish kerak
""",
    13: """## CSRF va Authentication zaifliklari

### Cross-Site Request Forgery (CSRF)

Foydalanuvchi saytga kirgan holatda, hujumchi boshqa sayt orqali foydalanuvchi nomidan
so'rov yuboradi (masalan, parolni o'zgartirish). Himoya — **CSRF token** ishlatish,
har bir muhim amalda tasdiqlash so'rash.

### Zaif autentifikatsiya belgilari

- Parol murakkabligi talab qilinmasligi
- Login urinishlari cheklanmasligi (brute-force imkoni)
- Session ID'lar URL'da ko'rinishi (cookie'da bo'lishi kerak)
- "Parolni unutdim" funksiyasida zaif tasdiqlash

### Amaliy fikr almashish

Bu mavzularni Hacker Lab'dagi "Jamoa" bo'limida boshqa o'quvchilar bilan muhokama
qiling — real loyihalarda qanday himoya qo'llaganlaringizni ulashing.
""",
    14: """## Burp Suite bilan tanishish

**Burp Suite** — veb-ilova xavfsizligini tekshirish uchun eng mashhur vosita.
Asosiy funksiyalari:

- **Proxy** — brauzer va server orasidagi trafikni ushlab turish va tahlil qilish
- **Repeater** — bitta so'rovni qayta-qayta yuborib, javoblarni solishtirish
- **Intruder** — avtomatlashtirilgan parametrларни sinash (masalan brute-force)
- **Scanner** (Pro versiyada) — avtomatik zaiflik aniqlash

### Ish jarayoni

1. Brauzer trafigini Burp orqali yo'naltirish (proxy sozlash)
2. So'rovlarni ushlab turish va tahlil qilish
3. Shubhali parametrlarni Repeater'da qo'lda sinash

Bu vosita bilan ishlash — professional penetration testing'ning kundalik amaliyoti.
""",
    15: """## 3-Modul Amaliyoti: Web Security mashqi

### Hacker Lab terminali orqali

```
sqlmap -u demo-lab.local
```

Bu buyruq sqlmap vositasining demo-simulyatsiyasini ko'rsatadi — haqiqiy so'rov
yuborilmaydi, lekin vositaning qanday ishlashini tushunish uchun foydali.

### Modul yakuni — bilim tekshiruvi

- SQL Injection'dan himoyalanishning eng yaxshi usuli? (parametrlangan so'rovlar)
- XSS nima uchun xavfli? (boshqa foydalanuvchi brauzerida kod bajaradi)
- CSRF'dan qanday himoyalanish mumkin? (CSRF token)

Keyingi modul — **Penetration Testing**: to'liq pentest metodologiyasi bilan
tanishasiz — qidiruvdan hisobotgacha.
""",

    # --- MODUL 4: Penetration Testing (darslar 16-21) ---
    16: """## Penetration Testing metodologiyasi

Professional pentest 5 bosqichdan iborat (PTES standarti asosida):

1. **Reconnaissance (razvedka)** — maqsad haqida ma'lumot yig'ish
2. **Scanning (skanerlash)** — ochiq portlar, xizmatlar, zaifliklarni aniqlash
3. **Exploitation (ekspluatatsiya)** — topilgan zaiflikdan foydalanish
4. **Post-Exploitation** — kirilgan tizimda harakat, ma'lumot yig'ish
5. **Reporting (hisobot)** — topilmalar va tavsiyalarni hujjatlashtirish

### Nega metodologiya muhim?

Tasodifiy "urinib ko'rish" professional emas. Mijoz (kompaniya) sizdan **tizimli**
yondashuv kutadi — har bir qadam hujjatlashtirilishi va asoslanishi kerak.
""",
    17: """## Reconnaissance — passiv va aktiv razvedka

### Passiv razvedka (maqsad bilmaydi)

- Google dorking (`site:example.com filetype:pdf`)
- WHOIS ma'lumotlari
- Ijtimoiy tarmoqlardan ma'lumot yig'ish (OSINT)
- DNS yozuvlarini tekshirish

### Aktiv razvedka (maqsad bilishi mumkin)

- Port skanerlash (`nmap`)
- Xizmat versiyalarini aniqlash
- Subdomenlarni qidirish

### Muhim eslatma

Aktiv razvedka **ruxsat talab qiladi**. Faqat o'zingizning yoki rasman ruxsat
berilgan tizimlarda bajaring.
""",
    18: """## Zaiflik skanerlash va tahlil

### Avtomatlashtirilgan vositalar

- **Nessus / OpenVAS** — keng qamrovli zaiflik skanerlari
- **Nikto** — veb-server zaifliklarini tekshirish
- **searchsploit** — Exploit-DB'dagi tayyor ekspluatlarni qidirish

### Qo'lda tekshirish nima uchun ham kerak?

Avtomatik skanerlar **false positive** (yolg'on signal) berishi mumkin. Professional
pentester har doim natijalarni qo'lda tasdiqlaydi, faqat avtomatik hisobotga
ishonmaydi.

### Hacker Lab terminali

```
searchsploit apache
```

Bu buyruq demo rejimda Apache uchun mavjud ekspluatlar ro'yxatini ko'rsatadi.
""",
    19: """## Metasploit Framework asoslari

**Metasploit** — eng mashhur ekspluatatsiya freymvorki, minglab tayyor modullar bilan.

### Asosiy tushunchalar

- **Exploit** — zaiflikdan foydalanish kodi
- **Payload** — exploit muvaffaqiyatli bo'lgandan keyin bajariladigan kod
- **Auxiliary** — skanerlash, fuzzing kabi yordamchi modullar

### Demo buyruq (Hacker Lab'da xavfsiz simulyatsiya)

```
msfconsole
```

Bu sizga Metasploit konsolining qanday ko'rinishini ko'rsatadi (sandbox rejimida,
haqiqiy ekspluatatsiya yo'q).

### Etika eslatmasi

Metasploit — qonuniy CTF, HackTheBox, TryHackMe kabi platformalarda yoki o'z
laboratoriyangizda ishlatilishi kerak.
""",
    20: """## Privilege Escalation (huquqlarni oshirish)

Tizimga kirgandan keyin, ko'pincha siz **cheklangan foydalanuvchi** huquqiga egasiz.
Maqsad — **root/administrator** darajasiga ko'tarilish.

### Linux'da keng tarqalgan usullar

- Noto'g'ri sozlangan **SUID** fayllar
- `sudo -l` orqali ruxsat etilgan buyruqlarni tekshirish
- Kernel zaifliklari (eski versiyalar)
- Cron job'lardagi xavfsizlik kamchiliklari

### Windows'da keng tarqalgan usullar

- Zaif xizmat ruxsatlari
- DLL Hijacking
- Token manipulatsiyasi

Bu mavzu juda chuqur — OSCP sertifikatining katta qismi shunga bag'ishlangan.
""",
    21: """## 4-Modul Amaliyoti: To'liq pentest simulyatsiyasi

### Bosqichma-bosqich mashq (Hacker Lab terminalida)

```
nmap -sV demo-lab.local        # 1. Skanerlash
searchsploit apache             # 2. Zaiflik qidirish
msfconsole                      # 3. Ekspluatatsiya vositasi
```

### Hisobot yozish ko'nikmasi

Professional pentest hisoboti quyidagilarni o'z ichiga oladi:
1. Executive Summary (boshqaruv uchun qisqacha xulosa)
2. Topilgan zaifliklar (CVSS bali bilan)
3. Har bir zaiflik uchun dalil (screenshot, log)
4. Tavsiyalar

### Modul yakuni

Endi siz to'liq pentest metodologiyasini bilasiz: razvedkadan hisobotgacha.
Keyingi modul — **Wireless Hacking**: WiFi xavfsizligi.
""",

    # --- MODUL 5: Wireless Hacking (darslar 22-24) ---
    22: """## WiFi xavfsizligi asoslari

### Shifrlash protokollari

- **WEP** — eskirgan, bir necha daqiqada buzilishi mumkin (ISHLATMANG)
- **WPA/WPA2** — keng tarqalgan, PSK (Pre-Shared Key) usulida
- **WPA3** — eng yangi, kuchliroq himoya

### Asosiy hujum turlari (faqat ta'lim uchun)

- **Deauthentication attack** — qurilmani tarmoqdan uzish (handshake olish uchun)
- **Handshake capture** — WPA2 parolni keyinchalik offline buzish uchun ushlab qolish
- **Evil Twin** — qalbaki kirish nuqtasi yaratish

Bu vositalar (`aircrack-ng`, `wifite`) faqat **o'z tarmog'ingizda yoki yozma ruxsat
bilan** ishlatilishi mumkin — boshqa birovning WiFi tarmog'iga ruxsatsiz kirish
jinoyat hisoblanadi.
""",
    23: """## Aircrack-ng to'plami bilan tanishish

### Asosiy vositalar

- `airmon-ng` — tarmoq adapterini monitor rejimiga o'tkazish
- `airodump-ng` — atrofdagi WiFi tarmoqlarni skanerlash
- `aireplay-ng` — deauth paketlarini yuborish
- `aircrack-ng` — ushlangan handshake'ni parol lug'ati bilan buzish

### Hacker Lab'da demo

```
aircrack-ng
```

Demo rejimida bu vosita haqiqiy WiFi adapter yo'qligi sababli simulyatsiya
xabarini ko'rsatadi — lekin buyruq sintaksisi bilan tanishish foydali.

### Himoya choralari

- WPA3 ishlatish (mavjud bo'lsa)
- Kuchli, uzun parol (12+ belgidan)
- WPS funksiyasini o'chirib qo'yish (ko'p marshrutizatorlarda zaif)
""",
    24: """## 5-Modul Amaliyoti: Wireless xavfsizlik tahlili

### Nazariy mashq

O'z uy WiFi tarmog'ingizni tahlil qiling (faqat O'ZINGIZNIKINI):
1. Qaysi shifrlash protokoli ishlatilgan? (router sozlamalaridan tekshiring)
2. WPS yoqilganmi?
3. Parol qanchalik kuchli?

### Modul yakuni

WiFi xavfsizligi — IoT qurilmalar ko'payishi bilan tobora muhim mavzuga aylanmoqda.
Keyingi modul — **Malware Analysis**: zararli dasturlarni tahlil qilish asoslari.
""",

    # --- MODUL 6: Malware Analysis (darslar 25-28) ---
    25: """## Malware Analysis — kirish

### Zararli dastur turlari

- **Virus** — boshqa dasturlarga "yopishadi", ko'payadi
- **Worm** — mustaqil tarqaladi, tarmoq orqali
- **Trojan** — foydali dastur niqobida yashiringan
- **Ransomware** — fayllarni shifrlab, to'lov talab qiladi
- **Spyware** — foydalanuvchi haqida ma'lumot yig'adi

### Tahlil usullari

1. **Static Analysis** — kodni bajarmasdan tahlil qilish (signature, strings)
2. **Dynamic Analysis** — izolyatsiyalangan muhitda (sandbox) ishga tushirib kuzatish

Malware tahlili **har doim izolyatsiyalangan virtual mashinada** (internet'siz)
bajarilishi shart — aks holda o'z tizimingizni zararlash xavfi bor.
""",
    26: """## Static Analysis vositalari

### Asosiy vositalar

- **strings** — fayldagi o'qiladigan matnlarni chiqarish (URL, parol, xabarlar topish
  uchun foydali)
- **file** — fayl turini aniqlash
- **Binwalk** — fayl ichidagi yashiringan ma'lumotlarni topish (firmware tahlili uchun)
- **PEiD / Detect It Easy** — Windows fayllarini tahlil qilish, "packer" aniqlash

### Hash tekshirish

Fayl hash'ini (MD5/SHA256) hisoblab, VirusTotal kabi xizmatlarda tekshirish — fayl
allaqachon ma'lum zararli dastur ekanligini aniqlashning tez usuli.
""",
    27: """## Dynamic Analysis va Sandboxing

### Nima uchun sandbox kerak?

Zararli dasturni **haqiqiy** kompyuterda ishga tushirish xavfli. Shuning uchun
maxsus izolyatsiyalangan virtual muhitlar (masalan Cuckoo Sandbox) ishlatiladi —
bu yerda dastur "ishga tushiriladi" va uning xatti-harakati (qaysi fayllarni
o'zgartiradi, qaysi tarmoq so'rovlarini yuboradi) kuzatiladi.

### Kuzatish nuqtalari

- Yangi fayllar yaratilishi
- Registry o'zgarishlari (Windows)
- Tarmoq trafigi (C2 serverga ulanish urinishi)
- Process injection
""",
    28: """## 6-Modul Amaliyoti: Malware tahlili mashqi

### Hacker Lab terminali

```
cat /etc/passwd
```

Bu demo buyruq sandbox faylida statik ma'lumot ko'rsatadi — haqiqiy tizim
ma'lumotlari emas, faqat o'rganish uchun namuna.

### Modul yakuni — bilim tekshiruvi

- Static va Dynamic Analysis farqi nima? (bajarmasdan vs bajarib kuzatish)
- Nima uchun malware tahlili izolyatsiyalangan muhitda bajariladi? (o'z tizimni
  zararlamaslik uchun)

Keyingi modul — **Social Engineering**: inson omilidan foydalanuvchi hujumlar.
""",

    # --- MODUL 7: Social Engineering (darslar 29-31) ---
    29: """## Social Engineering — eng zaif bo'g'in: inson

Statistikaga ko'ra, ko'pchilik muvaffaqiyatli kiberhujumlar texnik zaiflikdan emas,
balki **inson ishonchidan** foydalanish orqali sodir bo'ladi.

### Asosiy texnikalar

- **Phishing** — soxta email orqali ma'lumot o'g'irlash
- **Pretexting** — soxta bahona bilan ishonch qozonish (masalan "IT bo'limidan
  qo'ng'iroq qilyapman")
- **Baiting** — jozibali narsa (masalan USB flash) qoldirib, qurbonni o'zi ulashga
  undash
- **Tailgating** — ruxsat etilgan zonaga boshqa xodim ortidan kirib olish
""",
    30: """## Phishing hujumlarini aniqlash

### Shubhali belgilar

1. Jo'natuvchi manzili rasmiy domendan farq qiladi (`support@gmai1.com` — "i" o'rniga "1")
2. Shoshilinch harakat talab qilinadi ("24 soat ichida tasdiqlang yoki hisobingiz
   bloklanadi")
3. Havola matn bilan haqiqiy manzil mos kelmaydi (sichqonchani ustiga olib borib
   tekshiring)
4. Imlo xatolari, professional bo'lmagan dizayn

### Himoya — tashkilot darajasida

- Xodimlarni muntazam o'qitish (phishing simulyatsiyalari)
- Email filtrlash tizimlari
- Ikki faktorli autentifikatsiya (2FA) — parol o'g'irlansa ham qo'shimcha himoya
""",
    31: """## 7-Modul Amaliyoti: Social Engineering stsenariysi

### Nazariy mashq

Quyidagi vaziyatni tahlil qiling: Sizga "bank xodimi"dan qo'ng'iroq keladi va
"hisobingizda shubhali harakat aniqlandi, tasdiqlash uchun SMS kodingizni ayting"
deydi. Bu nima uchun shubhali?

**Javob:** Hech qachon haqiqiy bank xodimi SMS kod yoki parol so'ramaydi. Bu —
klassik **vishing** (voice phishing) hujumi.

### Modul yakuni

Social Engineering'dan himoyalanishning eng kuchli vositasi — **bilim va shubha**.
Keyingi (yakuniy) modul — **Final Project**: barcha bilimlaringizni birlashtirib,
yakuniy loyiha ustida ishlaysiz.
""",

    # --- MODUL 8: Final Project (darslar 32-33) ---
    32: """## Final Project — Yakuniy loyiha

Tabriklaymiz! Siz Ethical Hacker kursining barcha modullarini muvaffaqiyatli
o'tdingiz: Tarmoq asoslari, Linux, Web Security, Penetration Testing, Wireless
Hacking, Malware Analysis va Social Engineering.

### Yakuniy loyiha vazifasi

Hacker Lab panelidagi terminal va materiallardan foydalanib, to'liq pentest
hisobotini tuzing:

1. Reconnaissance — maqsad haqida ma'lumot
2. Scanning — ochiq portlar va xizmatlar
3. Zaifliklar ro'yxati (kamida 3 ta)
4. Tavsiyalar

Bu hisobotni Hacker Lab'dagi "Jamoa" bo'limida boshqa o'quvchilar bilan ulashing
va fikr almashing — bu real loyihalar ustida ishlash tajribasiga juda yaqin.
""",
    33: """## Kurs yakuni va keyingi qadamlar

### Siz nimalarni o'rgandingiz

- Tarmoq asoslari (OSI, TCP/IP, portlar)
- Linux buyruqlar qatori va xavfsizlik
- Web zaifliklari (SQL Injection, XSS, CSRF)
- Professional pentest metodologiyasi
- WiFi xavfsizligi
- Malware tahlili asoslari
- Social Engineering va undan himoyalanish

### Keyingi qadamlar

1. **Tarmoq Xavfsizligi Asoslari** kursiga o'ting — chuqurroq tarmoq xavfsizligi
2. **Web Ilova Xavfsizligi** kursi — OWASP Top 10'ni amaliyotda chuqur o'rganish
3. **Penetration Testing Pro** — professional darajadagi pentest

### Tashqi resurslar (qo'shimcha mashq uchun)

- **TryHackMe** (tryhackme.com) — boshlang'ichlar uchun ajoyib, bosqichma-bosqich
  yo'llar bilan
- **OverTheWire** (overthewire.org/wargames) — "wargame" uslubida, terminal orqali
  bosqichma-bosqich qiyinlashadigan mashqlar (Bandit, Natas va boshqalar)

Sertifikat olish uchun Hacker Lab panelidan sertifikat imtihoniga yoziling!
""",
}

print(f"Ethical Hacker (course_id=9): {len(ETHICAL_HACKER)} ta dars materiali tayyor")


# =================================================================
# KURS 10: TARMOQ XAVFSIZLIGI ASOSLARI (9 dars, 3 modul)
# =================================================================
NETWORK_SECURITY = {
    1: """## Firewall — birinchi himoya chizig'i

Firewall — tarmoq trafigini oldindan belgilangan qoidalar asosida filtrlash uchun
xavfsizlik devori. Ikki asosiy turi:

- **Network Firewall** — butun tarmoqni himoya qiladi (router darajasida)
- **Host-based Firewall** — bitta kompyuterni himoya qiladi (Windows Defender Firewall,
  iptables)

### Qoidalar mantig'i

Firewall qoidalari odatda **"deny by default, allow by exception"** tamoyiliga
asoslanadi — hamma narsa taqiqlangan, faqat aniq ruxsat berilgan trafik o'tadi.
""",
    2: """## VPN va shifrlangan tunnellar

VPN (Virtual Private Network) — ochiq internet orqali xavfsiz, shifrlangan
"tunnel" yaratadi. Ikki asosiy maqsad:

1. **Maxfiylik** — trafik shifrlanadi, uchinchi tomon ko'ra olmaydi
2. **Masofaviy kirish** — kompaniya tarmog'iga uzoqdan xavfsiz ulanish

### Protokollar

- **OpenVPN** — ochiq manbali, keng tarqalgan
- **WireGuard** — zamonaviy, tezroq va sodda
- **IPsec** — korporativ darajada keng ishlatiladi
""",
    3: """## 1-Modul Amaliyoti: Tarmoq Xavfsizligi Asoslari amaliyoti

Hacker Lab terminalida `nmap -sV demo-lab.local` orqali firewall ortidagi xizmatlarni
aniqlashga harakat qiling. Ochiq portlar qaysilar? Qaysi portlar yopiq yoki filtrlangan
ko'rinadi?

### Bilim tekshiruvi

VPN nima uchun kerak? Firewall qanday ishlaydi (deny by default tamoyili)?
""",
    4: """## IDS/IPS tizimlari

- **IDS (Intrusion Detection System)** — shubhali faoliyatni aniqlaydi va ogohlantiradi
- **IPS (Intrusion Prevention System)** — aniqlangan tahdidni avtomatik bloklaydi

### Mashhur vositalar

- **Snort** — ochiq manbali IDS/IPS
- **Suricata** — zamonaviy, yuqori unumdorlikka ega muqobil

Bu tizimlar imzo-asoslangan (signature-based) yoki anomaliya-asoslangan
(anomaly-based) ishlashi mumkin.
""",
    5: """## Tarmoq segmentatsiyasi va VLAN

Katta tarmoqni kichik, izolyatsiyalangan bo'limlarga (VLAN) bo'lish — xavfsizlikni
sezilarli oshiradi. Agar hujumchi bir segmentga kirsa ham, boshqa segmentlarga
o'tolmaydi (lateral movement cheklanadi).

### Zero Trust arxitekturasi

Zamonaviy yondashuv: "hech kimga ishonma, har doim tekshir" — hatto ichki tarmoqdagi
foydalanuvchi ham har bir resursga kirishda qayta autentifikatsiyadan o'tadi.
""",
    6: """## 2-Modul Amaliyoti: Tarmoq Xavfsizligi Asoslari amaliyoti

### Nazariy mashq

O'z uy yoki ish tarmog'ingizni tasavvur qiling. Uni qanday segmentlarga bo'lar
edingiz? (masalan: mehmon WiFi, ish stansiyalari, serverlar — alohida VLAN'larda)
""",
    7: """## Log tahlili va SIEM

**SIEM (Security Information and Event Management)** tizimlari — tarmoqdagi barcha
qurilmalardan log yig'ib, markazlashtirilgan tahlil qiladi.

### Mashhur vositalar

- **Splunk** — sanoat standarti, kuchli qidiruv imkoniyatlari
- **ELK Stack (Elasticsearch, Logstash, Kibana)** — ochiq manbali muqobil
- **Wazuh** — bepul, open-source SIEM/XDR

Log tahlili orqali hujumlarni **real vaqtda** yoki keyinchalik tergov paytida
aniqlash mumkin.
""",
    8: """## Incident Response asoslari

Xavfsizlik buzilishi yuz berganda, tashkilot qanday harakat qilishi kerakligini
belgilovchi jarayon — **Incident Response (IR)**. NIST standarti bo'yicha 6 bosqich:

1. **Preparation** — oldindan tayyorgarlik (jarayonlar, vositalar)
2. **Identification** — hodisani aniqlash
3. **Containment** — zararni cheklash (izolyatsiya)
4. **Eradication** — sabab va zararli kodni yo'q qilish
5. **Recovery** — tizimni qayta tiklash
6. **Lessons Learned** — sabablarni tahlil qilib, kelajakda oldini olish
""",
    9: """## 3-Modul Amaliyoti: Tarmoq Xavfsizligi Asoslari amaliyoti — Kurs yakuni

### Yakuniy bilim tekshiruvi

- IDS va IPS farqi nima?
- Zero Trust arxitekturasining asosiy g'oyasi nima?
- Incident Response'ning 6 bosqichini sanab bering

### Tabriklaymiz!

Siz Tarmoq Xavfsizligi Asoslari kursini muvaffaqiyatli yakunladingiz. Endi
firewall, VPN, IDS/IPS, segmentatsiya va incident response asoslarini bilasiz.
Keyingi qadam — **Web Ilova Xavfsizligi** kursida amaliy zaifliklarni chuqurroq
o'rganing.
""",
}

print(f"Tarmoq Xavfsizligi Asoslari (course_id=10): {len(NETWORK_SECURITY)} ta dars")


# =================================================================
# KURS 11: WEB ILOVA XAVFSIZLIGI (18 dars, 3 modul)
# =================================================================
WEB_APP_SECURITY = {
    1: """## Web Asoslari — HTTP protokoli chuqur

HTTP so'rov-javob (request-response) modeliga asoslangan. Asosiy metodlar:

- **GET** — ma'lumot olish
- **POST** — yangi ma'lumot yuborish
- **PUT/PATCH** — mavjud ma'lumotni yangilash
- **DELETE** — ma'lumotni o'chirish

### HTTP Headers

`Authorization`, `Cookie`, `Content-Type` kabi sarlavhalar so'rov haqida qo'shimcha
ma'lumot beradi — xavfsizlik tahlilida bularni ko'rib chiqish muhim.
""",
    2: """## Cookie va Session boshqaruvi

Veb-sayt foydalanuvchini "eslab qolish" uchun **cookie** ishlatadi. Xavfsiz cookie
quyidagi atributlarga ega bo'lishi kerak:

- **HttpOnly** — JavaScript orqali o'qib bo'lmaydi (XSS'dan himoya)
- **Secure** — faqat HTTPS orqali yuboriladi
- **SameSite** — CSRF hujumlaridan himoya qiladi

Agar bu atributlar yo'q bo'lsa, session token osongina o'g'irlanishi mumkin.
""",
    3: """## Web zaifliklarni qidirish metodologiyasi

1. Saytning barcha funksiyalarini xaritalash (mapping)
2. Har bir kirish nuqtasini (input) aniqlash
3. Har bir parametrni turli usullarda sinash
4. Server javoblarini tahlil qilish

Bu jarayon Burp Suite kabi vositalar bilan ancha tezlashadi.
""",
    4: """## Authentication zaifliklari chuqur

### Brute-force va himoya

Agar login sahifasida urinishlar soni cheklanmagan bo'lsa, hujumchi avtomatik
skript bilan minglab parol kombinatsiyasini sinab ko'rishi mumkin.

### Himoya choralari

- Urinishlar sonini cheklash (rate limiting)
- CAPTCHA qo'shish
- Hisobni vaqtinchalik bloklash (lockout)
- 2FA (ikki faktorli autentifikatsiya)
""",
    5: """## Insecure Direct Object Reference (IDOR)

Agar URL `example.com/order?id=1001` ko'rinishida bo'lsa va siz `id=1002` ga
o'zgartirib, boshqa foydalanuvchining buyurtmasini ko'rsangiz — bu **IDOR**
zaifligi.

### Himoya

Har bir so'rovda server **albatta** tekshirishi kerak: "bu foydalanuvchi haqiqatan
ham shu ID'ga tegishli ma'lumotga kirish huquqiga egami?"
""",
    6: """## 1-Modul Amaliyoti: Web Ilova Xavfsizligi amaliyoti

Hacker Lab terminalida `sqlmap -u demo-lab.local` orqali demo skanerlashni
sinab ko'ring. IDOR va Authentication zaifliklari haqida bilganlaringizni
"Jamoa" bo'limida muhokama qiling.
""",
    7: """## File Upload zaifliklari

Agar sayt foydalanuvchiga fayl yuklashga ruxsat bersa va fayl turini to'g'ri
tekshirmasa, hujumchi `.php` yoki `.jsp` kabi bajariladigan faylni yuklab,
serverda kod bajarishi mumkin.

### Himoya

- Fayl kengaytmasi va MIME turini qattiq tekshirish
- Yuklangan fayllarni bajarilmaydigan papkada saqlash
- Fayl nomini tasodifiy generatsiya qilish
- Fayl hajmini cheklash
""",
    8: """## Server-Side Request Forgery (SSRF)

Agar server foydalanuvchi bergan URL'ga so'rov yuborsa (masalan rasm yuklash uchun),
hujumchi bu URL'ni serverning ichki tarmog'iga (`http://localhost:8080/admin`)
yo'naltirib, ichki resurslarga kirishi mumkin.

### Himoya

Server tomonidan yuboriladigan URL'larni qat'iy whitelist orqali cheklash.
""",
    9: """## XML va API xavfsizligi

### XXE (XML External Entity)

Noto'g'ri sozlangan XML parser orqali server fayl tizimidan ma'lumot o'qishga
majburlanishi mumkin.

### API xavfsizligi

- Har bir endpoint uchun autentifikatsiya
- Rate limiting (DDoS'dan himoya)
- Input validatsiya
- API kalitlarini hech qachon frontend kodida ko'rsatmaslik
""",
    10: """## 2-Modul Amaliyoti: Web Ilova Xavfsizligi amaliyoti

### Nazariy mashq

Agar siz fayl yuklash funksiyasini loyihalashtirsangiz, qanday xavfsizlik
choralarini qo'llagan bo'lardingiz? Ro'yxat tuzing (kamida 4 ta chora).
""",
    11: """## Security Headers — HTTP sarlavhalari orqali himoya

### Muhim sarlavhalar

- `Content-Security-Policy` — qaysi manbalardan skript yuklash mumkinligini cheklaydi
- `X-Frame-Options` — clickjacking hujumlaridan himoya
- `Strict-Transport-Security` — faqat HTTPS orqali ulanishni majburlaydi
- `X-Content-Type-Options: nosniff` — brauzerni fayl turini "taxmin qilish"dan saqlaydi

Bu sarlavhalar to'g'ri sozlansa, ko'p hujum turlarining oldini oladi.
""",
    12: """## 2-Modul Amaliyoti: Web Ilova Xavfsizligi amaliyoti (davomi)

Security Headers'ni real saytlarda tekshirish uchun `securityheaders.com` kabi
xizmatlar mavjud. O'z loyihangiz uchun qaysi sarlavhalar zarurligini aniqlang.
""",
    13: """## API Security chuqur — OAuth va JWT

### OAuth 2.0

Uchinchi tomon ilovalarga foydalanuvchi ma'lumotlariga **cheklangan** kirish
huquqini berish protokoli (masalan "Google orqali kirish").

### JWT (JSON Web Token)

Autentifikatsiya ma'lumotlarini xavfsiz uzatish uchun ishlatiladigan token formati.
Muhim: JWT **shifrlangan emas**, faqat imzolangan — maxfiy ma'lumotni JWT ichida
saqlamaslik kerak.
""",
    14: """## Rate Limiting va DDoS himoyasi

Agar API yoki login sahifasiga cheksiz so'rov yuborish mumkin bo'lsa, bu DDoS yoki
brute-force hujumlariga yo'l ochadi.

### Himoya strategiyalari

- IP-asoslangan rate limiting
- CAPTCHA qo'shish
- CDN/WAF (Web Application Firewall) ishlatish — Cloudflare kabi xizmatlar
""",
    15: """## 3-Modul Amaliyoti: Web Ilova Xavfsizligi amaliyoti

### Nazariy mashq

JWT va session-cookie autentifikatsiyasining afzallik va kamchiliklarini
solishtiring.
""",
    16: """## Secure Development Lifecycle (SDLC)

Xavfsizlik dasturlash jarayonining **boshidan oxirigacha** integratsiya qilinishi
kerak ("Shift Left" tamoyili):

1. Talablar bosqichida xavfsizlik talablari belgilanadi
2. Dizayn bosqichida threat modeling o'tkaziladi
3. Kodlash bosqichida xavfsiz kodlash standartlariga rioya qilinadi
4. Test bosqichida xavfsizlik testlari (SAST/DAST) bajariladi
5. Deploy bosqichida konfiguratsiya tekshiriladi
""",
    17: """## Code Review xavfsizlik nuqtai nazaridan

Har bir kod o'zgarishi nashr etilishidan oldin xavfsizlik nuqtai nazaridan
tekshirilishi kerak:

- Foydalanuvchi kiritgan ma'lumot to'g'ri filtrlanganmi?
- Maxfiy kalitlar (API key, parol) kodda qattiq yozilmaganmi?
- Yangi kutubxonalar zaif versiyalarda emasmi?
""",
    18: """## 3-Modul Amaliyoti: Web Ilova Xavfsizligi amaliyoti — Kurs yakuni

### Yakuniy bilim tekshiruvi

- IDOR nima va undan qanday himoyalanish mumkin?
- SSRF qanday ishlaydi?
- SDLC'da xavfsizlik qaysi bosqichlarda integratsiya qilinadi?

### Tabriklaymiz!

Web Ilova Xavfsizligi kursini yakunladingiz — endi OWASP Top 10'ning aksariyat
zaifliklarini chuqur tushunasiz. Keyingi qadam: **Penetration Testing Pro** —
professional darajadagi to'liq pentest loyihasi.
""",
}

print(f"Web Ilova Xavfsizligi (course_id=11): {len(WEB_APP_SECURITY)} ta dars")


# =================================================================
# KURS 12: PENETRATION TESTING PRO (15 dars, 3 modul)
# =================================================================
PENTEST_PRO = {
    1: """## Pentest Pro — Professional metodologiya (PTES/OSSTMM)

Professional darajada pentest **standartlashtirilgan metodologiya**ga asoslanadi:

- **PTES (Penetration Testing Execution Standard)**
- **OSSTMM (Open Source Security Testing Methodology Manual)**
- **NIST SP 800-115**

Bu standartlar mijoz bilan **scope** (qamrov chegarasi) kelishuvidan boshlab,
hisobot topshirishgacha bo'lgan jarayonni belgilaydi.
""",
    2: """## Scope va Rules of Engagement (RoE)

Har qanday qonuniy pentest **yozma kelishuv** bilan boshlanadi:

- Qaysi tizimlar test qilinadi (va qaysilari **taqiqlangan**)
- Qaysi vaqt oralig'ida ishlash mumkin
- Qanday hujum turlari ruxsat etilgan (masalan DoS odatda taqiqlanadi)
- Favqulodda holatda kim bilan bog'lanish kerak

**RoE'siz pentest qilish — hatto yaxshi niyat bilan bo'lsa ham — jinoiy
javobgarlikka olib kelishi mumkin.**
""",
    3: """## Advanced Reconnaissance texnikalari

### OSINT chuqur

- **Shodan** — internetga ulangan qurilmalarni qidiruvchi tizim
- **theHarvester** — email, subdomen, IP yig'ish vositasi
- **Maltego** — vizual aloqalar xaritasini tuzish

Professional darajada razvedka bosqichi butun pentest vaqtining 30-40%ini
egallashi mumkin — sifatli razvedka muvaffaqiyatli ekspluatatsiya ehtimolini
sezilarli oshiradi.
""",
    4: """## Advanced Exploitation texnikalari

### Exploit Development asoslari

Tayyor ekspluatlardan tashqari, professional pentesterlar ba'zan **o'zlari**
ekspluat yozadilar:

- Buffer overflow tushunish
- Zaiflikni "fuzzing" orqali topish
- Debugger (masalan GDB) bilan ishlash

Bu — eng murakkab ko'nikma, odatda OSCE/OSED kabi yuqori darajadagi
sertifikatlar shu mavzuga bag'ishlangan.
""",
    5: """## 1-Modul Amaliyoti: Penetration Testing Pro amaliyoti

Hacker Lab terminalida to'liq zanjirni sinab ko'ring:
```
nmap -sV demo-lab.local
searchsploit apache
msfconsole
```

RoE va Scope nima uchun har doim yozma bo'lishi kerakligini tushuntiring.
""",
    6: """## Active Directory Pentest asoslari

Ko'pchilik korporativ tarmoqlar **Active Directory (AD)** asosida boshqariladi.
AD pentest maxsus ko'nikmalar talab qiladi:

- **Kerberoasting** — xizmat hisoblari uchun hash olish
- **Pass-the-Hash** — parolni bilmasdan, hash orqali autentifikatsiya
- **Golden Ticket** — domen administratoridek harakat qilish imkoni beruvchi hujum

Bu mavzular juda chuqur va odatda alohida ixtisoslashgan kurslar talab qiladi.
""",
    7: """## Cloud Penetration Testing

Zamonaviy tashkilotlar AWS, Azure, GCP kabi bulutli platformalarda ishlaydi.
Cloud pentest o'ziga xos xususiyatlarga ega:

- IAM (Identity and Access Management) noto'g'ri konfiguratsiyasi
- Ochiq S3 bucket'lar (ma'lumotlar oshkor bo'lishi)
- Zaif API Gateway sozlamalari

Har bir bulut provayder o'zining **pentest siyosati**ga ega — ba'zi testlar
oldindan ruxsat talab qiladi.
""",
    8: """## Container va Kubernetes xavfsizligi

Docker va Kubernetes keng tarqalishi bilan, ularning xavfsizligi ham muhim
mavzuga aylandi:

- Noto'g'ri sozlangan konteyner imtiyozlari (privileged mode)
- Zaif image'lar (eskirgan kutubxonalar)
- Kubernetes RBAC (Role-Based Access Control) xatolari
""",
    9: """## 2-Modul Amaliyoti: Penetration Testing Pro amaliyoti

### Nazariy mashq

Agar siz kompaniyaning AWS infratuzilmasini pentest qilsangiz, birinchi
navbatda nimalarni tekshirgan bo'lardingiz? Ro'yxat tuzing.
""",
    10: """## Red Team vs Penetration Testing

### Farqi nimada?

- **Penetration Testing** — belgilangan vaqt va qamrovda, barcha zaifliklarni
  topishga harakat qiladi
- **Red Team** — uzoqroq muddatda, **maxfiy** tarzda, real hujumchi kabi
  harakat qiladi, maqsad — Blue Team (himoya jamoasi)ning aniqlash qobiliyatini
  sinash

Red Team mashqlari ko'pincha "Purple Team" formatida — hujum va himoya
jamoalari birga ishlab, bilim almashadi.
""",
    11: """## Threat Intelligence va MITRE ATT&CK

**MITRE ATT&CK** — haqiqiy hujumchilar ishlatadigan taktika va texnikalarning
keng qamrovli bazasi. Professional pentesterlar va Red Team a'zolari o'z
hujumlarini shu freymvorkka moslashtiradi — bu natijalarni standartlashtirish va
himoya jamoasi bilan umumiy til topishga yordam beradi.
""",
    12: """## 2-Modul Amaliyoti: Penetration Testing Pro amaliyoti

Red Team va oddiy Penetration Testing farqini "Jamoa" bo'limida muhokama qiling —
qaysi vaziyatda qaysi yondashuv ko'proq mos kelishini fikr almashing.
""",
    13: """## Professional hisobot yozish

Pentest natijasi qanchalik yaxshi bo'lmasin, agar hisobot tushunarsiz bo'lsa,
mijoz uni qadrlay olmaydi. Yaxshi hisobot tuzilishi:

1. **Executive Summary** — boshqaruv uchun, texnik bo'lmagan til bilan
2. **Metodologiya** — qanday yondashuv qo'llanilgani
3. **Topilmalar** — har biri uchun: tavsif, dalil, CVSS bali, tavsiya
4. **Ilovalar** — to'liq texnik tafsilotlar

### CVSS (Common Vulnerability Scoring System)

Zaiflik jiddiyligini 0-10 ball oralig'ida standartlashtirilgan baholash tizimi.
""",
    14: """## Karyera yo'li — Pentest sohasida sertifikatlar

### Tan olingan sertifikatlar

- **eJPT** — boshlang'ich daraja uchun yaxshi kirish nuqtasi
- **OSCP** — sanoatda eng nufuzli amaliy sertifikat
- **CEH** — keng tan olingan, ko'proq nazariy
- **GPEN/GWAPT** — SANS institutining yuqori darajadagi sertifikatlari

### Karyera yo'nalishlari

Penetration Tester → Senior Pentester → Red Team Operator → Security
Consultant/Architect
""",
    15: """## 3-Modul Amaliyoti: Penetration Testing Pro — Kurs yakuni

### Yakuniy loyiha

Hacker Lab'dagi barcha bilimlaringizni birlashtirib, to'liq professional pentest
hisoboti tuzing va "Jamoa" bo'limida ulashing.

### Tabriklaymiz!

Siz Cyber Security yo'nalishining barcha 4 kursini (Ethical Hacker, Tarmoq
Xavfsizligi Asoslari, Web Ilova Xavfsizligi, Penetration Testing Pro)
muvaffaqiyatli yakunladingiz!

### Qo'shimcha amaliyot uchun tavsiya etilgan platformalar

- **TryHackMe** (tryhackme.com) — bosqichma-bosqich yo'llar
- **OverTheWire** (overthewire.org/wargames) — terminal-asoslangan wargame'lar
- **HackTheBox** — yuqori darajadagi amaliy mashqlar

Sertifikat olish uchun Hacker Lab panelidan imtihonga yoziling!
""",
}

print(f"Penetration Testing Pro (course_id=12): {len(PENTEST_PRO)} ta dars")


# =================================================================
# BAZAGA YOZISH
# =================================================================
def main():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    all_courses = {
        9: ETHICAL_HACKER,
        10: NETWORK_SECURITY,
        11: WEB_APP_SECURITY,
        12: PENTEST_PRO,
    }

    total_updated = 0
    for course_id, lessons_content in all_courses.items():
        rows = c.execute(
            "SELECT id FROM lessons WHERE course_id=? ORDER BY order_num", (course_id,)
        ).fetchall()
        for idx, (lesson_id,) in enumerate(rows, start=1):
            if idx in lessons_content:
                c.execute(
                    "UPDATE lessons SET content_html=? WHERE id=?",
                    (lessons_content[idx], lesson_id)
                )
                total_updated += 1

    conn.commit()
    conn.close()
    print(f"\nJami yangilangan darslar: {total_updated}")


if __name__ == "__main__":
    main()
