#!/usr/bin/env python3
# ============================================================
# CYBER SHATS — Bazani yaratish va namunaviy ma'lumotlar bilan to'ldirish
# Ishlatish: python3 database/seed.py
# ============================================================
import sqlite3
import os
import random
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "cyber_shats.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "database", "schema.sql")

random.seed(42)

# 12 IT yo'nalishi — spesifikatsiyadagi aniq kurs sonlari bilan
DIRECTIONS = [
    ("web-dev", "Web Dasturlash", "code", 124, "green"),
    ("python", "Python", "terminal", 98, "cyan"),
    ("cyber-security", "Cyber Xavfsizlik", "shield", 76, "red"),
    ("mobile-dev", "Mobil Dasturlash", "smartphone", 82, "green"),
    ("javascript", "JavaScript", "code", 110, "yellow"),
    ("cpp", "C++", "cpu", 65, "cyan"),
    ("networking", "Tarmoq Texnologiyalari", "wifi", 48, "green"),
    ("database", "Ma'lumotlar Bazasi", "database", 50, "cyan"),
    ("ai-ml", "AI & Machine Learning", "bot", 70, "green"),
    ("data-science", "Data Science", "trending-up", 68, "yellow"),
    ("cloud", "Cloud Computing", "cloud", 45, "cyan"),
    ("devops", "DevOps", "git-branch", 60, "green"),
    ("smm", "SMM Menejeri", "share-2", 30, "pink"),
    ("targetolog", "Targetolog", "target", 25, "orange"),
    ("logistika", "Logistika", "truck", 20, "blue"),
]

# Har bir yo'nalish uchun namunaviy kurs nomlari (haqiqiy qator sifatida bazaga yoziladi)
COURSE_TEMPLATES = {
    "web-dev": ["HTML & CSS Asoslari", "Responsive Veb-dizayn", "React.js Boshlang'ich", "Full-Stack Web Dasturchi"],
    "python": ["Python Asoslari", "Python OOP va Algoritmlar", "Django bilan Backend", "Python Avtomatlashtirish"],
    "cyber-security": ["Ethical Hacker", "Tarmoq Xavfsizligi Asoslari", "Web Ilova Xavfsizligi", "Penetration Testing Pro"],
    "mobile-dev": ["Flutter bilan Mobil Ilova", "Android (Kotlin) Asoslari", "iOS (Swift) Boshlang'ich", "React Native Amaliyot"],
    "javascript": ["JavaScript Asoslari", "ES6+ va Zamonaviy JS", "Node.js Backend", "TypeScript Chuqur Kurs"],
    "cpp": ["C++ Asoslari", "Ma'lumotlar Tuzilmalari (C++)", "Algoritmlar va Murakkablik", "C++ Tizim Dasturlash"],
    "networking": ["Tarmoq Asoslari (CCNA)", "Cisco Router & Switch", "TCP/IP Chuqur Tahlil", "Tarmoq Monitoring"],
    "database": ["SQL Asoslari", "MySQL Chuqur Kurs", "PostgreSQL Amaliyot", "NoSQL va MongoDB"],
    "ai-ml": ["Machine Learning Asoslari", "Neyron Tarmoqlar", "Computer Vision", "NLP va Til Modellari"],
    "data-science": ["Data Science Asoslari", "Pandas va NumPy", "Data Vizualizatsiya", "Statistik Tahlil"],
    "cloud": ["AWS Asoslari", "Cloud Architecture", "Docker va Konteynerlar", "Serverless Dasturlash"],
    "devops": ["DevOps Asoslari", "CI/CD Pipeline", "Kubernetes Amaliyot", "Linux Server Boshqaruvi"],
    "smm": ["SMM Asoslari", "Instagram va TikTok Marketing", "Kontent Strategiyasi", "SMM Analitika"],
    "targetolog": ["Facebook Ads Asoslari", "Instagram Reklama", "Google Ads", "Targetolog Pro"],
    "logistika": ["Logistika Asoslari", "Omborxona Boshqaruvi", "Import va Eksport", "Supply Chain Management"],
}

LEVELS = ["Boshlang'ich", "O'rta", "Yuqori"]
ICONS_BY_DIR = {
    "web-dev": "code", "python": "terminal", "cyber-security": "shield", "mobile-dev": "smartphone",
    "javascript": "code", "cpp": "cpu", "networking": "wifi", "database": "database",
    "ai-ml": "bot", "data-science": "trending-up", "cloud": "cloud", "devops": "git-branch",
    "smm": "share-2", "targetolog": "target", "logistika": "truck",
}

