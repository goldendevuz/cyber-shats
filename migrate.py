#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CYBER SHATS — Ma'lumotlar migratsiya tizimi

Yangi versiya yuklaganda barcha foydalanuvchi ma'lumotlari
(email, parol, CODE, kurslar, sertifikatlar) saqlab qolinadi.

ISHLATISH:
    python migrate.py --backup    # Eski bazadan backup olish
    python migrate.py --restore   # Backup'dan tiklash
    python migrate.py --check     # Baza sog'lomligini tekshirish
    python migrate.py             # Avtomatik migratsiya

Yangi versiya yuklashdan OLDIN:
    python migrate.py --backup

Yangi versiya yuklagandan KEYIN:
    python migrate.py --restore
"""

import sqlite3
import json
import os
import sys
import datetime
import shutil
import argparse

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database", "cyber_shats.db")
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def backup_all_data(backup_file: str = None) -> str:
    """Barcha muhim ma'lumotlarni JSON ga saqlaydi."""
    if not backup_file:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs(BACKUP_DIR, exist_ok=True)
        backup_file = os.path.join(BACKUP_DIR, f"backup_{ts}.json")

    conn = get_db()
    c = conn.cursor()

    data = {
        "version": "1.3",
        "created_at": datetime.datetime.now().isoformat(),
        "tables": {}
    }

    # Saqlaniladigan jadvallar
    tables_to_backup = [
        "users", "user_themes", "code_transactions", "notifications",
        "lesson_progress", "certificates", "quiz_results",
        "bot_purchase_requests", "payment_requests",
        "telegram_users", "telegram_verifications",
        "pro_payments", "affiliate_earnings",
        "site_settings", "pricing_settings", "panel_status", "trading_trend",
        "trading_stats", "promo_codes", "promo_code_uses",
        "treasury_accounts", "fund_log",
        "startups", "startup_likes", "startup_auctions", "startup_auction_bids",
        "groups", "group_members", "group_posts",
        "channels", "channel_subscribers", "channel_posts",
        "stories", "story_views",
        "reels", "reel_likes", "reel_comments",
        "forum_posts", "forum_replies",
        "hacker_lab_consent", "hacker_lab_access",
        "hacker_lab_security_events",
        "announcements",
    ]

    total_rows = 0
    for table in tables_to_backup:
        try:
            c.execute(f"SELECT * FROM {table}")
            rows = [dict(r) for r in c.fetchall()]
            data["tables"][table] = rows
            total_rows += len(rows)
            if rows:
                print(f"  ✓ {table}: {len(rows)} ta yozuv")
        except sqlite3.OperationalError:
            pass  # Jadval mavjud emas

    conn.close()

    # Shuningdek DB faylini ham to'g'ridan-to'g'ri nusxalash
    db_backup = backup_file.replace(".json", ".db")
    shutil.copy2(DB_PATH, db_backup)

    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n✅ Backup saqlandi: {backup_file}")
    print(f"✅ DB nusxasi: {db_backup}")
    print(f"📊 Jami {total_rows} ta yozuv, {len(data['tables'])} ta jadval")
    return backup_file


