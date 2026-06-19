"""
Mavjud DB ga yangi ustunlar va jadvallar qo'shadigan migration skript.
Bir marta ishga tushiriladi: python database/migrate.py
"""
import sqlite3, os, random

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyber_shats.db")

def col_exists(cursor, table, col):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(r[1] == col for r in cursor.fetchall())

conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute("PRAGMA foreign_keys = ON")

# users jadvaliga yangi ustunlar
for col, defn in [
    ("code_balance", "INTEGER NOT NULL DEFAULT 0"),
    ("oauth_provider", "TEXT DEFAULT ''"),
    ("last_login_ip", "TEXT DEFAULT ''"),
    ("failed_login_count", "INTEGER NOT NULL DEFAULT 0"),
    ("locked_until", "TEXT DEFAULT NULL"),
    ("custom_id", "TEXT UNIQUE DEFAULT NULL"),
]:
    if not col_exists(c, "users", col):
        try:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} {defn}")
            print(f"  + users.{col}")
        except Exception as e:
            print(f"  ! users.{col}: {e}")

# courses jadvaliga
for col, defn in [
    ("code_price", "INTEGER NOT NULL DEFAULT 0"),
    ("is_pro_only", "INTEGER NOT NULL DEFAULT 0"),
    ("is_paid", "INTEGER NOT NULL DEFAULT 0"),
]:
    if not col_exists(c, "courses", col):
        c.execute(f"ALTER TABLE courses ADD COLUMN {col} {defn}")
        print(f"  + courses.{col}")

# directions jadvaliga
for col, defn in [
    ("is_pro_only", "INTEGER NOT NULL DEFAULT 0"),
]:
    if not col_exists(c, "directions", col):
        c.execute(f"ALTER TABLE directions ADD COLUMN {col} {defn}")
        print(f"  + directions.{col}")

# Yangi jadvallarni yaratish
schema_sql = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")).read()
new_tables = [
    "code_transactions", "pro_payments", "oauth_links",
    "security_events", "blocked_ips", "user_ratings",
    "premium_ids", "id_auctions", "auction_bids",
    "smm_ai_messages", "course_access_codes",
]
for t in new_tables:
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (t,))
    if not c.fetchone():
        start = schema_sql.find(f"CREATE TABLE IF NOT EXISTS {t}")
        if start == -1:
            print(f"  ! {t} schema.sql da topilmadi")
            continue
        end = schema_sql.find(");", start) + 2
        ddl = schema_sql[start:end]
        c.execute(ddl)
        print(f"  + jadval: {t}")

# user_ratings
c.execute("""
    INSERT OR IGNORE INTO user_ratings (user_id, total_score, courses_done, tests_passed, rank_position)
    SELECT id, xp, 0, 0, 0 FROM users
""")

# Premium IDlar
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
    c.execute(
        "INSERT OR IGNORE INTO premium_ids (custom_id, id_type, base_price, status) VALUES (?,?,?,'available')",
        (cid, ctype, price)
    )
print("  + Premium IDlar qo'shildi")

# Mavjud foydalanuvchilarga custom_id berish
users_without_id = c.execute("SELECT id FROM users WHERE custom_id IS NULL").fetchall()
used_ids = set(r[0] for r in c.execute("SELECT custom_id FROM users WHERE custom_id IS NOT NULL").fetchall())
for (uid,) in users_without_id:
    for _ in range(200):
        new_cid = str(random.randint(1000000, 9999999))
        if any(new_cid.count(d) >= 4 for d in "0123456789"):
            continue
        if new_cid not in used_ids:
            used_ids.add(new_cid)
            c.execute("UPDATE users SET custom_id=? WHERE id=?", (new_cid, uid))
            break

# SMM/Logistika yo'nalishlarini is_pro_only=1 ga o'rnatish
c.execute("UPDATE directions SET is_pro_only=1 WHERE slug IN ('smm','targetolog','logistika')")
c.execute("UPDATE courses SET is_pro_only=1 WHERE direction_id IN (SELECT id FROM directions WHERE slug IN ('smm','targetolog','logistika'))")

conn.commit()
conn.close()
print("Migration muvaffaqiyatli yakunlandi!")
