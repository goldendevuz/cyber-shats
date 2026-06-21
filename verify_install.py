"""
CYBER SHATS V1.3 — Diagnostika skripti

Bu skript loyihangizning to'g'ri o'rnatilganligini tekshiradi va
nima yetishmayotganini ko'rsatadi.

Ishga tushirish:  python verify_install.py
"""
import os
import sys

print("=" * 70)
print("CYBER SHATS V1.3 — DIAGNOSTIKA")
print("=" * 70)
print(f"\nIshlash papkasi: {os.getcwd()}")
print(f"Python versiyasi: {sys.version.split()[0]}")

# 1. Kerakli fayllar mavjudligi
print("\n[1] KERAKLI FAYLLAR:")
required_files = [
    "app.py",
    "treasury.py",
    "messaging.py",
    "coins.py",
    "pricing.py",
    "database/cyber_shats.db",
    "database/bootstrap_v13.py",
    "database/import_premium_ids_v13.py",
    "database/demo_users.txt",
    "templates/treasury_login.html",
    "templates/treasury_dashboard.html",
    "templates/treasury_accounts.html",
]
missing = []
for f in required_files:
    exists = os.path.exists(f)
    print(f"    {'OK' if exists else 'YOQ'} {f}")
    if not exists:
        missing.append(f)

if missing:
    print(f"\n*** XATO: {len(missing)} ta kerakli fayl YO'Q ***")
    print("Yangi zip arxivini to'liq ochmagansiz!")
    sys.exit(1)

# 2. Database tekshirish
print("\n[2] DATABASE TEKSHIRISH:")
try:
    import sqlite3
    conn = sqlite3.connect("database/cyber_shats.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    needed = ['treasury_accounts', 'treasury_fund', 'treasury_fund_log',
              'coin_transfers', 'private_messages', 'premium_ids']
    for t in needed:
        print(f"    {'OK' if t in tables else 'YOQ'} jadval: {t}")

    # 3. Sizning hisoblar
    print("\n[3] HISOBLAR:")
    admin = c.execute("SELECT id, ism, email, role FROM users WHERE email='avazbek@mixridinov'").fetchone()
    if admin:
        print(f"    OK Admin: {admin['ism']} ({admin['email']}) role={admin['role']}")
    else:
        print("    YOQ Admin (avazbek@mixridinov) topilmadi!")

    treas = c.execute("SELECT id, ism, email FROM treasury_accounts WHERE email='kassa@shats'").fetchone()
    if treas:
        print(f"    OK G'aznachi: {treas['ism']} ({treas['email']})")
    else:
        print("    YOQ G'aznachi (kassa@shats) topilmadi!")

    # 4. Demo users
    demo_count = c.execute("SELECT COUNT(*) c FROM users WHERE email LIKE 'demo_user_%'").fetchone()[0]
    print(f"\n[4] DEMO FOYDALANUVCHILAR: {demo_count} ta (kutilgan 137)")

    # 5. Premium IDs
    print("\n[5] PREMIUM IDLAR (TOIFA BO'YICHA):")
    for r in c.execute("SELECT id_type, COUNT(*) c FROM premium_ids GROUP BY id_type ORDER BY id_type"):
        print(f"    {r['id_type']}: {r['c']} ta")
    total = c.execute("SELECT COUNT(*) c FROM premium_ids").fetchone()[0]
    print(f"    JAMI: {total} ta")

    # 6. Narxlar
    print("\n[6] NARXLAR SOZLAMASI:")
    for k in ['welcome_bonus_code', 'cyber_pro_price_code', 'certificate_exam_fee',
              'id_tier_A_min', 'id_tier_A_max', 'ping_test_cost_free']:
        r = c.execute("SELECT value FROM pricing_settings WHERE key=?", (k,)).fetchone()
        print(f"    {k}: {r[0] if r else 'YOQ (default ishlatiladi)'}")

    conn.close()
except Exception as e:
    print(f"    XATO: {e}")

# 7. Flask import qilish va Treasury sahifasi ishlashini tekshirish
print("\n[7] FLASK ILOVASI:")
try:
    os.environ['SECRET_KEY'] = 'test'
    import app as application
    client = application.app.test_client()
    r = client.get('/treasury/login')
    print(f"    /treasury/login javob: {r.status_code} {'OK' if r.status_code == 200 else 'XATO'}")
    r2 = client.get('/login')
    print(f"    /login javob: {r2.status_code} {'OK' if r2.status_code == 200 else 'XATO'}")
except Exception as e:
    print(f"    XATO: {e}")

print("\n" + "=" * 70)
print("DIAGNOSTIKA TUGADI")
print("=" * 70)
print("\nAGAR HAMMASI 'OK' BO'LSA — fayllar to'g'ri o'rnatilgan.")
print("Endi: python app.py  va brauzerda http://localhost:5000 oching")
print("\nMUHIM: Brauzerda Ctrl+Shift+R bosing (kesh tozalash)")