def restore_from_backup(backup_file: str) -> bool:
    """JSON backup'dan ma'lumotlarni tiklaydi."""
    if not os.path.exists(backup_file):
        print(f"❌ Backup fayl topilmadi: {backup_file}")
        return False

    with open(backup_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Backup versiyasi: {data.get('version')}")
    print(f"Yaratilgan: {data.get('created_at')}")

    conn = get_db()
    c = conn.cursor()

    # Muhim jadvallar — foydalanuvchi ma'lumotlari
    priority_tables = ["users", "code_transactions", "lesson_progress",
                       "certificates", "user_themes", "site_settings",
                       "pricing_settings", "promo_codes"]

    total_restored = 0
    for table, rows in data["tables"].items():
        if not rows:
            continue
        try:
            # Jadval mavjudligini tekshirish
            c.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if not c.fetchone():
                print(f"  ⚠️  {table}: jadval yangi versiyada yo'q, o'tkazib yuborildi")
                continue

            # Unikum kalitlar bilan qo'shish
            cols = list(rows[0].keys())
            placeholders = ",".join(["?" for _ in cols])
            col_names = ",".join([f'"{c_}"' for c_ in cols])

            for row in rows:
                try:
                    c.execute(
                        f'INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})',
                        [row.get(col) for col in cols]
                    )
                    total_restored += 1
                except Exception as e:
                    pass  # Conflicts skip

            conn.commit()
            print(f"  ✓ {table}: {len(rows)} ta yozuv tiklandi")
        except Exception as e:
            print(f"  ✗ {table}: {e}")

    conn.close()
    print(f"\n✅ Jami {total_restored} ta yozuv tiklandi!")
    return True


def check_database():
    """Baza sog'lomligini tekshiradi."""
    print("🔍 Baza tekshirilmoqda...\n")
    conn = get_db()
    c = conn.cursor()

    checks = [
        ("users", "SELECT COUNT(*) FROM users"),
        ("Foydalanuvchi code balanslari", "SELECT SUM(code_balance) FROM users"),
        ("Bitirgan kurslar", "SELECT COUNT(*) FROM lesson_progress WHERE is_done=1"),
        ("Sertifikatlar", "SELECT COUNT(*) FROM certificates"),
        ("Promo kodlar", "SELECT COUNT(*) FROM promo_codes"),
        ("Trading pozitsiyalar", "SELECT COUNT(*) FROM trading_positions"),
    ]

    for label, query in checks:
        try:
            c.execute(query)
            result = c.fetchone()[0]
            print(f"  ✓ {label}: {result:,}" if isinstance(result, int) and result else f"  ✓ {label}: {result}")
        except Exception as e:
            print(f"  ✗ {label}: {e}")

    conn.close()
    print("\n✅ Tekshiruv yakunlandi!")


def auto_migrate():
    """
    Avtomatik migratsiya — yangi jadvallar va ustunlarni qo'shadi,
    mavjud ma'lumotlarni saqlab qoladi.
    """
    print("🔄 Avtomatik migratsiya boshlandi...\n")
    conn = get_db()
    c = conn.cursor()

    migrations = [
        # Promo kodlar
        """CREATE TABLE IF NOT EXISTS promo_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            discount_type TEXT NOT NULL DEFAULT 'pct',
            discount_value INTEGER NOT NULL DEFAULT 10,
            max_uses INTEGER NOT NULL DEFAULT 100,
            used_count INTEGER NOT NULL DEFAULT 0,
            expires_at TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_by INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            note TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS promo_code_uses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            promo_id INTEGER NOT NULL REFERENCES promo_codes(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            order_id INTEGER,
            discount_applied INTEGER NOT NULL DEFAULT 0,
            used_at TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        # Sayt sozlamalari
        """CREATE TABLE IF NOT EXISTS site_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        # Trading trend
        """CREATE TABLE IF NOT EXISTS trading_trend (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            direction TEXT NOT NULL DEFAULT 'neutral',
            target_change_pct REAL NOT NULL DEFAULT 0,
            duration_days INTEGER NOT NULL DEFAULT 7,
            volatility REAL NOT NULL DEFAULT 0.015,
            created_by INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            active INTEGER NOT NULL DEFAULT 1
        )""",
        # Panel holati
        """CREATE TABLE IF NOT EXISTS panel_status (
            panel_key TEXT PRIMARY KEY,
            is_active INTEGER NOT NULL DEFAULT 1,
            maintenance_msg TEXT DEFAULT NULL,
            updated_by INTEGER,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        # Foydalanuvchi temalari
        """CREATE TABLE IF NOT EXISTS user_themes (
            user_id INTEGER PRIMARY KEY REFERENCES users(id),
            primary_color TEXT NOT NULL DEFAULT '#00ff41',
            secondary_color TEXT NOT NULL DEFAULT '#00b8d9',
            accent_color TEXT NOT NULL DEFAULT '#ffd23f',
            bg_color TEXT NOT NULL DEFAULT '#0a0a0a',
            card_bg TEXT NOT NULL DEFAULT '#111111',
            border_color TEXT NOT NULL DEFAULT '#1a1a1a',
            font_style TEXT NOT NULL DEFAULT 'mono',
            glow_intensity TEXT NOT NULL DEFAULT 'medium',
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
    ]

    for sql in migrations:
        try:
            c.execute(sql)
            conn.commit()
        except Exception as e:
            if "already exists" not in str(e):
                print(f"  ⚠️  {e}")

    # Standart ma'lumotlar
    defaults = [
        ("INSERT OR IGNORE INTO site_settings (key,value) VALUES ('site_theme','football')", []),
        ("INSERT OR IGNORE INTO trading_trend (id,direction,target_change_pct,duration_days) VALUES (1,'neutral',0,7)", []),
        ("INSERT OR IGNORE INTO trading_stats (id) VALUES (1)", []),
    ]
    for sql, args in defaults:
        try:
            c.execute(sql, args)
            conn.commit()
        except Exception:
            pass

    conn.close()
    print("✅ Migratsiya yakunlandi!\n")


def main():
    parser = argparse.ArgumentParser(description="CYBER SHATS Ma'lumotlar Migratsiya Tizimi")
    parser.add_argument("--backup", action="store_true", help="Barcha ma'lumotlarni backup qilish")
    parser.add_argument("--restore", metavar="FILE", help="Backup fayldan tiklash")
    parser.add_argument("--check", action="store_true", help="Baza tekshiruvi")
    parser.add_argument("--list", action="store_true", help="Mavjud backup'lar ro'yxati")
    args = parser.parse_args()

    if args.backup:
        backup_all_data()
    elif args.restore:
        restore_from_backup(args.restore)
    elif args.check:
        check_database()
    elif args.list:
        if os.path.exists(BACKUP_DIR):
            files = sorted(os.listdir(BACKUP_DIR))
            for f in files:
                if f.endswith(".json"):
                    fpath = os.path.join(BACKUP_DIR, f)
                    size = os.path.getsize(fpath) / 1024
                    print(f"  {f} ({size:.1f} KB)")
        else:
            print("Backup papkasi yo'q")
    else:
        # Standart: avtomatik migratsiya
        auto_migrate()
        check_database()


if __name__ == "__main__":
    main()
