-- ============================================================
-- CYBER SHATS — MA'LUMOTLAR BAZASI SXEMASI (SQLite)
-- ============================================================
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ism TEXT NOT NULL,
    familiya TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'student',
    avatar TEXT DEFAULT '',
    bio TEXT DEFAULT '',
    xp INTEGER NOT NULL DEFAULT 0,
    level INTEGER NOT NULL DEFAULT 1,
    plan TEXT NOT NULL DEFAULT 'free',
    is_blocked INTEGER NOT NULL DEFAULT 0,
    code_balance INTEGER NOT NULL DEFAULT 0,
    oauth_provider TEXT DEFAULT '',
    last_login_ip TEXT DEFAULT '',
    failed_login_count INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT DEFAULT NULL,
    custom_id TEXT UNIQUE DEFAULT NULL,
    admin_id TEXT DEFAULT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_admin_id ON users(admin_id) WHERE admin_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS directions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    name_uz TEXT NOT NULL,
    icon TEXT NOT NULL DEFAULT 'code',
    description TEXT DEFAULT '',
    course_count INTEGER NOT NULL DEFAULT 0,
    color TEXT NOT NULL DEFAULT 'green',
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_pro_only INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    direction_id INTEGER NOT NULL REFERENCES directions(id),
    title TEXT NOT NULL,
    subtitle TEXT DEFAULT '',
    description TEXT DEFAULT '',
    level TEXT NOT NULL DEFAULT 'Boshlang''ich',
    duration_weeks INTEGER NOT NULL DEFAULT 6,
    lessons_count INTEGER NOT NULL DEFAULT 10,
    students_count INTEGER NOT NULL DEFAULT 0,
    rating REAL NOT NULL DEFAULT 4.7,
    price INTEGER NOT NULL DEFAULT 0,
    icon TEXT NOT NULL DEFAULT 'shield',
    is_active INTEGER NOT NULL DEFAULT 1,
    code_price INTEGER NOT NULL DEFAULT 0,
    is_pro_only INTEGER NOT NULL DEFAULT 0,
    is_paid INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS modules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL REFERENCES courses(id),
    order_num INTEGER NOT NULL DEFAULT 0,
    title TEXT NOT NULL,
    icon TEXT NOT NULL DEFAULT 'layers',
    lessons_count INTEGER NOT NULL DEFAULT 3
);

CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL REFERENCES courses(id),
    module_id INTEGER REFERENCES modules(id),
    order_num INTEGER NOT NULL DEFAULT 0,
    title TEXT NOT NULL,
    duration_seconds INTEGER NOT NULL DEFAULT 600,
    content_html TEXT DEFAULT '',
    has_practice INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    course_id INTEGER NOT NULL REFERENCES courses(id),
    progress_percent INTEGER NOT NULL DEFAULT 0,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    UNIQUE(user_id, course_id)
);

CREATE TABLE IF NOT EXISTS lesson_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    lesson_id INTEGER NOT NULL REFERENCES lessons(id),
    is_done INTEGER NOT NULL DEFAULT 0,
    UNIQUE(user_id, lesson_id)
);

CREATE TABLE IF NOT EXISTS tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER REFERENCES courses(id),
    title TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL DEFAULT 15
);

CREATE TABLE IF NOT EXISTS test_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id INTEGER NOT NULL REFERENCES tests(id),
    order_num INTEGER NOT NULL DEFAULT 0,
    question_text TEXT NOT NULL,
    option_a TEXT NOT NULL,
    option_b TEXT NOT NULL,
    option_c TEXT NOT NULL,
    option_d TEXT NOT NULL,
    correct_option TEXT NOT NULL DEFAULT 'a'
);

CREATE TABLE IF NOT EXISTS test_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    test_id INTEGER NOT NULL REFERENCES tests(id),
    score INTEGER NOT NULL DEFAULT 0,
    total INTEGER NOT NULL DEFAULT 0,
    completed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS forum_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'umumiy',
    views INTEGER NOT NULL DEFAULT 0,
    replies_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS forum_replies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL REFERENCES forum_posts(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    body TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS certificates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    course_id INTEGER NOT NULL REFERENCES courses(id),
    cert_code TEXT NOT NULL UNIQUE,
    issued_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    type TEXT NOT NULL DEFAULT 'info',
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'Cyber Shats',
    category TEXT NOT NULL DEFAULT 'umumiy',
    published_at TEXT NOT NULL DEFAULT (datetime('now')),
    url TEXT DEFAULT '#'
);

CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'PDF',
    size_label TEXT NOT NULL DEFAULT '2.4 MB',
    category TEXT NOT NULL DEFAULT 'umumiy',
    file_url TEXT DEFAULT '#'
);

CREATE TABLE IF NOT EXISTS badges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    icon TEXT NOT NULL DEFAULT 'award',
    description TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS user_badges (
    user_id INTEGER NOT NULL REFERENCES users(id),
    badge_id INTEGER NOT NULL REFERENCES badges(id),
    earned_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, badge_id)
);

CREATE TABLE IF NOT EXISTS action_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    details TEXT DEFAULT '',
    ip TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ai_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    assistant_type TEXT NOT NULL DEFAULT 'umumiy',
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS code_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    amount INTEGER NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    ref_id INTEGER DEFAULT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pro_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    method TEXT NOT NULL DEFAULT 'code',
    amount_code INTEGER DEFAULT 0,
    amount_uzs INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    txn_id TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS oauth_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    provider TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    email TEXT DEFAULT '',
    name TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(provider, provider_id)
);

