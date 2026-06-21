"""
CYBER SHATS V1.3 — Yo'nalishlar uchun Hacker Lab matn materiallari.
Har bir yo'nalish tanlanganda foydalanuvchiga ko'rsatiladigan to'liq ma'lumot.
Video YO'Q — faqat yozma matn (va kelajakda audio, hozircha bo'sh).

Ishga tushirish: python database/seed_direction_content.py
"""
import sqlite3, os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyber_shats.db")

CONTENT = {
    "cyber-security": """# Cyber Xavfsizlik — Amaliyot Yo'nalishi

## Bu yo'nalishda nimani o'rganasiz

Cyber xavfsizlik — tizimlar, tarmoqlar va ma'lumotlarni ruxsatsiz kirish, hujum va
buzilishlardan himoya qilish san'ati va fani. Bu yo'nalishda siz **penetration testing**
(kirish testlari), **zaifliklarni aniqlash**, **tarmoq xavfsizligi** va **raqamli
sud ekspertizasi** (digital forensics) asoslarini o'rganasiz.

## Operatsion tizimlar haqida

### Kali Linux
Kali Linux — Offensive Security tomonidan yaratilgan, Debian asosidagi, penetration
testing uchun maxsus moslashtirilgan distributiv. 600 dan ortiq oldindan o'rnatilgan
xavfsizlik vositasi bilan keladi.

**Qaysi versiya yaxshi?**
- **Kali Linux (rolling release)** — doimiy yangilanadigan asosiy versiya, eng yangi
  vositalar bilan. Tajribali foydalanuvchilar uchun tavsiya etiladi.
- **Kali Purple** — ko'k jamoa (defensive security) uchun maxsus versiya, SOC va
  monitoring vositalari bilan boyitilgan.
- **Kali NetHunter** — Android qurilmalar uchun mobil versiya.
- **Kali Linux Light** — kam resursli kompyuterlar uchun yengil versiya (XFCE).

Yangi boshlovchilar uchun: **standart Kali Linux (XFCE desktop)** versiyasi eng
muvozanatli tanlov — yetarli vosita, oddiy interfeys.

**Rasmiy manba:** kali.org/get-kali — yuklab olish uchun ISO tasvirlari, VM
image'lari (VirtualBox/VMware uchun tayyor), va ARM versiyalari (Raspberry Pi).

### Boshqa xavfsizlik operatsion tizimlari

**Parrot Security OS** — Kali'ga muqobil, Debian asosida, yengilroq va
maxfiylikka yo'naltirilgan (Tor, anonymity vositalari bilan).

**BlackArch Linux** — Arch Linux asosida, 2800+ vosita bilan eng katta
to'plamlardan biri, lekin tajribali foydalanuvchilar uchun.

**Tails OS** — to'liq anonim, izsiz ishlash uchun (RAM'da ishlaydi, diskka
yozmaydi), jurnalistlar va maxfiylik tadqiqotchilari uchun.

**Qubes OS** — xavfsizlikka yo'naltirilgan, virtual mashinalar orqali
izolyatsiya qiluvchi operatsion tizim.

## Kali Linux'dagi asosiy vositalar (kategoriya bo'yicha)

**Ma'lumot yig'ish (Reconnaissance):** nmap, theHarvester, recon-ng, maltego

**Zaiflik tahlili:** OpenVAS, Nikto, lynis

**Veb-ilova hujumlari:** Burp Suite, OWASP ZAP, sqlmap, wpscan

**Parol hujumlari:** John the Ripper, Hashcat, Hydra, Medusa

**Simsiz tarmoq hujumlari:** Aircrack-ng, Wifite, Kismet

**Ekspluatatsiya vositalari:** Metasploit Framework, BeEF, SET (Social Engineer Toolkit)

**Sniffing va spoofing:** Wireshark, Ettercap, Bettercap

**Forensics:** Autopsy, Volatility, Binwalk

## Muhim eslatma

Bu yerdagi barcha ma'lumotlar **faqat ta'lim maqsadida**. O'z tizimingiz yoki
ruxsat berilgan (masalan CTF, HackTheBox, TryHackMe) muhitlardan tashqari hech
qachon boshqa birovning tizimiga ruxsatsiz kirishga harakat qilmang — bu jinoiy
javobgarlikka olib keladi.
""",

    "web-dev": """# Web Dasturlash — Amaliyot Yo'nalishi

## Bu yo'nalishda nimani o'rganasiz

Zamonaviy veb-ilovalar yaratish: frontend (HTML, CSS, JavaScript, React),
backend (Node.js, Python/Flask, Django), va ma'lumotlar bazasi bilan ishlash.

## Asosiy texnologiyalar

**Frontend:** HTML5, CSS3 (Flexbox, Grid), JavaScript (ES6+), React, Vue.js

**Backend:** Node.js + Express, Python + Flask/Django, PHP + Laravel

**Ma'lumotlar bazasi:** PostgreSQL, MySQL, MongoDB

**DevOps asoslari:** Git, Docker, CI/CD

## Amaliy loyihalar yo'nalishi

Ushbu panelda siz real loyihalar ustida ishlay olasiz: portfolio sayt,
e-commerce platforma, ijtimoiy tarmoq klonlari, REST API yaratish va h.k.
Terminal orqali kod yozish, xato topish va debug qilishni mashq qilasiz.
""",

    "python": """# Python — Amaliyot Yo'nalishi

## Bu yo'nalishda nimani o'rganasiz

Python — soddaligi va kuchli imkoniyatlari bilan eng mashhur dasturlash
tillaridan biri. Web development, data science, automation, AI/ML va
boshqa ko'p sohalarda qo'llaniladi.

## Asosiy mavzular

- Sintaksis asoslari, ma'lumot turlari, funksiyalar
- Obyektga yo'naltirilgan dasturlash (OOP)
- Fayllar bilan ishlash, exception handling
- Kutubxonalar: NumPy, Pandas, Requests, Flask/Django
- Avtomatlashtirish skriptlari yozish

## Amaliy panel imkoniyatlari

Terminal orqali Python kodini yozib, natijani darhol ko'rishingiz mumkin.
Real loyihalar: web scraper, Telegram bot, ma'lumotlar tahlili skriptlari.
""",

    "mobile-dev": """# Mobil Dasturlash — Amaliyot Yo'nalishi

## Bu yo'nalishda nimani o'rganasiz

iOS va Android uchun mobil ilovalar yaratish: native (Swift/Kotlin) va
cross-platform (Flutter, React Native) yondashuvlari.

## Asosiy texnologiyalar

**Cross-platform:** Flutter (Dart), React Native (JavaScript)

**Native Android:** Kotlin, Java

**Native iOS:** Swift, SwiftUI

## Amaliy panel imkoniyatlari

UI/UX dizayn asoslari, API integratsiyasi, ma'lumotlar bazasi bilan ishlash,
va Google Play / App Store'ga chiqarish jarayonlari bo'yicha amaliy mashqlar.
""",

    "javascript": """# JavaScript — Amaliyot Yo'nalishi

## Bu yo'nalishda nimani o'rganasiz

JavaScript — veb-saytlarni interaktiv qiluvchi asosiy dasturlash tili.
Frontend va backend (Node.js) ikkalasida ham qo'llaniladi.

## Asosiy mavzular

- ES6+ sintaksis: arrow functions, destructuring, async/await
- DOM manipulatsiyasi va Event handling
- Fetch API va AJAX so'rovlar
- Frameworklar: React, Vue, Node.js + Express

## Amaliy panel imkoniyatlari

Terminal orqali JS kodini yozib sinab ko'rish, real loyihalar: interaktiv
veb-ilovalar, single-page application (SPA), REST API client.
""",

    "cpp": """# C++ — Amaliyot Yo'nalishi

## Bu yo'nalishda nimani o'rganasiz

C++ — yuqori unumdorlik talab qiluvchi tizimlar, o'yinlar, va dasturiy
ta'minot yaratishda qo'llaniladigan kuchli dasturlash tili.

## Asosiy mavzular

- Sintaksis, ko'rsatkichlar (pointers), xotira boshqaruvi
- Obyektga yo'naltirilgan dasturlash (OOP)
- STL (Standard Template Library)
- Algoritmlar va ma'lumotlar tuzilmalari

## Amaliy panel imkoniyatlari

Terminal orqali C++ kodini kompilyatsiya qilib sinash, algoritm masalalarini
yechish, va real loyihalar ustida ishlash (masalan, oddiy o'yin dvigateli).
""",

    "networking": """# Tarmoq Texnologiyalari — Amaliyot Yo'nalishi

## Bu yo'nalishda nimani o'rganasiz

Kompyuter tarmoqlari asoslari: TCP/IP, routing, switching, va tarmoq
xavfsizligi.

## Asosiy mavzular

- OSI va TCP/IP modellari
- IP manzillash, subnetting, VLAN
- Router va switch konfiguratsiyasi (Cisco IOS)
- Firewall va VPN asoslari

## Amaliy panel imkoniyatlari

Tarmoq diagnostikasi buyruqlari (ping, traceroute, netstat) simulyatori,
tarmoq topologiyasi loyihalash mashqlari.
""",

    "database": """# Ma'lumotlar Bazasi — Amaliyot Yo'nalishi

## Bu yo'nalishda nimani o'rganasiz

Relyatsion va NoSQL ma'lumotlar bazalarini loyihalash, so'rovlar yozish va
optimallashtirish.

## Asosiy mavzular

- SQL asoslari: SELECT, JOIN, GROUP BY, subquery
- Ma'lumotlar bazasi loyihalash, normalizatsiya
- PostgreSQL, MySQL administratsiya
- NoSQL: MongoDB, Redis

## Amaliy panel imkoniyatlari

Terminal orqali SQL so'rovlarini yozib sinash, real ma'lumotlar bazasi
loyihalash mashqlari.
""",

    "ai-ml": """# AI & Machine Learning — Amaliyot Yo'nalishi

## Bu yo'nalishda nimani o'rganasiz

Sun'iy intellekt va mashinaviy o'qitish asoslari: ma'lumotlarni tahlil
qilish, modellar qurish va trening qilish.

## Asosiy mavzular

- Python uchun NumPy, Pandas, Matplotlib
- Scikit-learn bilan klassik ML algoritmlar
- Neyron tarmoqlar asoslari (TensorFlow/PyTorch)
- Natural Language Processing (NLP) asoslari

## Amaliy panel imkoniyatlari

Terminal orqali ML kodini yozib sinash, real datasetlar ustida mashq qilish.
""",

    "data-science": """# Data Science — Amaliyot Yo'nalishi

## Bu yo'nalishda nimani o'rganasiz

Ma'lumotlarni yig'ish, tozalash, tahlil qilish va vizualizatsiya qilish
orqali biznes qarorlarga yordam berish.

## Asosiy mavzular

- Pandas, NumPy bilan ma'lumotlar tahlili
- Statistik tahlil asoslari
- Vizualizatsiya: Matplotlib, Seaborn, Plotly
- A/B testing va biznes metrikalar

## Amaliy panel imkoniyatlari

Real datasetlar bilan ishlash, hisobot va dashboard yaratish mashqlari.
""",

    "cloud": """# Cloud Computing — Amaliyot Yo'nalishi

## Bu yo'nalishda nimani o'rganasiz

Bulutli hisoblash platformalari: AWS, Google Cloud, Azure — infratuzilmani
boshqarish va masshtablash.

## Asosiy mavzular

- AWS asosiy xizmatlari: EC2, S3, RDS, Lambda
- Konteynerizatsiya: Docker, Kubernetes
- Infrastructure as Code: Terraform
- CI/CD pipeline qurish

## Amaliy panel imkoniyatlari

Cloud CLI buyruqlari simulyatori, deployment jarayonlari bo'yicha mashqlar.
""",

    "devops": """# DevOps — Amaliyot Yo'nalishi

## Bu yo'nalishda nimani o'rganasiz

Dasturiy ta'minotni ishlab chiqish va operatsiya jarayonlarini birlashtirish:
avtomatlashtirish, monitoring, va tez yetkazib berish.

## Asosiy mavzular

- Git va versiya nazorati strategiyalari
- Docker va konteynerizatsiya
- CI/CD: Jenkins, GitHub Actions, GitLab CI
- Monitoring: Prometheus, Grafana

## Amaliy panel imkoniyatlari

Terminal orqali Docker va Git buyruqlari simulyatori, pipeline qurish
mashqlari.
""",
}


def main():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    updated = 0
    for slug, content in CONTENT.items():
        c.execute("UPDATE directions SET text_content=? WHERE slug=?", (content, slug))
        if c.rowcount:
            updated += 1
            print(f"  + {slug}: material qo'shildi ({len(content)} belgi)")
    conn.commit()
    conn.close()
    print(f"\nJami {updated} ta yo'nalishga material qo'shildi.")


if __name__ == "__main__":
    main()
