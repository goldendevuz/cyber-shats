"""
CYBER SHATS V1.3 — Migration V11 (Bosqich 1)
SHATS CYBER VIP versiyasi + obuna muddati tizimi + VIP maxsus IDlar.

1. users.plan_expires_at — Pro/Cyber Pro/VIP qachon tugashi (1 oy)
2. vip_ids jadvali — 0-9 raqamlari (10 ta), faqat admin tomonidan beriladi
3. pricing_settings ga vip_price_code qo'shiladi
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

# 1. Obuna tugash sanasi
if not col_exists(c, "users", "plan_expires_at"):
    c.execute("ALTER TABLE users ADD COLUMN plan_expires_at TEXT DEFAULT NULL")
    print("  + users.plan_expires_at")

# 2. VIP maxsus IDlar (0-9, 10 ta, faqat admin beradi)
if not table_exists(c, "vip_ids"):
    c.execute("""
        CREATE TABLE vip_ids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            digit TEXT NOT NULL UNIQUE,         -- '0'..'9'
            status TEXT NOT NULL DEFAULT 'available',  -- available, assigned
            owner_user_id INTEGER DEFAULT NULL REFERENCES users(id),
            assigned_by INTEGER DEFAULT NULL REFERENCES users(id),
            assigned_at TEXT DEFAULT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    for d in "1234567890":
        c.execute("INSERT INTO vip_ids (digit, status) VALUES (?, 'available')", (d,))
    print("  + jadval: vip_ids (10 ta: 0-9)")

# 3. Narxlar
c.execute("INSERT OR IGNORE INTO pricing_settings (key, value) VALUES ('vip_price_code', '570000')")
c.execute("INSERT OR IGNORE INTO pricing_settings (key, value) VALUES ('vip_welcome_bonus', '30000')")
c.execute("INSERT OR IGNORE INTO pricing_settings (key, value) VALUES ('vip_course_bonus', '2000')")
c.execute("INSERT OR IGNORE INTO pricing_settings (key, value) VALUES ('vip_enabled', '1')")
c.execute("INSERT OR IGNORE INTO pricing_settings (key, value) VALUES ('plan_duration_days', '30')")
print("  + narxlar: vip_price_code=570000, vip_welcome_bonus=30000, vip_course_bonus=2000")
print("  + sozlama: vip_enabled=1 (admin yoqib/o'chira oladi)")
print("  + sozlama: plan_duration_days=30 (Pro/Cyber Pro/VIP muddati)")

conn.commit()
conn.close()
print("\nMigration V11 muvaffaqiyatli yakunlandi!")
