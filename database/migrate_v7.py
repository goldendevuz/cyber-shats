"""
CYBER SHATS V1.3 — Migration V7 (Bosqich 3)
- announcements: admin broadcast e'lonlari (ovozli)
- announcement_views: kim ko'rgan/eshitganini kuzatish
- ping_test_usage: foydalanuvchilarning ping test ishlatishi (limit hisoblash)

Ishga tushirish: python database/migrate_v7.py
"""
import sqlite3, os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyber_shats.db")


def table_exists(c, table):
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return c.fetchone() is not None


conn = sqlite3.connect(DB)
c = conn.cursor()

if not table_exists(c, "announcements"):
    c.execute("""
        CREATE TABLE announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body TEXT NOT NULL DEFAULT '',
            priority TEXT NOT NULL DEFAULT 'normal',  -- normal, important, urgent
            target_plans TEXT NOT NULL DEFAULT 'all', -- all, free, pro, cyber_pro
            is_active INTEGER NOT NULL DEFAULT 1,
            voice_enabled INTEGER NOT NULL DEFAULT 1, -- ovozli yoqilganmi
            created_by INTEGER NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            expires_at TEXT DEFAULT NULL
        )
    """)
    c.execute("CREATE INDEX idx_announcements_active ON announcements(is_active, created_at)")
    print("  + jadval: announcements")

if not table_exists(c, "announcement_views"):
    c.execute("""
        CREATE TABLE announcement_views (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            announcement_id INTEGER NOT NULL REFERENCES announcements(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            viewed_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(announcement_id, user_id)
        )
    """)
    print("  + jadval: announcement_views")

if not table_exists(c, "ping_test_usage"):
    c.execute("""
        CREATE TABLE ping_test_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            target TEXT NOT NULL,                    -- masalan: google.com
            response_time_ms INTEGER NOT NULL,       -- ping javob vaqti
            success INTEGER NOT NULL DEFAULT 1,
            was_paid INTEGER NOT NULL DEFAULT 0,     -- pulli ping bo'lganmi (kvota tugaganidan keyin)
            cost_paid INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX idx_ping_usage_user ON ping_test_usage(user_id, created_at)")
    print("  + jadval: ping_test_usage")

conn.commit()
conn.close()
print("\nMigration V7 muvaffaqiyatli yakunlandi!")
