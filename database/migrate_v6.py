"""
CYBER SHATS V1.3 — Migration V6 (Bosqich 2)
Cyber Pro versiyasi + Sertifikat tizimi
- directions.is_cyber_pro_only ustuni qo'shiladi
- Cyber Pro yo'nalishlari: Ingliz tili, Matematika, Office
- certificate_applications jadvali (sertifikat arizalari)
- Cyber Pro yo'nalishlariga 12 ta yangi kurs

Ishga tushirish: python database/migrate_v6.py
"""
import sqlite3, os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyber_shats.db")


def col_exists(c, table, col):
    c.execute(f"PRAGMA table_info({table})")
    return any(r[1] == col for r in c.fetchall())


def table_exists(c, table):
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return c.fetchone() is not None


conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# 1. directions.is_cyber_pro_only ustuni
if not col_exists(c, "directions", "is_cyber_pro_only"):
    c.execute("ALTER TABLE directions ADD COLUMN is_cyber_pro_only INTEGER NOT NULL DEFAULT 0")
    print("  + directions.is_cyber_pro_only")

# 2. Cyber Pro yo'nalishlari
cyber_pro_directions = [
    ("ingliz-tili",   "Ingliz tili",         "globe",     "Ingliz tilini noldan ravon darajagacha", 4, "blue",  100),
    ("matematika",    "Matematika",          "hash",      "Algebra, geometriya, oliy matematika",   4, "blue",  101),
    ("office",        "Microsoft Office",    "file-text", "Word, Excel, PowerPoint mukammal",       3, "blue",  102),
]
for slug, name, icon, desc, cc, color, sort_order in cyber_pro_directions:
    existing = c.execute("SELECT id FROM directions WHERE slug=?", (slug,)).fetchone()
    if not existing:
        c.execute(
            "INSERT INTO directions (slug, name_uz, icon, description, course_count, color, sort_order, is_pro_only, is_cyber_pro_only) VALUES (?,?,?,?,?,?,?,0,1)",
            (slug, name, icon, desc, cc, color, sort_order)
        )
        print(f"  + yo'nalish: {name}")

# 3. Cyber Pro yo'nalishlari uchun kurslar
cyber_pro_courses = [
    # Ingliz tili
    ("ingliz-boshlangich",     "ingliz-tili", "Ingliz tili — Boshlang'ich (A1)",  "Alifbo, oddiy gaplar, asosiy so'zlar",       "Boshlang'ich", 6,  20, "globe"),
    ("ingliz-orta",            "ingliz-tili", "Ingliz tili — O'rta (A2-B1)",      "Grammar, dialog, kundalik suhbatlar",        "O'rta",        8,  25, "globe"),
    ("ingliz-yuqori",          "ingliz-tili", "Ingliz tili — Yuqori (B2-C1)",     "IELTS, TOEFL, akademik ingliz tili",          "Yuqori",       12, 30, "globe"),
    ("ingliz-biznes",          "ingliz-tili", "Biznes inglizcha",                  "Business english, presentation, emails",     "O'rta",        8,  22, "briefcase"),
    # Matematika
    ("matematika-algebra",     "matematika",  "Algebra asoslari",                  "Tenglamalar, funksiyalar, ko'phadlar",       "Boshlang'ich", 8,  20, "hash"),
    ("matematika-geometriya",  "matematika",  "Geometriya",                        "Planimetriya va stereometriya",              "O'rta",        8,  20, "hash"),
    ("matematika-trigonometriya","matematika","Trigonometriya",                    "Sinus, kosinus, identitetlar, formulalar",   "O'rta",        6,  18, "hash"),
    ("matematika-oliy",        "matematika",  "Oliy matematika",                   "Differensial va integral hisob",             "Yuqori",       12, 28, "hash"),
    # Office
    ("office-word",            "office",      "Microsoft Word",                    "Hujjat formatlash, jadvallar, shablonlar",   "O'rta",        4,  15, "file-text"),
    ("office-excel",           "office",      "Microsoft Excel",                   "Formulalar, jadvallar, grafik, makrolar",    "O'rta",        6,  20, "grid"),
    ("office-powerpoint",      "office",      "Microsoft PowerPoint",              "Taqdimot, dizayn, animatsiya",               "Boshlang'ich", 4,  15, "layers"),
]

for slug, dir_slug, title, subtitle, level, weeks, lessons, icon in cyber_pro_courses:
    existing = c.execute("SELECT id FROM courses WHERE slug=?", (slug,)).fetchone()
    if existing:
        continue
    dir_row = c.execute("SELECT id FROM directions WHERE slug=?", (dir_slug,)).fetchone()
    if not dir_row:
        continue
    c.execute(
        """INSERT INTO courses (slug, direction_id, title, subtitle, level,
                                 duration_weeks, lessons_count, code_price, icon, is_active)
           VALUES (?,?,?,?,?,?,?,?,?,1)""",
        (slug, dir_row["id"], title, subtitle, level, weeks, lessons, 0, icon)
    )
    print(f"  + kurs: {title}")

# 4. Sertifikat arizalari jadvali
if not table_exists(c, "certificate_applications"):
    c.execute("""
        CREATE TABLE certificate_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            direction_id INTEGER NOT NULL REFERENCES directions(id),
            custom_id TEXT NOT NULL,            -- foydalanuvchi ID raqami (snapshot)
            exam_score INTEGER NOT NULL,        -- imtihondan olingan ball (avtomatik)
            exam_total INTEGER NOT NULL,        -- jami ball
            paid_amount INTEGER NOT NULL,       -- to'lagan summa (snapshot)
            status TEXT NOT NULL DEFAULT 'pending',  -- pending / approved / rejected / issued
            admin_note TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            reviewed_at TEXT DEFAULT NULL,
            reviewed_by INTEGER DEFAULT NULL REFERENCES users(id),
            certificate_number TEXT DEFAULT NULL    -- ariza qabul qilingach beriladi
        )
    """)
    c.execute("CREATE INDEX idx_cert_app_user ON certificate_applications(user_id)")
    c.execute("CREATE INDEX idx_cert_app_status ON certificate_applications(status)")
    print("  + jadval: certificate_applications")

# 5. Direction-darajasi imtihon urinishlari (yo'nalish sertifikati uchun)
if not table_exists(c, "direction_exam_attempts"):
    c.execute("""
        CREATE TABLE direction_exam_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            direction_id INTEGER NOT NULL REFERENCES directions(id),
            test_score INTEGER NOT NULL,
            test_total INTEGER NOT NULL,
            practice_score INTEGER NOT NULL,
            practice_total INTEGER NOT NULL,
            total_score INTEGER NOT NULL,       -- test + practice umumiy ball
            max_total INTEGER NOT NULL,
            passed INTEGER NOT NULL,             -- 60% dan baland = passed
            paid_amount INTEGER NOT NULL,
            started_at TEXT NOT NULL DEFAULT (datetime('now')),
            finished_at TEXT DEFAULT NULL
        )
    """)
    c.execute("CREATE INDEX idx_dir_exam_user ON direction_exam_attempts(user_id)")
    print("  + jadval: direction_exam_attempts")

conn.commit()
conn.close()
print("\nMigration V6 muvaffaqiyatli yakunlandi!")
