"""
CYBER SHATS V1.3 — Migration V15 (Bosqich 5 davomi — Stories & Reels)

STORIES: Instagram-uslubidagi vaqtinchalik kontent (rasm/video), 24 soatdan
keyin avtomatik yashiriladi (fon jarayoni shart emas — har so'rovda
expires_at < now tekshiriladi, xuddi plan_expires_at kabi).

REELS: qisqa vertikal videolar tasmasi, like funksiyasi bilan.
"""
import sqlite3, os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyber_shats.db")


def table_exists(c, table):
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return c.fetchone() is not None


conn = sqlite3.connect(DB)
c = conn.cursor()

# =================================================================
# STORIES — 24 soatlik vaqtinchalik kontent
# =================================================================
if not table_exists(c, "stories"):
    c.execute("""
        CREATE TABLE stories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            file_path TEXT NOT NULL,
            file_type TEXT NOT NULL DEFAULT 'image',   -- 'image' yoki 'video'
            caption TEXT NOT NULL DEFAULT '',
            view_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            expires_at TEXT NOT NULL                    -- created_at + 24 soat
        )
    """)
    c.execute("CREATE INDEX idx_stories_user ON stories(user_id, expires_at)")
    c.execute("CREATE INDEX idx_stories_expires ON stories(expires_at)")
    print("  + jadval: stories")

if not table_exists(c, "story_views"):
    c.execute("""
        CREATE TABLE story_views (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id INTEGER NOT NULL REFERENCES stories(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            viewed_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(story_id, user_id)
        )
    """)
    print("  + jadval: story_views")

# =================================================================
# REELS — qisqa vertikal videolar
# =================================================================
if not table_exists(c, "reels"):
    c.execute("""
        CREATE TABLE reels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            file_path TEXT NOT NULL,
            caption TEXT NOT NULL DEFAULT '',
            view_count INTEGER NOT NULL DEFAULT 0,
            like_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX idx_reels_created ON reels(created_at)")
    print("  + jadval: reels")

if not table_exists(c, "reel_likes"):
    c.execute("""
        CREATE TABLE reel_likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reel_id INTEGER NOT NULL REFERENCES reels(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(reel_id, user_id)
        )
    """)
    print("  + jadval: reel_likes")

if not table_exists(c, "reel_comments"):
    c.execute("""
        CREATE TABLE reel_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reel_id INTEGER NOT NULL REFERENCES reels(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            body TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX idx_reel_comments ON reel_comments(reel_id)")
    print("  + jadval: reel_comments")

conn.commit()
conn.close()
print("\nMigration V15 muvaffaqiyatli yakunlandi!")
