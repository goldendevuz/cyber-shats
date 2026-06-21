"""
CYBER SHATS V1.3 — Migration V18 (Startaplar Auksioni)

Foydalanuvchi loyiha/startap joylaydi -> admin ko'rib chiqadi -> tasdiqlasa
auksionga qo'yadi -> boshqa foydalanuvchilar CODE bilan tiklashadi (g'oyaga/
loyihaga "egalik" yoki "homiylik" huquqi sifatida) -> g'olib CODE to'laydi,
bu summa g'azna jamg'armasiga tushadi.
"""
import sqlite3, os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyber_shats.db")


def table_exists(c, table):
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return c.fetchone() is not None


def col_exists(c, table, col):
    c.execute(f"PRAGMA table_info({table})")
    return any(r[1] == col for r in c.fetchall())


conn = sqlite3.connect(DB)
c = conn.cursor()

if not table_exists(c, "startup_auctions"):
    c.execute("""
        CREATE TABLE startup_auctions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            startup_id INTEGER NOT NULL REFERENCES startups(id),
            start_price INTEGER NOT NULL DEFAULT 10000,
            current_bid INTEGER NOT NULL DEFAULT 0,
            current_bidder_id INTEGER DEFAULT NULL REFERENCES users(id),
            starts_at TEXT NOT NULL DEFAULT (datetime('now')),
            ends_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',  -- active, ended, cancelled
            created_by INTEGER NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX idx_startup_auctions_status ON startup_auctions(status)")
    print("  + jadval: startup_auctions")

if not table_exists(c, "startup_auction_bids"):
    c.execute("""
        CREATE TABLE startup_auction_bids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            auction_id INTEGER NOT NULL REFERENCES startup_auctions(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            amount INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX idx_startup_bids_auction ON startup_auction_bids(auction_id)")
    print("  + jadval: startup_auction_bids")

# startups jadvaliga auksion holatini bilish uchun maydon
if not col_exists(c, "startups", "in_auction"):
    c.execute("ALTER TABLE startups ADD COLUMN in_auction INTEGER NOT NULL DEFAULT 0")
    print("  + startups.in_auction")

c.execute("INSERT OR IGNORE INTO pricing_settings (key, value) VALUES ('startup_auction_default_price', '10000')")
c.execute("INSERT OR IGNORE INTO pricing_settings (key, value) VALUES ('startup_auction_default_days', '7')")
print("  + narxlar: startup_auction_default_price=10000, startup_auction_default_days=7")

conn.commit()
conn.close()
print("\nMigration V18 muvaffaqiyatli yakunlandi!")
