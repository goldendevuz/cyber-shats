"""
CYBER SHATS V1.3 — Migration V16 (Telegram majburiy tasdiqlash)

Ro'yxatdan o'tishda foydalanuvchi Telegram orqali tasdiqlanishi majburiy:
1. Foydalanuvchi ro'yxatdan o'tadi -> users.telegram_verified=0
2. Sayt 6 xonali tasdiqlash kodi yaratadi (telegram_verifications jadvali)
3. Foydalanuvchi botga /start bosadi, keyin /verify <kod> yuboradi
   (yoki shunchaki /start bosgach, agar kutilayotgan kod bo'lsa, avtomatik bog'lanadi)
4. Bot kodni tekshiradi, agar to'g'ri bo'lsa users.telegram_verified=1 qiladi
5. Tasdiqlanmagan foydalanuvchi saytning asosiy qismlariga kira olmaydi
   (faqat tasdiqlash sahifasi ochiq turadi)
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

if not col_exists(c, "users", "telegram_verified"):
    c.execute("ALTER TABLE users ADD COLUMN telegram_verified INTEGER NOT NULL DEFAULT 0")
    print("  + users.telegram_verified")

if not col_exists(c, "users", "telegram_username"):
    c.execute("ALTER TABLE users ADD COLUMN telegram_username TEXT DEFAULT NULL")
    print("  + users.telegram_username")

if not col_exists(c, "users", "telegram_chat_id"):
    c.execute("ALTER TABLE users ADD COLUMN telegram_chat_id INTEGER DEFAULT NULL")
    print("  + users.telegram_chat_id")

if not table_exists(c, "telegram_verifications"):
    c.execute("""
        CREATE TABLE telegram_verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            code TEXT NOT NULL,
            telegram_username TEXT NOT NULL,
            is_used INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            expires_at TEXT NOT NULL,
            verified_at TEXT DEFAULT NULL
        )
    """)
    c.execute("CREATE INDEX idx_tgv_user ON telegram_verifications(user_id)")
    c.execute("CREATE INDEX idx_tgv_code ON telegram_verifications(code)")
    print("  + jadval: telegram_verifications")

# Mavjud foydalanuvchilar (sizning admin hisobingiz kabi) avtomatik tasdiqlangan
# deb belgilanadi — ular ro'yxatdan o'tish oqimidan o'tmagan, shuning uchun bloklanmasin
c.execute("UPDATE users SET telegram_verified=1 WHERE telegram_verified=0")
print("  ~ Mavjud foydalanuvchilar avtomatik tasdiqlangan deb belgilandi (orqaga moslik uchun)")

conn.commit()
conn.close()
print("\nMigration V16 muvaffaqiyatli yakunlandi!")
