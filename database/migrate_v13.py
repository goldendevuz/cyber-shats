"""
CYBER SHATS V1.3 — Migration V13 (Bosqich 2)
Saytdan to'g'ridan-to'g'ri CODE sotib olish — bot orqali emas,
foydalanuvchi o'z panelidan ID kiritib, miqdor tanlab/yozib,
chek rasmini yuklab to'lov qiladi. G'azna tasdiqlaydi (botga o'xshab).

bot_purchase_requests jadvaliga:
- source: 'bot' yoki 'site' — qaysi kanaldan kelganini bilish uchun
- receipt_file_path: saytga yuklangan chek fayli yo'li (Telegram file_id'dan farqli)
- chat_id ENDI ixtiyoriy (sayt orqali bo'lsa NULL)
"""
import sqlite3, os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyber_shats.db")


def col_exists(c, table, col):
    c.execute(f"PRAGMA table_info({table})")
    return any(r[1] == col for r in c.fetchall())


conn = sqlite3.connect(DB)
c = conn.cursor()

if not col_exists(c, "bot_purchase_requests", "source"):
    c.execute("ALTER TABLE bot_purchase_requests ADD COLUMN source TEXT NOT NULL DEFAULT 'bot'")
    print("  + bot_purchase_requests.source")

if not col_exists(c, "bot_purchase_requests", "receipt_file_path"):
    c.execute("ALTER TABLE bot_purchase_requests ADD COLUMN receipt_file_path TEXT DEFAULT NULL")
    print("  + bot_purchase_requests.receipt_file_path")

# chat_id NOT NULL cheklovini olib tashlash kerak (sayt so'rovlarida chat_id yo'q).
# SQLite'da ustunni o'zgartirish uchun jadvalni qayta yaratish kerak.
c.execute("PRAGMA table_info(bot_purchase_requests)")
cols = c.fetchall()
chat_id_notnull = any(col[1] == "chat_id" and col[3] == 1 for col in cols)

if chat_id_notnull:
    print("  ~ chat_id NOT NULL cheklovini olib tashlash uchun jadval qayta quriladi...")
    c.execute("""
        CREATE TABLE bot_purchase_requests_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER DEFAULT NULL,
            tg_user_id INTEGER DEFAULT NULL,
            request_type TEXT NOT NULL,
            code_amount INTEGER DEFAULT 0,
            price_uzs INTEGER DEFAULT 0,
            courses_json TEXT DEFAULT '',
            target_custom_id TEXT NOT NULL,
            site_user_id INTEGER DEFAULT NULL REFERENCES users(id),
            receipt_file_id TEXT DEFAULT NULL,
            receipt_file_path TEXT DEFAULT NULL,
            source TEXT NOT NULL DEFAULT 'bot',
            status TEXT NOT NULL DEFAULT 'pending',
            admin_note TEXT DEFAULT '',
            reviewed_by INTEGER DEFAULT NULL REFERENCES treasury_accounts(id),
            reviewed_at TEXT DEFAULT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    c.execute("""
        INSERT INTO bot_purchase_requests_new
        (id, chat_id, tg_user_id, request_type, code_amount, price_uzs, courses_json,
         target_custom_id, site_user_id, receipt_file_id, receipt_file_path, source,
         status, admin_note, reviewed_by, reviewed_at, created_at)
        SELECT id, chat_id, tg_user_id, request_type, code_amount, price_uzs, courses_json,
               target_custom_id, site_user_id, receipt_file_id,
               COALESCE(receipt_file_path, NULL), COALESCE(source, 'bot'),
               status, admin_note, reviewed_by, reviewed_at, created_at
        FROM bot_purchase_requests
    """)
    c.execute("DROP TABLE bot_purchase_requests")
    c.execute("ALTER TABLE bot_purchase_requests_new RENAME TO bot_purchase_requests")
    c.execute("CREATE INDEX idx_purchase_status ON bot_purchase_requests(status, created_at)")
    c.execute("CREATE INDEX idx_purchase_chat ON bot_purchase_requests(chat_id)")
    print("  + jadval qayta qurildi, chat_id endi ixtiyoriy")

conn.commit()
conn.close()
print("\nMigration V13 muvaffaqiyatli yakunlandi!")