CREATE TABLE IF NOT EXISTS security_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER DEFAULT NULL,
    event_type TEXT NOT NULL,
    ip TEXT DEFAULT '',
    user_agent TEXT DEFAULT '',
    details TEXT DEFAULT '',
    severity TEXT NOT NULL DEFAULT 'low',
    is_blocked INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS blocked_ips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip TEXT NOT NULL UNIQUE,
    reason TEXT DEFAULT '',
    blocked_by INTEGER DEFAULT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS user_ratings (
    user_id INTEGER PRIMARY KEY REFERENCES users(id),
    total_score INTEGER NOT NULL DEFAULT 0,
    courses_done INTEGER NOT NULL DEFAULT 0,
    tests_passed INTEGER NOT NULL DEFAULT 0,
    rank_position INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- YANGI: Premium IDlar, Auktsion, SMM AI, Kurs Access Kodlari
-- ============================================================

CREATE TABLE IF NOT EXISTS premium_ids (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    custom_id TEXT NOT NULL UNIQUE,
    id_type TEXT NOT NULL DEFAULT 'normal',
    base_price INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'available',
    owner_user_id INTEGER DEFAULT NULL REFERENCES users(id),
    sold_at TEXT DEFAULT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS id_auctions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    premium_id_id INTEGER NOT NULL REFERENCES premium_ids(id),
    custom_id TEXT NOT NULL,
    start_price INTEGER NOT NULL DEFAULT 40000,
    current_bid INTEGER NOT NULL DEFAULT 0,
    current_bidder_id INTEGER DEFAULT NULL REFERENCES users(id),
    starts_at TEXT NOT NULL DEFAULT (datetime('now')),
    ends_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS auction_bids (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    auction_id INTEGER NOT NULL REFERENCES id_auctions(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    bid_amount INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS smm_ai_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    direction TEXT NOT NULL DEFAULT 'smm',
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS course_access_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL REFERENCES courses(id),
    access_code TEXT NOT NULL UNIQUE,
    is_used INTEGER NOT NULL DEFAULT 0,
    used_by INTEGER DEFAULT NULL REFERENCES users(id),
    used_at TEXT DEFAULT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- YANGI: Narxlar boshqaruvi (admin tahrirlay oladigan global sozlamalar)
-- ============================================================

CREATE TABLE IF NOT EXISTS pricing_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_by INTEGER DEFAULT NULL REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS admin_action_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id INTEGER NOT NULL REFERENCES users(id),
    target_id INTEGER DEFAULT NULL REFERENCES users(id),
    action TEXT NOT NULL,
    details TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- YANGI: Foydalanuvchilar orasida code tangasi o'tkazmasi (P2P)
-- ============================================================

CREATE TABLE IF NOT EXISTS coin_transfers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_user_id INTEGER NOT NULL REFERENCES users(id),
    to_user_id INTEGER NOT NULL REFERENCES users(id),
    amount_sent INTEGER NOT NULL,      -- jo'natuvchi hisobidan yechilgan umumiy summa (komissiya bilan)
    fee_amount INTEGER NOT NULL DEFAULT 0,
    amount_received INTEGER NOT NULL,  -- qabul qiluvchiga tushgan summa (komissiyasiz)
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_coin_transfers_from ON coin_transfers(from_user_id);
CREATE INDEX IF NOT EXISTS idx_coin_transfers_to ON coin_transfers(to_user_id);

-- ============================================================
-- YANGI: Foydalanuvchilar orasidagi shaxsiy xabarlashuv (Telegram uslubida)
-- ============================================================

CREATE TABLE IF NOT EXISTS private_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL REFERENCES users(id),
    receiver_id INTEGER NOT NULL REFERENCES users(id),
    body TEXT NOT NULL DEFAULT '',
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_pm_sender ON private_messages(sender_id);
CREATE INDEX IF NOT EXISTS idx_pm_receiver ON private_messages(receiver_id);
CREATE INDEX IF NOT EXISTS idx_pm_pair ON private_messages(sender_id, receiver_id, created_at);

-- ============================================================
-- YANGI: G'AZNA (Code Panel) — foydalanuvchilar tizimidan butunlay mustaqil.
-- O'z login (email+parol) hisoblari, o'z jamg'arma balansi.
-- ============================================================

-- G'azna xodimlari (foydalanuvchilar emas — alohida login tizimi)
CREATE TABLE IF NOT EXISTS treasury_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ism TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_login_at TEXT DEFAULT NULL
);

-- Jamg'arma balansi — bitta qator (singleton), 0 dan boshlanadi.
-- Faqat foydalanuvchilar sarflagan/komissiya sifatida bergan coinlardan to'ladi.
CREATE TABLE IF NOT EXISTS treasury_fund (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    balance INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
INSERT OR IGNORE INTO treasury_fund (id, balance) VALUES (1, 0);

-- Jamg'arma harakatlari tarixi (kirim: foydalanuvchi sarfi/komissiya; chiqim: foydalanuvchiga chiqarilgan coin)
CREATE TABLE IF NOT EXISTS treasury_fund_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    direction TEXT NOT NULL,              -- 'in' yoki 'out'
    amount INTEGER NOT NULL,
    reason TEXT NOT NULL DEFAULT '',      -- masalan: buy_pro, buy_course, ai_usage, transfer_fee, issue_to_user
    user_id INTEGER DEFAULT NULL REFERENCES users(id),     -- tegishli bo'lgan foydalanuvchi (agar bor bo'lsa)
    treasury_account_id INTEGER DEFAULT NULL REFERENCES treasury_accounts(id),  -- chiqarishni amalga oshirgan g'azna xodimi
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_treasury_log_user ON treasury_fund_log(user_id);
CREATE INDEX IF NOT EXISTS idx_treasury_log_created ON treasury_fund_log(created_at);
