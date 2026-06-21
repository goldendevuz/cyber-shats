"""
CYBER SHATS — Migration V5
G'azna (Code Panel) endi foydalanuvchilar tizimidan butunlay mustaqil:
- treasury_accounts: G'azna xodimlari uchun alohida login (email+parol), users jadvalida emas
- treasury_fund: jamg'arma balansi (0 dan boshlanadi, faqat real tranzaksiyalardan to'ladi)
- treasury_fund_log: jamg'arma kirim-chiqim tarixi

Eslatma: avvalgi V4 migratsiyada qo'shilgan users.treasury_password_hash ustuni
endi ishlatilmaydi (SQLite'da ustun o'chirish murakkab bo'lgani uchun shunchaki
e'tiborsiz qoldiriladi, ma'lumotlarga zarar bermaydi).

Ishga tushirish: python database/migrate_v5.py
"""
import sqlite3, os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyber_shats.db")


def table_exists(cursor, table):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cursor.fetchone() is not None


conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute("PRAGMA foreign_keys = ON")

if not table_exists(c, "treasury_accounts"):
    c.execute("""
        CREATE TABLE treasury_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ism TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            last_login_at TEXT DEFAULT NULL
        )
    """)
    print("  + jadval: treasury_accounts")

if not table_exists(c, "treasury_fund"):
    c.execute("""
        CREATE TABLE treasury_fund (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            balance INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    c.execute("INSERT OR IGNORE INTO treasury_fund (id, balance) VALUES (1, 0)")
    print("  + jadval: treasury_fund (balance=0)")

if not table_exists(c, "treasury_fund_log"):
    c.execute("""
        CREATE TABLE treasury_fund_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            direction TEXT NOT NULL,
            amount INTEGER NOT NULL,
            reason TEXT NOT NULL DEFAULT '',
            user_id INTEGER DEFAULT NULL REFERENCES users(id),
            treasury_account_id INTEGER DEFAULT NULL REFERENCES treasury_accounts(id),
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX idx_treasury_log_user ON treasury_fund_log(user_id)")
    c.execute("CREATE INDEX idx_treasury_log_created ON treasury_fund_log(created_at)")
    print("  + jadval: treasury_fund_log")

conn.commit()
conn.close()
print("Migration V5 muvaffaqiyatli yakunlandi!")
print("Eslatma: G'azna xodimi hisobini /treasury/register orqali (yoki seed skripti bilan) yarating.")