# "Ethical Hacker" kursi uchun rasmiy 8 modulli o'quv dasturi (skrinshotga mos)
ETHICAL_HACKER_MODULES = [
    ("Network Basics", "wifi", 4),
    ("Linux Fundamentals", "terminal", 5),
    ("Web Security", "shield", 6),
    ("Penetration Testing", "bug", 6),
    ("Wireless Hacking", "wifi", 3),
    ("Malware Analysis", "code", 4),
    ("Social Engineering", "users", 3),
    ("Final Project", "flag", 2),
]

NEWS_ITEMS = [
    ("Yangi avlod fishing hujumlari AI yordamida kuchaydi", "Xavfsizlik tadqiqotchilari sun'iy intellekt yordamida yaratilgan fishing xatlarining sezilarli darajada oshganini aniqladilar.", "cyber-security"),
    ("Python 3.13 chiqdi: nima o'zgardi?", "Yangi versiya tezlik va xotira boshqarishda muhim yaxshilanishlarni taqdim etadi.", "python"),
    ("OWASP Top 10 ro'yxati yangilandi", "Web ilovalardagi eng xavfli zaifliklar ro'yxati yana bir bor qayta ko'rib chiqildi.", "cyber-security"),
    ("React 19 — yangi imkoniyatlar sharhi", "Komponentlarni qurish uslubi yana ham soddalashtirildi.", "web-dev"),
    ("Kubernetes 1.31 — yangi xususiyatlar", "Konteyner orkestratsiyasi tizimida yangi xavfsizlik sozlamalari qo'shildi.", "devops"),
    ("ChatGPT va Claude — AI yordamchilar taqqoslandi", "Ishlab chiquvchilar uchun qaysi AI assistenti samaraliroq?", "ai-ml"),
    ("Ransomware hujumlari 2026-yilda 40% ga oshdi", "Korxonalar ma'lumotlarini himoya qilish bo'yicha yangi tavsiyalar e'lon qilindi.", "cyber-security"),
    ("AWS yangi mintaqa ochdi: Markaziy Osiyo", "Bu mintaqadagi kompaniyalar uchun tezroq cloud xizmatlari imkonini beradi.", "cloud"),
    ("TypeScript 5.6 chiqarildi", "Tip tekshirish tezligi sezilarli darajada oshirildi.", "javascript"),
    ("Linux yadrosi 6.10 — xavfsizlik yamoqlari", "Bir qancha muhim zaifliklar tuzatildi.", "networking"),
    ("Data Science mutaxassislariga bo'lgan talab oshmoqda", "2026-yilda eng ko'p talab qilinadigan IT kasblari ro'yxati.", "data-science"),
    ("GitHub Copilot endi butun loyihani tahlil qiladi", "Yangi funksiya kod bazasini chuqurroq tushunishga yordam beradi.", "web-dev"),
]

BOOKS = [
    ("Web Xavfsizligi Asoslari", "PDF", "3.2 MB", "cyber-security"),
    ("Python uchun To'liq Qo'llanma", "PDF", "5.1 MB", "python"),
    ("Tarmoq Protokollari Cheat Sheet", "PDF", "0.8 MB", "networking"),
    ("Linux Buyruqlari To'plami", "PDF", "1.4 MB", "devops"),
    ("Machine Learning Roadmap 2026", "PDF", "2.0 MB", "ai-ml"),
    ("SQL Injection — Chuqur Tahlil", "PDF", "2.7 MB", "cyber-security"),
    ("JavaScript ES6+ Qo'llanma", "PDF", "3.6 MB", "javascript"),
    ("Docker & Kubernetes Roadmap", "PDF", "1.9 MB", "devops"),
    ("Data Structures Cheat Sheet", "PDF", "1.1 MB", "cpp"),
    ("AWS Sertifikatiga Tayyorgarlik", "PDF", "4.4 MB", "cloud"),
    ("Mobil Ilova Arxitekturasi", "PDF", "2.3 MB", "mobile-dev"),
    ("Penetration Testing Yo'l Xaritasi", "PDF", "2.9 MB", "cyber-security"),
]

