"""
CYBER SHATS V1.3 — Migration V8 (Bosqich 2 — Telegram bot)
- telegram_users: bot foydalanuvchilari (chat_id, tanlangan til, holat)
- bot_purchase_requests: code/kurs sotib olish so'rovlari (chek skrin + tasdiqlash)
- bot_courses_purchased: bot orqali sotib olingan kurslar ro'yxati
"""
import sqlite3, os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyber_shats.db")


def table_exists(c, table):
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return c.fetchone() is not None


conn = sqlite3.connect(DB)
c = conn.cursor()

if not table_exists(c, "telegram_users"):
    c.execute("""
        CREATE TABLE telegram_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL UNIQUE,
            first_name TEXT DEFAULT '',
            last_name TEXT DEFAULT '',
            username TEXT DEFAULT '',
            language TEXT NOT NULL DEFAULT 'uz',     -- uz, ru, en, tr, kk, ky, tj
            state TEXT NOT NULL DEFAULT 'main',      -- holat (FSM): main, awaiting_id, awaiting_receipt, ...
            state_data TEXT DEFAULT '',              -- JSON ko'rinishidagi vaqtinchalik ma'lumotlar
            linked_user_id INTEGER DEFAULT NULL REFERENCES users(id),  -- saytdagi foydalanuvchi (ID orqali bog'lansa)
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            last_seen_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX idx_tg_chat ON telegram_users(chat_id)")
    print("  + jadval: telegram_users")

if not table_exists(c, "bot_purchase_requests"):
    c.execute("""
        CREATE TABLE bot_purchase_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            tg_user_id INTEGER REFERENCES telegram_users(id),
            request_type TEXT NOT NULL,        -- 'code' yoki 'course'
            -- code uchun:
            code_amount INTEGER DEFAULT 0,
            price_uzs INTEGER DEFAULT 0,
            -- course uchun: courses_json kursalarning JSON ro'yxati
            courses_json TEXT DEFAULT '',
            -- umumiy:
            target_custom_id TEXT NOT NULL,    -- saytdagi foydalanuvchi ID (#)
            site_user_id INTEGER DEFAULT NULL REFERENCES users(id),
            receipt_file_id TEXT DEFAULT NULL, -- Telegram file_id chek skrini
            status TEXT NOT NULL DEFAULT 'pending',  -- pending, approved, rejected, completed
            admin_note TEXT DEFAULT '',
            reviewed_by INTEGER DEFAULT NULL REFERENCES treasury_accounts(id),
            reviewed_at TEXT DEFAULT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX idx_purchase_status ON bot_purchase_requests(status, created_at)")
    c.execute("CREATE INDEX idx_purchase_chat ON bot_purchase_requests(chat_id)")
    print("  + jadval: bot_purchase_requests")

conn.commit()
conn.close()
print("Migration V8 muvaffaqiyatli yakunlandi!")
