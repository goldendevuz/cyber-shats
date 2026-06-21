"""
CYBER SHATS V1.3 — Migration V14 (Bosqich 5 — Ijtimoiy tarmoq MVP)

GURUH (Group): har qanday foydalanuvchi yaratadi, a'zolar qo'shiladi,
ichida ko'p kishilik suhbat (matn + rasm) bo'ladi — Telegram guruhiga o'xshab.

KANAL (Channel): egasi/admin e'lon qiladi, a'zolar obuna bo'lib o'qiydi,
izoh qoldirishi mumkin — Telegram kanaliga o'xshab.
"""
import sqlite3, os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyber_shats.db")


def table_exists(c, table):
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return c.fetchone() is not None


conn = sqlite3.connect(DB)
c = conn.cursor()

# =================================================================
# GURUHLAR
# =================================================================
if not table_exists(c, "groups"):
    c.execute("""
        CREATE TABLE groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            avatar TEXT DEFAULT NULL,
            owner_id INTEGER NOT NULL REFERENCES users(id),
            is_public INTEGER NOT NULL DEFAULT 1,    -- 1=ochiq (har kim qo'shiladi), 0=yopiq (taklif kerak)
            member_count INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    print("  + jadval: groups")

if not table_exists(c, "group_members"):
    c.execute("""
        CREATE TABLE group_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL REFERENCES groups(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            role TEXT NOT NULL DEFAULT 'member',     -- 'owner', 'admin', 'member'
            joined_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(group_id, user_id)
        )
    """)
    c.execute("CREATE INDEX idx_gm_group ON group_members(group_id)")
    c.execute("CREATE INDEX idx_gm_user ON group_members(user_id)")
    print("  + jadval: group_members")

if not table_exists(c, "group_messages"):
    c.execute("""
        CREATE TABLE group_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL REFERENCES groups(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            body TEXT NOT NULL DEFAULT '',
            file_path TEXT DEFAULT NULL,
            file_type TEXT DEFAULT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX idx_gmsg_group ON group_messages(group_id, created_at)")
    print("  + jadval: group_messages")

# =================================================================
# KANALLAR
# =================================================================
if not table_exists(c, "channels"):
    c.execute("""
        CREATE TABLE channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            avatar TEXT DEFAULT NULL,
            owner_id INTEGER NOT NULL REFERENCES users(id),
            subscriber_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    print("  + jadval: channels")

if not table_exists(c, "channel_subscribers"):
    c.execute("""
        CREATE TABLE channel_subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id INTEGER NOT NULL REFERENCES channels(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            subscribed_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(channel_id, user_id)
        )
    """)
    c.execute("CREATE INDEX idx_cs_channel ON channel_subscribers(channel_id)")
    c.execute("CREATE INDEX idx_cs_user ON channel_subscribers(user_id)")
    print("  + jadval: channel_subscribers")

if not table_exists(c, "channel_posts"):
    c.execute("""
        CREATE TABLE channel_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id INTEGER NOT NULL REFERENCES channels(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            body TEXT NOT NULL DEFAULT '',
            file_path TEXT DEFAULT NULL,
            file_type TEXT DEFAULT NULL,
            views INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX idx_cpost_channel ON channel_posts(channel_id, created_at)")
    print("  + jadval: channel_posts")

if not table_exists(c, "channel_post_comments"):
    c.execute("""
        CREATE TABLE channel_post_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL REFERENCES channel_posts(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            body TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX idx_ccom_post ON channel_post_comments(post_id)")
    print("  + jadval: channel_post_comments")

conn.commit()
conn.close()
print("\nMigration V14 muvaffaqiyatli yakunlandi!")
