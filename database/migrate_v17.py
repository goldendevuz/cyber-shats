"""
CYBER SHATS V1.3 — Migration V17 (Startaplar bo'limi)

Foydalanuvchilar loyihalarini (startaplarini) joylaydi: nomi, tavsifi, rasm.
Bosh sahifada "Foydalanuvchilar loyihalari" deb har kuni aylanib turadigan
ko'rinishda ko'rsatiladi (kunlik tasodifiy tartibda, real vaqt asosida —
fon jarayoni shart emas, sana asosida deterministik tasodifiy tartiblash).
"""
import sqlite3, os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyber_shats.db")


def table_exists(c, table):
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return c.fetchone() is not None


conn = sqlite3.connect(DB)
c = conn.cursor()

if not table_exists(c, "startups"):
    c.execute("""
        CREATE TABLE startups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            image_path TEXT DEFAULT NULL,
            link_url TEXT DEFAULT '',          -- loyihaga tashqi havola (ixtiyoriy)
            category TEXT NOT NULL DEFAULT 'boshqa',
            status TEXT NOT NULL DEFAULT 'pending',  -- pending, approved, rejected
            view_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            reviewed_by INTEGER DEFAULT NULL REFERENCES users(id),
            reviewed_at TEXT DEFAULT NULL
        )
    """)
    c.execute("CREATE INDEX idx_startups_status ON startups(status, created_at)")
    c.execute("CREATE INDEX idx_startups_user ON startups(user_id)")
    print("  + jadval: startups")

if not table_exists(c, "startup_likes"):
    c.execute("""
        CREATE TABLE startup_likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            startup_id INTEGER NOT NULL REFERENCES startups(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(startup_id, user_id)
        )
    """)
    print("  + jadval: startup_likes")

conn.commit()
conn.close()
print("\nMigration V17 muvaffaqiyatli yakunlandi!")
