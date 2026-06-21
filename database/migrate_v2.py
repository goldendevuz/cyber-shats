"""
CYBER SHATS — Migration V2
Admin narxlar boshqaruvi, super-admin tizimi, premium ID admin boshqaruvi.
Ishga tushirish: python database/migrate_v2.py
"""
import sqlite3, os, random

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyber_shats.db")


def col_exists(cursor, table, col):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(r[1] == col for r in cursor.fetchall())


def table_exists(cursor, table):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cursor.fetchone() is not None


conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute("PRAGMA foreign_keys = ON")

# --- users.admin_id ---
if not col_exists(c, "users", "admin_id"):
    c.execute("ALTER TABLE users ADD COLUMN admin_id TEXT DEFAULT NULL")
    print("  + users.admin_id")

c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_admin_id ON users(admin_id) WHERE admin_id IS NOT NULL")


# --- pricing_settings ---
if not table_exists(c, "pricing_settings"):
    c.execute("""
        CREATE TABLE pricing_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_by INTEGER DEFAULT NULL REFERENCES users(id)
        )
    """)
    print("  + jadval: pricing_settings")

# --- admin_action_audit ---
if not table_exists(c, "admin_action_audit"):
    c.execute("""
        CREATE TABLE admin_action_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_id INTEGER NOT NULL REFERENCES users(id),
            target_id INTEGER DEFAULT NULL REFERENCES users(id),
            action TEXT NOT NULL,
            details TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    print("  + jadval: admin_action_audit")

# --- Default narxlar (faqat mavjud bo'lmasa) ---
DEFAULTS = {
    "pro_price_uzs": "99000",
    "pro_price_code": "57000",
    "pro_ai_limit": "100",
    "pro_duration_days": "30",
    "free_ai_limit": "10",
    "free_test_limit": "30",
    "free_smm_access": "0",
    "course_reward_code": "100",
    "ai_cost_per_msg": "200",
    "paid_course_code_default": "10000",
}
for k, v in DEFAULTS.items():
    c.execute("INSERT OR IGNORE INTO pricing_settings (key, value) VALUES (?,?)", (k, v))
print("  + narxlar sozlamalari (default qiymatlar)")

# --- Mavjud admin/mentor foydalanuvchilarga 4 xonali admin_id berish ---
admins = c.execute("SELECT id, role FROM users WHERE role IN ('admin','mentor','super_admin') AND admin_id IS NULL").fetchall()
used_admin_ids = set(r[0] for r in c.execute("SELECT admin_id FROM users WHERE admin_id IS NOT NULL").fetchall())


def gen_admin_id():
    for _ in range(500):
        cid = str(random.randint(1000, 9999))
        if cid not in used_admin_ids:
            used_admin_ids.add(cid)
            return cid
    raise RuntimeError("admin_id generatsiya qilinmadi")


for (uid, role) in admins:
    new_aid = gen_admin_id()
    c.execute("UPDATE users SET admin_id=? WHERE id=?", (new_aid, uid))
    print(f"  + user#{uid} ({role}) -> admin_id {new_aid}")

# --- Birinchi adminni super_admin qilib belgilash (agar super_admin umuman bo'lmasa) ---
has_super = c.execute("SELECT id FROM users WHERE role='super_admin' LIMIT 1").fetchone()
if not has_super:
    first_admin = c.execute("SELECT id FROM users WHERE role='admin' ORDER BY id ASC LIMIT 1").fetchone()
    if first_admin:
        c.execute("UPDATE users SET role='super_admin' WHERE id=?", (first_admin[0],))
        print(f"  + user#{first_admin[0]} -> role super_admin (birinchi admin avtomatik super admin qilindi)")

conn.commit()
conn.close()
print("Migration V2 muvaffaqiyatli yakunlandi!")