BADGES = [
    ("Birinchi Qadam", "flag", "Birinchi darsni yakunladi"),
    ("Kod Ustasi", "code", "10 ta amaliy topshiriqni bajardi"),
    ("Xavfsizlik Bilimdoni", "shield", "Cyber Security yo'nalishini 50% tugatdi"),
    ("Test Chempioni", "award", "3 ta testdan 90%+ natija oldi"),
    ("Forum Faoli", "message", "Forumda 10 ta mavzuga javob yozdi"),
    ("Sertifikat Egasi", "award", "Birinchi sertifikatni qo'lga oldi"),
    ("Marafonchi", "trending-up", "7 kun ketma-ket platformaga kirdi"),
    ("AI Hamkor", "bot", "AI Yordamchi bilan 20 ta suhbat qildi"),
]

FORUM_POSTS = [
    ("SQL Injection haqida savol", "Salom! SQLMap bilan ishlashda xato chiqyapti, kim yordam bera oladi?", "cyber-security"),
    ("Python'da decorator qanday ishlaydi?", "Decoratorlar mantig'ini tushunmadim, misol bilan tushuntirib bera olasizmi?", "python"),
    ("React useEffect cleanup haqida", "useEffect ichida cleanup funksiyasi qachon kerak bo'ladi?", "web-dev"),
    ("CCNA sertifikatiga qanday tayyorlanish kerak?", "Tarmoq yo'nalishida ishlayman, CCNA uchun qaysi resurslarni tavsiya qilasiz?", "networking"),
    ("Docker konteyner va VM farqi", "Konteyner bilan virtual mashina o'rtasidagi asosiy farqlarni tushunmadim.", "devops"),
    ("Machine Learning'ni noldan o'rganish mumkinmi?", "Matematikadan zaif bilimim bor, shunga qaramay ML o'rganishni boshlasam bo'ladimi?", "ai-ml"),
    ("Burp Suite proxy sozlamalari", "Burp Suite'ni brauzer bilan ulashda muammo bo'lyapti, sabab nimada?", "cyber-security"),
    ("Frilanserlik uchun qaysi yo'nalish foydaliroq?", "Web dev yoki mobil dev — qaysi biri tezroq pul keltiradi?", "umumiy"),
]

