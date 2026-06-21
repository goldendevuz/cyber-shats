# ============================================================
# CYBER SHATS — Baza bilan ishlash uchun yordamchi funksiyalar
# ============================================================
import sqlite3
from flask import g, current_app


def get_db():
    """Joriy so'rov uchun SQLite ulanishini qaytaradi (har bir request uchun bitta)."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DB_PATH"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


# ------------------------------------------------------------------
# AVTOMATIK SCHEMA TEKSHIRUVI (V2 — V7 migratsiyalarining yig'indisi)
# ------------------------------------------------------------------
# Eski baza fayllarida (masalan, migrate_v6.py / migrate_v7.py qo'lda
# ishga tushirilmagan bo'lsa) ba'zi jadvallar yo'q bo'lib qoladi va
# "no such table: ..." xatosi chiqadi (masalan ping_test_usage,
# certificate_applications). Bu funksiya ilova ishga tushganda bir marta
# chaqiriladi va yetishmayotgan jadval/ustunlarni CREATE TABLE IF NOT
# EXISTS / ALTER TABLE orqali xavfsiz qo'shib qo'yadi. Mavjud ma'lumotga
# tegmaydi, faqat yo'q narsalarni qo'shadi.
def _col_exists(conn, table, col):
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == col for r in rows)


def _table_exists(conn, table):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def ensure_schema(db_path):
    """Baza faylida yetishmayotgan jadval/ustunlarni avtomatik yaratadi."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    # --- users jadvaliga yetishmayotgan ustunlar (V1/V2/V4) ---
    if _table_exists(conn, "users"):
        for col, defn in [
            ("code_balance", "INTEGER NOT NULL DEFAULT 0"),
            ("oauth_provider", "TEXT DEFAULT ''"),
            ("last_login_ip", "TEXT DEFAULT ''"),
            ("failed_login_count", "INTEGER NOT NULL DEFAULT 0"),
            ("locked_until", "TEXT DEFAULT NULL"),
            ("custom_id", "TEXT UNIQUE DEFAULT NULL"),
            ("admin_id", "TEXT DEFAULT NULL"),
            ("treasury_password_hash", "TEXT DEFAULT NULL"),
        ]:
            if not _col_exists(conn, "users", col):
                conn.execute(f"ALTER TABLE users ADD COLUMN {col} {defn}")

        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_admin_id "
            "ON users(admin_id) WHERE admin_id IS NOT NULL"
        )

    # --- courses / directions yetishmayotgan ustunlar ---
    if _table_exists(conn, "courses"):
        for col, defn in [
            ("code_price", "INTEGER NOT NULL DEFAULT 0"),
            ("is_pro_only", "INTEGER NOT NULL DEFAULT 0"),
            ("is_paid", "INTEGER NOT NULL DEFAULT 0"),
        ]:
            if not _col_exists(conn, "courses", col):
                conn.execute(f"ALTER TABLE courses ADD COLUMN {col} {defn}")

    if _table_exists(conn, "directions"):
        for col, defn in [
            ("is_pro_only", "INTEGER NOT NULL DEFAULT 0"),
            ("is_cyber_pro_only", "INTEGER NOT NULL DEFAULT 0"),
        ]:
            if not _col_exists(conn, "directions", col):
                conn.execute(f"ALTER TABLE directions ADD COLUMN {col} {defn}")

    # --- pricing_settings (V2) ---
    if not _table_exists(conn, "pricing_settings"):
        conn.execute("""
            CREATE TABLE pricing_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_by INTEGER DEFAULT NULL REFERENCES users(id)
            )
        """)

    # --- admin_action_audit (V2) ---
    if not _table_exists(conn, "admin_action_audit"):
        conn.execute("""
            CREATE TABLE admin_action_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_id INTEGER NOT NULL REFERENCES users(id),
                target_id INTEGER DEFAULT NULL REFERENCES users(id),
                action TEXT NOT NULL,
                details TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

    # --- Default narx sozlamalari (V2) ---
    if _table_exists(conn, "pricing_settings"):
        defaults = {
            "pro_price_uzs": "99000",
            "pro_price_code": "57000",
            "pro_ai_limit": "100",
            "pro_duration_days": "30",
            "free_ai_limit": "10",
            "free_test_limit": "30",
            "free_smm_access": "0",
            "course_reward_code": "100",
            "ai_cost_per_msg": "200",
            "paid_course_code_default": "10000",
            "coin_transfer_fee_percent": "5",
            "certificate_exam_fee": "20000",
            "ping_test_free_quota": "10",
            "ping_test_cost_free": "2000",
            "ping_test_pro_quota": "20",
            "ping_test_cost_pro": "1000",
            "ping_test_cyber_pro_quota": "30",
            "ping_test_cost_cyber_pro": "500",
        }
        for k, v in defaults.items():
            conn.execute(
                "INSERT OR IGNORE INTO pricing_settings (key, value) VALUES (?,?)", (k, v)
            )

    # --- coin_transfers / private_messages (V3) ---
    if not _table_exists(conn, "coin_transfers"):
        conn.execute("""
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
        conn.execute("CREATE INDEX idx_coin_transfers_from ON coin_transfers(from_user_id)")
        conn.execute("CREATE INDEX idx_coin_transfers_to ON coin_transfers(to_user_id)")

    if not _table_exists(conn, "private_messages"):
        conn.execute("""
            CREATE TABLE private_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL REFERENCES users(id),
                receiver_id INTEGER NOT NULL REFERENCES users(id),
                body TEXT NOT NULL DEFAULT '',
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("CREATE INDEX idx_pm_sender ON private_messages(sender_id)")
        conn.execute("CREATE INDEX idx_pm_receiver ON private_messages(receiver_id)")
        conn.execute("CREATE INDEX idx_pm_pair ON private_messages(sender_id, receiver_id, created_at)")

    # --- treasury_accounts / treasury_fund / treasury_fund_log (V5) ---
    if not _table_exists(conn, "treasury_accounts"):
        conn.execute("""
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

    if not _table_exists(conn, "treasury_fund"):
        conn.execute("""
            CREATE TABLE treasury_fund (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                balance INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("INSERT OR IGNORE INTO treasury_fund (id, balance) VALUES (1, 0)")

    if not _table_exists(conn, "treasury_fund_log"):
        conn.execute("""
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
        conn.execute("CREATE INDEX idx_treasury_log_user ON treasury_fund_log(user_id)")
        conn.execute("CREATE INDEX idx_treasury_log_created ON treasury_fund_log(created_at)")

    # --- certificate_applications / direction_exam_attempts (V6) ---
    if not _table_exists(conn, "certificate_applications"):
        conn.execute("""
            CREATE TABLE certificate_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                direction_id INTEGER NOT NULL REFERENCES directions(id),
                custom_id TEXT NOT NULL,
                exam_score INTEGER NOT NULL,
                exam_total INTEGER NOT NULL,
                paid_amount INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                admin_note TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                reviewed_at TEXT DEFAULT NULL,
                reviewed_by INTEGER DEFAULT NULL REFERENCES users(id),
                certificate_number TEXT DEFAULT NULL
            )
        """)
        conn.execute("CREATE INDEX idx_cert_app_user ON certificate_applications(user_id)")
        conn.execute("CREATE INDEX idx_cert_app_status ON certificate_applications(status)")

    if not _table_exists(conn, "direction_exam_attempts"):
        conn.execute("""
            CREATE TABLE direction_exam_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                direction_id INTEGER NOT NULL REFERENCES directions(id),
                test_score INTEGER NOT NULL,
                test_total INTEGER NOT NULL,
                practice_score INTEGER NOT NULL,
                practice_total INTEGER NOT NULL,
                total_score INTEGER NOT NULL,
                max_total INTEGER NOT NULL,
                passed INTEGER NOT NULL,
                paid_amount INTEGER NOT NULL,
                started_at TEXT NOT NULL DEFAULT (datetime('now')),
                finished_at TEXT DEFAULT NULL
            )
        """)
        conn.execute("CREATE INDEX idx_dir_exam_user ON direction_exam_attempts(user_id)")

    # --- announcements / announcement_views / ping_test_usage (V7) ---
    if not _table_exists(conn, "announcements"):
        conn.execute("""
            CREATE TABLE announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                body TEXT NOT NULL DEFAULT '',
                priority TEXT NOT NULL DEFAULT 'normal',
                target_plans TEXT NOT NULL DEFAULT 'all',
                is_active INTEGER NOT NULL DEFAULT 1,
                voice_enabled INTEGER NOT NULL DEFAULT 1,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                expires_at TEXT DEFAULT NULL
            )
        """)
        conn.execute("CREATE INDEX idx_announcements_active ON announcements(is_active, created_at)")

    if not _table_exists(conn, "announcement_views"):
        conn.execute("""
            CREATE TABLE announcement_views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                announcement_id INTEGER NOT NULL REFERENCES announcements(id),
                user_id INTEGER NOT NULL REFERENCES users(id),
                viewed_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(announcement_id, user_id)
            )
        """)

    if not _table_exists(conn, "ping_test_usage"):
        conn.execute("""
            CREATE TABLE ping_test_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                target TEXT NOT NULL,
                response_time_ms INTEGER NOT NULL,
                success INTEGER NOT NULL DEFAULT 1,
                was_paid INTEGER NOT NULL DEFAULT 0,
                cost_paid INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("CREATE INDEX idx_ping_usage_user ON ping_test_usage(user_id, created_at)")

    conn.commit()
    conn.close()


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query_one(sql, args=()):
    cur = get_db().execute(sql, args)
    row = cur.fetchone()
    return dict(row) if row else None


def query_all(sql, args=()):
    cur = get_db().execute(sql, args)
    rows = cur.fetchall()
    return [dict(r) for r in rows]


def execute(sql, args=()):
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.lastrowid


def log_action(user_id, action, details="", ip=""):
    """Har bir muhim amalni xavfsizlik jurnaliga (action_logs) yozadi."""
    try:
        execute(
            "INSERT INTO action_logs (user_id, action, details, ip) VALUES (?,?,?,?)",
            (user_id, action, details, ip),
        )
    except Exception:
        pass  # log yozilmasa ham asosiy funksiya to'xtamasligi kerak
