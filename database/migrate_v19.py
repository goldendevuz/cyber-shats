"""
CYBER SHATS V1.3 — Migration V19 (Trading bo'limi)

CODE tangasi real vaqtda "narx" o'zgarib turadi (0.1 soniyada, WebSocket yoki
server-sent events orqali), foydalanuvchilar "ko'tariladi" yoki "tushadi" deb
tiklov qo'yadi. To'g'ri taxmin = foyda (%), Noto'g'ri = zarar (%).
G'azna jamg'armasiga yo'qotilgan CODE tushadi, g'azna g'oliblarga to'liq
foyda chiqaradi (platformakomissiyasi: 2%).
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

# CODE tangasining narx tarixi (WebSocket/SSE uchun bufer)
if not table_exists(c, "trading_prices"):
    c.execute("""
        CREATE TABLE trading_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            price REAL NOT NULL,                  -- joriy narx (CODE/so'm)
            change_pct REAL NOT NULL DEFAULT 0,   -- oldingi narxdan % farq
            direction INTEGER NOT NULL DEFAULT 0, -- 1=ko'tarilgan, -1=tushgan, 0=barqaror
            created_at TEXT NOT NULL DEFAULT (datetime('now','subsec'))
        )
    """)
    c.execute("CREATE INDEX idx_tp_created ON trading_prices(created_at DESC)")
    # Boshlang'ich narx 1.0 (1 CODE = 1 so'm bazaviy)
    c.execute("INSERT INTO trading_prices (price, change_pct, direction) VALUES (1.0, 0, 0)")
    print("  + jadval: trading_prices (boshlang'ich narx: 1.0)")

# Foydalanuvchi treding pozitsiyalari (ochiq/yopiq tiklovlar)
if not table_exists(c, "trading_positions"):
    c.execute("""
        CREATE TABLE trading_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            direction TEXT NOT NULL,              -- 'up' yoki 'down'
            amount INTEGER NOT NULL,              -- tiklov miqdori (CODE)
            entry_price REAL NOT NULL,            -- kirish narxi
            exit_price REAL,                      -- chiqish narxi (yopilganda)
            duration_seconds INTEGER NOT NULL DEFAULT 30,  -- necha soniya ochiq
            status TEXT NOT NULL DEFAULT 'open',  -- open, won, lost, cancelled
            profit_loss INTEGER,                  -- foydali: +N, zararli: -N (CODE)
            profit_pct REAL,                      -- % foyda/zarar
            opened_at TEXT NOT NULL DEFAULT (datetime('now')),
            closed_at TEXT
        )
    """)
    c.execute("CREATE INDEX idx_pos_user ON trading_positions(user_id, status)")
    c.execute("CREATE INDEX idx_pos_open ON trading_positions(status, opened_at)")
    print("  + jadval: trading_positions")

# Trading statistikasi (umumiy)
if not table_exists(c, "trading_stats"):
    c.execute("""
        CREATE TABLE trading_stats (
            id INTEGER PRIMARY KEY DEFAULT 1,
            total_volume INTEGER NOT NULL DEFAULT 0,   -- jami aylanma (CODE)
            total_trades INTEGER NOT NULL DEFAULT 0,   -- jami tranzaksiyalar
            total_won INTEGER NOT NULL DEFAULT 0,      -- g'alaba soni
            platform_commission INTEGER NOT NULL DEFAULT 0  -- platform foydasi
        )
    """)
    c.execute("INSERT INTO trading_stats (id) VALUES (1)")
    print("  + jadval: trading_stats")

# Narx sozlamalari
c.execute("INSERT OR IGNORE INTO pricing_settings (key,value) VALUES ('trading_commission_pct','2')")
c.execute("INSERT OR IGNORE INTO pricing_settings (key,value) VALUES ('trading_min_bet','100')")
c.execute("INSERT OR IGNORE INTO pricing_settings (key,value) VALUES ('trading_max_bet','100000')")
c.execute("INSERT OR IGNORE INTO pricing_settings (key,value) VALUES ('trading_win_multiplier','195')")  # 195% = 95% foyda
print("  + trading narx sozlamalari")

conn.commit()
conn.close()
print("\nMigration V19 muvaffaqiyatli!")
