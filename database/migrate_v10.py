"""
CYBER SHATS V1.3 — Migration V10 (Bosqich 1)
Barcha soxta/demo foydalanuvchilarni o'chirish — faqat real ro'yxatdan
o'tganlar (va sizning admin hisobingiz) qoladi.

O'chiriladi:
- 137 ta demo_user_* (bootstrap_v13.py orqali yaratilgan)
- admin@cybershats.uz, mentor@cybershats.uz (asl seed hisoblar)
- jasur/dilnoza/sardor/madina/bekzod @example.com (asl seed hisoblar)

Saqlanadi:
- avazbek@mixridinov (sizning real super_admin hisobingiz)
- G'azna xodimlari (treasury_accounts — alohida jadval, tegilmaydi)

DIQQAT: Bu amal qaytarib bo'lmaydi. Zaxira nusxa kerak bo'lsa, oldin
database/cyber_shats.db faylini nusxalab oling.

Ishga tushirish: python database/migrate_v10.py
"""
import sqlite3, os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyber_shats.db")

# Saqlanadigan email(lar) — bu ro'yxatdagilar HECH QACHON o'chirilmaydi
KEEP_EMAILS = ["avazbek@mixridinov"]

USER_RELATED_TABLES = [
    "enrollments", "lesson_progress", "test_attempts", "forum_posts", "forum_replies",
    "certificates", "notifications", "user_badges", "action_logs", "ai_messages",
    "code_transactions", "pro_payments", "oauth_links", "security_events",
    "user_ratings", "auction_bids", "smm_ai_messages", "treasury_fund_log",
    "certificate_applications", "direction_exam_attempts", "announcement_views",
    "ping_test_usage", "push_subscriptions",
]

# Bu jadvallarda user_id NULL bo'lishi mumkin (masalan treasury_fund_log.user_id),
# shuning uchun faqat user_id mavjud bo'lganlarni o'chiramiz.


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("PRAGMA foreign_keys = OFF")

    placeholders = ",".join("?" for _ in KEEP_EMAILS)
    to_delete = c.execute(
        f"SELECT id, email FROM users WHERE email NOT IN ({placeholders})",
        KEEP_EMAILS
    ).fetchall()

    if not to_delete:
        print("O'chiriladigan foydalanuvchi topilmadi.")
        conn.close()
        return

    delete_ids = [r["id"] for r in to_delete]
    print(f"O'chiriladigan foydalanuvchilar soni: {len(delete_ids)}")
    for r in to_delete[:10]:
        print(f"  - {r['email']} (id={r['id']})")
    if len(to_delete) > 10:
        print(f"  ... va yana {len(to_delete) - 10} ta")

    id_placeholders = ",".join("?" for _ in delete_ids)

    # Bog'liq jadvallardagi yozuvlarni tozalash
    for table in USER_RELATED_TABLES:
        try:
            c.execute(f"DELETE FROM {table} WHERE user_id IN ({id_placeholders})", delete_ids)
            print(f"  tozalandi: {table} ({c.rowcount} qator)")
        except sqlite3.OperationalError as e:
            print(f"  o'tkazib yuborildi: {table} ({e})")

    # premium_ids.owner_user_id — egasi o'chirilsa, ID yana "available" bo'lsin
    c.execute(
        f"UPDATE premium_ids SET status='available', owner_user_id=NULL, sold_at=NULL "
        f"WHERE owner_user_id IN ({id_placeholders})", delete_ids
    )
    print(f"  premium_ids tozalandi: {c.rowcount} ta ID 'available' holatiga qaytdi")

    # id_auctions.current_bidder_id — agar shu foydalanuvchilarga tegishli bo'lsa, tozalash
    try:
        c.execute(
            f"UPDATE id_auctions SET current_bidder_id=NULL, current_bid=0 "
            f"WHERE current_bidder_id IN ({id_placeholders})", delete_ids
        )
        print(f"  id_auctions tozalandi: {c.rowcount} qator")
    except sqlite3.OperationalError:
        pass

    # private_messages va coin_transfers — sender/receiver bo'lishi mumkin
    for table, cols in [
        ("private_messages", ["sender_id", "receiver_id"]),
        ("coin_transfers", ["from_user_id", "to_user_id"]),
    ]:
        try:
            for col in cols:
                c.execute(f"DELETE FROM {table} WHERE {col} IN ({id_placeholders})", delete_ids)
            print(f"  tozalandi: {table}")
        except sqlite3.OperationalError as e:
            print(f"  o'tkazib yuborildi: {table} ({e})")

    # bot_purchase_requests.site_user_id
    try:
        c.execute(f"DELETE FROM bot_purchase_requests WHERE site_user_id IN ({id_placeholders})", delete_ids)
        print(f"  tozalandi: bot_purchase_requests")
    except sqlite3.OperationalError:
        pass

    # Asosiy users jadvalidan o'chirish
    c.execute(f"DELETE FROM users WHERE id IN ({id_placeholders})", delete_ids)
    print(f"\n  users jadvalidan o'chirildi: {c.rowcount} ta")

    conn.commit()

    remaining = c.execute("SELECT id, email, role FROM users").fetchall()
    print(f"\nQolgan foydalanuvchilar ({len(remaining)} ta):")
    for r in remaining:
        print(f"  - {r['email']} (id={r['id']}, role={r['role']})")

    conn.close()
    print("\nMigration V10 muvaffaqiyatli yakunlandi!")


if __name__ == "__main__":
    main()
