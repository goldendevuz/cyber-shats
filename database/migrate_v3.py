"""
CYBER SHATS — Migration V3
Code tangalarini foydalanuvchidan-foydalanuvchiga o'tkazish (P2P) va
foydalanuvchilar orasidagi shaxsiy xabarlashuv (Telegram uslubidagi chat).
Ishga tushirish: python database/migrate_v3.py
"""
import sqlite3, os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyber_shats.db")


def table_exists(cursor, table):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cursor.fetchone() is not None


conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute("PRAGMA foreign_keys = ON")

# --- coin_transfers ---
if not table_exists(c, "coin_transfers"):
    c.execute("""
        CREATE TABLE coin_transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user_id INTEGER NOT NULL REFERENCES users(id),
            to_user_id INTEGER NOT NULL REFERENCES users(id),
            amount_sent INTEGER NOT NULL,
            fee_amount INTEGER NOT NULL DEFAULT 0,
            amount_received INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX idx_coin_transfers_from ON coin_transfers(from_user_id)")
    c.execute("CREATE INDEX idx_coin_transfers_to ON coin_transfers(to_user_id)")
    print("  + jadval: coin_transfers")

# --- private_messages ---
if not table_exists(c, "private_messages"):
    c.execute("""
        CREATE TABLE private_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL REFERENCES users(id),
            receiver_id INTEGER NOT NULL REFERENCES users(id),
            body TEXT NOT NULL DEFAULT '',
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX idx_pm_sender ON private_messages(sender_id)")
    c.execute("CREATE INDEX idx_pm_receiver ON private_messages(receiver_id)")
    c.execute("CREATE INDEX idx_pm_pair ON private_messages(sender_id, receiver_id, created_at)")
    print("  + jadval: private_messages")

# --- pricing_settings: P2P o'tkazma komissiyasi (foiz, free foydalanuvchi uchun) ---
c.execute("INSERT OR IGNORE INTO pricing_settings (key, value) VALUES (?,?)",
          ("coin_transfer_fee_percent", "5"))
print("  + sozlama: coin_transfer_fee_percent (default 5%)")

conn.commit()
conn.close()
print("Migration V3 muvaffaqiyatli yakunlandi!")
