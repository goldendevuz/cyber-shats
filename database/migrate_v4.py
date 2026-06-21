"""
CYBER SHATS — Migration V4
Code Panel (G'azna) uchun har bir admin/mentor/super_admin'ga tegishli,
alohida himoyalovchi parol (treasury_password_hash).
Ishga tushirish: python database/migrate_v4.py
"""
import sqlite3, os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyber_shats.db")


def col_exists(cursor, table, col):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(r[1] == col for r in cursor.fetchall())


conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute("PRAGMA foreign_keys = ON")

if not col_exists(c, "users", "treasury_password_hash"):
    c.execute("ALTER TABLE users ADD COLUMN treasury_password_hash TEXT DEFAULT NULL")
    print("  + users.treasury_password_hash")

conn.commit()
conn.close()
print("Migration V4 muvaffaqiyatli yakunlandi!")
