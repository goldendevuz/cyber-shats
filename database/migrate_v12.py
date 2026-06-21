"""
CYBER SHATS V1.3 — Migration V12 (Yangi: Hacker Lab / Amaliyot Paneli)

- hacker_lab_consent: foydalanuvchi rozilik bergan-bermaganligi (birinchi kirish)
- hacker_lab_access: Pro foydalanuvchi 100,000 CODE to'lab kirish huquqi sotib olgan-olmaganligi
- hacker_lab_security_events: "xavfli" buyruq urinishlari — admin ko'rib chiqishi uchun
- users.hacker_lab_blocked: alohida blok holati (faqat Hacker Lab uchun, butun hisobni blokламайди)
- users.selected_direction_id: foydalanuvchi tanlagan asosiy yo'nalish (panel shunga moslashadi)
- directions jadvaliga material ustunlari: text_content, audio_url
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
c = conn.cursor()

# 1. Foydalanuvchining tanlagan asosiy yo'nalishi
if not col_exists(c, "users", "selected_direction_id"):
    c.execute("ALTER TABLE users ADD COLUMN selected_direction_id INTEGER DEFAULT NULL REFERENCES directions(id)")
    print("  + users.selected_direction_id")

# 2. Hacker Lab uchun alohida blok (butun hisobni emas, faqat shu panelni blokлайди)
if not col_exists(c, "users", "hacker_lab_blocked"):
    c.execute("ALTER TABLE users ADD COLUMN hacker_lab_blocked INTEGER NOT NULL DEFAULT 0")
    print("  + users.hacker_lab_blocked")

# 3. Yo'nalishlarga matn/audio material ustunlari
if not col_exists(c, "directions", "text_content"):
    c.execute("ALTER TABLE directions ADD COLUMN text_content TEXT DEFAULT ''")
    print("  + directions.text_content")
if not col_exists(c, "directions", "audio_url"):
    c.execute("ALTER TABLE directions ADD COLUMN audio_url TEXT DEFAULT ''")
    print("  + directions.audio_url")

# 4. Rozilik jadvali
if not table_exists(c, "hacker_lab_consent"):
    c.execute("""
        CREATE TABLE hacker_lab_consent (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
            agreed_at TEXT NOT NULL DEFAULT (datetime('now')),
            ip TEXT DEFAULT ''
        )
    """)
    print("  + jadval: hacker_lab_consent")

# 5. Kirish huquqi (Pro to'lov yoki Cyber Pro/VIP bepul)
if not table_exists(c, "hacker_lab_access"):
    c.execute("""
        CREATE TABLE hacker_lab_access (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
            granted_via TEXT NOT NULL,        -- 'paid' (Pro 100K to'lagan) yoki 'plan' (Cyber Pro/VIP bepul)
            paid_amount INTEGER NOT NULL DEFAULT 0,
            granted_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    print("  + jadval: hacker_lab_access")

# 6. Xavfsizlik buzilishlari — "xavfli" terminal buyruqlari
if not table_exists(c, "hacker_lab_security_events"):
    c.execute("""
        CREATE TABLE hacker_lab_security_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            custom_id TEXT NOT NULL DEFAULT '',     -- snapshot, tezkor ko'rish uchun
            command TEXT NOT NULL,                   -- foydalanuvchi kiritgan xavfli buyruq
            direction_id INTEGER DEFAULT NULL REFERENCES directions(id),
            status TEXT NOT NULL DEFAULT 'pending',   -- pending, reviewed, blocked, dismissed
            reviewed_by INTEGER DEFAULT NULL REFERENCES users(id),
            reviewed_at TEXT DEFAULT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX idx_hl_sec_status ON hacker_lab_security_events(status, created_at)")
    c.execute("CREATE INDEX idx_hl_sec_user ON hacker_lab_security_events(user_id)")
    print("  + jadval: hacker_lab_security_events")

# 7. Narxlar
c.execute("INSERT OR IGNORE INTO pricing_settings (key, value) VALUES ('hacker_lab_pro_price', '100000')")
c.execute("INSERT OR IGNORE INTO pricing_settings (key, value) VALUES ('hacker_lab_violation_fine', '10000000')")
print("  + narxlar: hacker_lab_pro_price=100000, hacker_lab_violation_fine=10000000")

# 8. Yo'nalish ichidagi jamoa fikr almashish (soddalashtirilgan — to'liq ijtimoiy
#    tarmoq keyingi bosqichda quriladi, hozircha forum-uslubidagi oddiy bo'lim)
if not table_exists(c, "hacker_lab_posts"):
    c.execute("""
        CREATE TABLE hacker_lab_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            direction_id INTEGER NOT NULL REFERENCES directions(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            title TEXT NOT NULL,
            body TEXT NOT NULL DEFAULT '',
            file_path TEXT DEFAULT NULL,        -- yuklangan fayl (rasm/hujjat) yo'li
            file_type TEXT DEFAULT NULL,        -- 'image', 'document', va h.k.
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX idx_hl_posts_direction ON hacker_lab_posts(direction_id, created_at)")
    print("  + jadval: hacker_lab_posts")

if not table_exists(c, "hacker_lab_post_replies"):
    c.execute("""
        CREATE TABLE hacker_lab_post_replies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL REFERENCES hacker_lab_posts(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            body TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    print("  + jadval: hacker_lab_post_replies")

conn.commit()
conn.close()
print("\nMigration V12 muvaffaqiyatli yakunlandi!")