def main():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(open(SCHEMA_PATH, "r", encoding="utf-8").read())
    cur = conn.cursor()

    # ---------- FOYDALANUVCHILAR ----------
    users = [
        ("Admin", "Shats", "admin@cybershats.uz", "admin123", "admin", 9999, 20, "enterprise"),
        ("Mentor", "Aliyev", "mentor@cybershats.uz", "mentor123", "mentor", 4200, 12, "pro"),
        ("Jasur", "Karimov", "jasur@example.com", "demo1234", "student", 1850, 6, "pro"),
        ("Dilnoza", "Yusupova", "dilnoza@example.com", "demo1234", "student", 920, 4, "free"),
        ("Sardor", "Tosheva", "sardor@example.com", "demo1234", "student", 3100, 9, "pro"),
        ("Madina", "Rashidova", "madina@example.com", "demo1234", "student", 410, 2, "free"),
        ("Bekzod", "Nazarov", "bekzod@example.com", "demo1234", "student", 60, 1, "free"),
    ]
    user_ids = {}
    for ism, familiya, email, pw, role, xp, level, plan in users:
        cur.execute(
            "INSERT INTO users (ism, familiya, email, password_hash, role, xp, level, plan) VALUES (?,?,?,?,?,?,?,?)",
            (ism, familiya, email, generate_password_hash(pw), role, xp, level, plan),
        )
        user_ids[email] = cur.lastrowid

    # ---------- YO'NALISHLAR ----------
    direction_ids = {}
    PRO_ONLY_DIRS = {"smm", "targetolog", "logistika"}
    for i, (slug, name, icon, count, color) in enumerate(DIRECTIONS):
        is_pro = 1 if slug in PRO_ONLY_DIRS else 0
        cur.execute(
            "INSERT INTO directions (slug, name_uz, icon, course_count, color, sort_order, is_pro_only) VALUES (?,?,?,?,?,?,?)",
            (slug, name, icon, count, color, i, is_pro),
        )
        direction_ids[slug] = cur.lastrowid

    # ---------- KURSLAR + MODULLAR + DARSLAR ----------
    course_ids = {}
    all_course_rows = []
    PRO_ONLY_SLUGS = {"smm", "targetolog", "logistika"}
    for slug, titles in COURSE_TEMPLATES.items():
        dir_id = direction_ids[slug]
        icon = ICONS_BY_DIR[slug]
        is_pro_only = 1 if slug in PRO_ONLY_SLUGS else 0
        for j, title in enumerate(titles):
            course_slug = f"{slug}-{j+1}"
            level = LEVELS[min(j, 2)]
            duration = random.randint(4, 14)
            lessons_count = random.randint(8, 24)
            students = random.randint(120, 5400)
            rating = round(random.uniform(4.3, 5.0), 1)
            price = 0 if j == 0 else random.choice([0, 49000, 99000, 149000])
            # SMM/Logistika kurslari pullik va pro_only
            code_price = 10000 if is_pro_only or (price > 0) else 0
            is_paid = 1 if (is_pro_only or price > 0) and j > 0 else 0
            cur.execute(
                """INSERT INTO courses (slug, direction_id, title, subtitle, description, level,
                   duration_weeks, lessons_count, students_count, rating, price, icon, is_pro_only, code_price, is_paid)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (course_slug, dir_id, title, f"{title} bo'yicha to'liq amaliy kurs",
                 f"{title} kursida siz nazariy bilim va amaliy ko'nikmalarni birga egallaysiz. "
                 f"Kurs davomida real loyihalar ustida ishlaysiz va sertifikat olasiz.",
                 level, duration, lessons_count, students, rating, price, icon,
                 is_pro_only, code_price, is_paid),
            )
            cid = cur.lastrowid
            course_ids[course_slug] = cid
            all_course_rows.append((cid, course_slug, title, slug))

    # Ethical Hacker kursiga (cyber-security-1) rasmiy 8 modulli dastur
    eh_id = course_ids["cyber-security-1"]
    cur.execute("UPDATE courses SET lessons_count=33, students_count=4820, rating=4.9, duration_weeks=10 WHERE id=?", (eh_id,))
    order_n = 0
    for m_title, m_icon, m_lessons in ETHICAL_HACKER_MODULES:
        cur.execute(
            "INSERT INTO modules (course_id, order_num, title, icon, lessons_count) VALUES (?,?,?,?,?)",
            (eh_id, order_n, m_title, m_icon, m_lessons),
        )
        mid = cur.lastrowid
        for li in range(m_lessons):
            order_n += 1
            cur.execute(
                """INSERT INTO lessons (course_id, module_id, order_num, title, duration_seconds, content_html, has_practice)
                   VALUES (?,?,?,?,?,?,?)""",
                (eh_id, mid, order_n, f"{m_title} — {li+1}-dars", random.randint(360, 1500),
                 f"<p>Bu darsda <strong>{m_title}</strong> mavzusi bo'yicha asosiy tushunchalar va amaliy "
                 f"misollar ko'rib chiqiladi. Video darsni tomosha qiling va quyidagi materiallarni yuklab oling.</p>",
                 1 if li == m_lessons - 1 else 0),
            )

    # Qolgan barcha kurslar uchun umumiy modul/dars generatsiyasi
    for cid, cslug, title, dslug in all_course_rows:
        if cslug == "cyber-security-1":
            continue
        cur.execute("SELECT lessons_count FROM courses WHERE id=?", (cid,))
        lessons_count = cur.fetchone()[0]
        n_modules = max(3, lessons_count // 5)
        per_module = max(1, lessons_count // n_modules)
        order_n = 0
        for mi in range(n_modules):
            cur.execute(
                "INSERT INTO modules (course_id, order_num, title, icon, lessons_count) VALUES (?,?,?,?,?)",
                (cid, mi, f"{mi+1}-Modul: {title.split()[0]} Asoslari" if mi == 0 else f"{mi+1}-Modul", ICONS_BY_DIR[dslug], per_module),
            )
            mid = cur.lastrowid
            for li in range(per_module):
                order_n += 1
                cur.execute(
                    """INSERT INTO lessons (course_id, module_id, order_num, title, duration_seconds, content_html, has_practice)
                       VALUES (?,?,?,?,?,?,?)""",
                    (cid, mid, order_n, f"{order_n}-dars: {title} amaliyoti" if li == per_module - 1 else f"{order_n}-dars",
                     random.randint(300, 1200),
                     f"<p><strong>{title}</strong> kursining {order_n}-darsi. Video tomosha qilib, mavzuni o'zlashtiring.</p>",
                     1 if li == per_module - 1 else 0),
                )

    # ---------- TESTLAR ----------
    sample_questions = [
        ("HTTP statusi 404 nimani bildiradi?", "Sahifa topilmadi", "Server xatosi", "Ruxsat yo'q", "Muvaffaqiyatli", "a"),
        ("SQL Injection qaysi turdagi hujum?", "Tarmoq hujumi", "Web ilova hujumi", "Fizik hujum", "DDoS", "b"),
        ("Python'da ro'yxat (list) o'zgaruvchan (mutable)mi?", "Ha", "Yo'q", "Faqat Python 2'da", "Faqat tuple uchun", "a"),
        ("Linux'da fayl ruxsatlarini o'zgartirish buyrug'i?", "chmod", "chown", "chgrp", "ls -l", "a"),
        ("OSI modelida nechta qatlam bor?", "5", "6", "7", "8", "c"),
        ("Git'da o'zgarishlarni saqlash buyrug'i?", "git push", "git commit", "git pull", "git clone", "b"),
        ("Qaysi port odatda HTTPS uchun ishlatiladi?", "80", "21", "443", "22", "c"),
        ("Docker konteyneri nima?", "Virtual mashina", "Yengil izolyatsiyalangan muhit", "Fayl tizimi", "Server", "b"),
    ]
    for cid, cslug, title, dslug in all_course_rows[:20]:
        cur.execute("INSERT INTO tests (course_id, title, duration_minutes) VALUES (?,?,?)",
                    (cid, f"{title} — Yakuniy Test", 20))
        tid = cur.lastrowid
        qs = random.sample(sample_questions, 5)
        for oi, (q, a, b, c, d, correct) in enumerate(qs):
            cur.execute(
                """INSERT INTO test_questions (test_id, order_num, question_text, option_a, option_b, option_c, option_d, correct_option)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (tid, oi, q, a, b, c, d, correct),
            )

    # ---------- YOZILISHLAR (enrollments) + TEST URINISHLARI ----------
    student_emails = ["jasur@example.com", "dilnoza@example.com", "sardor@example.com", "madina@example.com", "bekzod@example.com"]
    enrolled_courses = random.sample(all_course_rows, 18)
    for email in student_emails:
        uid = user_ids[email]
        picks = random.sample(enrolled_courses, random.randint(2, 5))
        for cid, cslug, title, dslug in picks:
            progress = random.choice([15, 30, 45, 60, 75, 90, 100])
            cur.execute(
                "INSERT OR IGNORE INTO enrollments (user_id, course_id, progress_percent, started_at) VALUES (?,?,?,?)",
                (uid, cid, progress, (datetime.now() - timedelta(days=random.randint(1, 60))).isoformat()),
            )
            if progress == 100:
                cert_code = f"CS-{uid:04d}-{cid:04d}-{random.randint(1000,9999)}"
                cur.execute(
                    "INSERT INTO certificates (user_id, course_id, cert_code) VALUES (?,?,?)",
                    (uid, cid, cert_code),
                )

    cur.execute("SELECT id FROM tests LIMIT 10")
    test_ids = [r[0] for r in cur.fetchall()]
    for email in student_emails:
        uid = user_ids[email]
        for tid in random.sample(test_ids, min(3, len(test_ids))):
            total = 5
            score = random.randint(2, 5)
            cur.execute("INSERT INTO test_attempts (user_id, test_id, score, total) VALUES (?,?,?,?)", (uid, tid, score, total))

    # ---------- FORUM ----------
    post_ids = []
    for title, body, cat in FORUM_POSTS:
        uid = user_ids[random.choice(student_emails)]
        cur.execute(
            "INSERT INTO forum_posts (user_id, title, body, category, views, created_at) VALUES (?,?,?,?,?,?)",
            (uid, title, body, cat, random.randint(12, 480), (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat()),
        )
        post_ids.append(cur.lastrowid)
    sample_replies = [
        "Menimcha, avval rasmiy hujjatlarni o'qib chiqing, ko'p savollar shu yerda javob topadi.",
        "Bu muammoga men ham duch kelgandim, quyidagi yechim yordam berdi.",
        "Juda foydali savol, men ham shu narsani bilmoqchi edim.",
        "YouTube'da shu mavzu bo'yicha yaxshi darslar bor, qidirib ko'ring.",
        "Kodingizni to'liq yuborsangiz, aniqroq yordam bera olardim.",
    ]
    for pid in post_ids:
        for _ in range(random.randint(1, 4)):
            uid = user_ids[random.choice(student_emails + ["mentor@cybershats.uz"])]
            cur.execute(
                "INSERT INTO forum_replies (post_id, user_id, body, created_at) VALUES (?,?,?,?)",
                (pid, uid, random.choice(sample_replies), datetime.now().isoformat()),
            )

    cur.execute("""UPDATE forum_posts SET replies_count = (
        SELECT COUNT(*) FROM forum_replies WHERE forum_replies.post_id = forum_posts.id)""")

    # ---------- YANGILIKLAR ----------
    for title, summary, cat in NEWS_ITEMS:
        cur.execute(
            "INSERT INTO news (title, summary, category, published_at) VALUES (?,?,?,?)",
            (title, summary, cat, (datetime.now() - timedelta(days=random.randint(0, 14))).isoformat()),
        )

    # ---------- KITOBLAR ----------
    for title, ftype, size, cat in BOOKS:
        cur.execute("INSERT INTO books (title, type, size_label, category) VALUES (?,?,?,?)", (title, ftype, size, cat))

    # ---------- BADGELAR ----------
    badge_ids = []
    for name, icon, desc in BADGES:
        cur.execute("INSERT INTO badges (name, icon, description) VALUES (?,?,?)", (name, icon, desc))
        badge_ids.append(cur.lastrowid)
    for email in student_emails:
        uid = user_ids[email]
        for bid in random.sample(badge_ids, random.randint(1, 5)):
            cur.execute("INSERT OR IGNORE INTO user_badges (user_id, badge_id) VALUES (?,?)", (uid, bid))

    # ---------- BILDIRISHNOMALAR ----------
    notif_templates = [
        ("Yangi dars qo'shildi", "Sizning kursingizga yangi dars qo'shildi.", "info"),
        ("Test natijasi", "Testdan o'tdingiz! Natijangizni profilingizdan ko'ring.", "success"),
        ("Sertifikat tayyor", "Kursni yakunladingiz, sertifikatingiz tayyor.", "success"),
        ("Forumda javob", "Sizning postingizga yangi javob yozildi.", "info"),
    ]
    for email in student_emails:
        uid = user_ids[email]
        for title, body, ntype in random.sample(notif_templates, random.randint(1, 4)):
            cur.execute(
                "INSERT INTO notifications (user_id, title, body, type, is_read) VALUES (?,?,?,?,?)",
                (uid, title, body, ntype, random.choice([0, 1])),
            )

    conn.commit()
    conn.close()
    print(f"✅ Baza muvaffaqiyatli yaratildi: {DB_PATH}")
    print(f"   Foydalanuvchilar: {len(users)} | Yo'nalishlar: {len(DIRECTIONS)} | Kurslar: {len(all_course_rows)}")
    print("   Admin: admin@cybershats.uz / admin123")
    print("   Demo student: jasur@example.com / demo1234")

    conn2 = sqlite3.connect(DB_PATH)
    conn2.row_factory = sqlite3.Row
    cur2 = conn2.cursor()

    # ---------- PREMIUM IDlar ----------
    PREMIUM_ID_DATA = [
        ("1111111", "quad7", 100000),
        ("2222222", "quad7", 100000),
        ("3333333", "quad7", 100000),
        ("4444444", "quad7", 100000),
        ("5555555", "quad7", 100000),
        ("6666666", "quad7", 100000),
        ("7777777", "quad7", 100000),
        ("8888888", "quad7", 100000),
        ("9999999", "quad7", 100000),
        ("1234567", "sequential", 120000),
    ]
    for cid, ctype, price in PREMIUM_ID_DATA:
        cur2.execute(
            "INSERT OR IGNORE INTO premium_ids (custom_id, id_type, base_price, status) VALUES (?,?,?,'available')",
            (cid, ctype, price)
        )

    # ---------- Foydalanuvchilarga auto custom_id ----------
    all_users_rows = cur2.execute("SELECT id FROM users WHERE custom_id IS NULL").fetchall()
    used_ids = set()
    for row in all_users_rows:
        uid = row[0]
        for _ in range(200):
            new_cid = str(random.randint(1000000, 9999999))
            if any(new_cid.count(d) >= 4 for d in "0123456789"):
                continue
            if new_cid in used_ids:
                continue
            existing = cur2.execute("SELECT id FROM users WHERE custom_id=?", (new_cid,)).fetchone()
            if not existing:
                used_ids.add(new_cid)
                cur2.execute("UPDATE users SET custom_id=? WHERE id=?", (new_cid, uid))
                break

    conn2.commit()
    conn2.close()
    print("   Premium IDlar va foydalanuvchi IDlari yaratildi.")

if __name__ == "__main__":
    main()
