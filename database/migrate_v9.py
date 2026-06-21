"""
CYBER SHATS V1.3 — Migration V9 (Bosqich 3)
Web Push Notifications — foydalanuvchi saytdan chiqib ketsa ham
qurilmasiga bildirishnoma kelishi uchun.

push_subscriptions: har bir brauzer/qurilma obunasi (endpoint + kalitlar)
"""
import sqlite3, os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyber_shats.db")


def table_exists(c, table):
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return c.fetchone() is not None


conn = sqlite3.connect(DB)
c = conn.cursor()

if not table_exists(c, "push_subscriptions"):
    c.execute("""
        CREATE TABLE push_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            endpoint TEXT NOT NULL UNIQUE,
            p256dh TEXT NOT NULL,
            auth TEXT NOT NULL,
            user_agent TEXT DEFAULT '',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            last_used_at TEXT DEFAULT NULL
        )
    """)
    c.execute("CREATE INDEX idx_push_user ON push_subscriptions(user_id)")
    print("  + jadval: push_subscriptions")

conn.commit()
conn.close()
print("Migration V9 muvaffaqiyatli yakunlandi!")
