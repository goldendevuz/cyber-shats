"""
CYBER SHATS V1.3 — Diagnostika skripti

Bu skript loyihangizning to'g'ri o'rnatilganligini tekshiradi va
nima yetishmayotganini ko'rsatadi (kerakli fayllar, Python kutubxonalari,
database holati, asosiy sahifalar ishlashi).

Ishga tushirish:  python verify_install.py
"""
import os
import sys

print("=" * 70)
print("CYBER SHATS V1.3 — DIAGNOSTIKA")
print("=" * 70)
print(f"\nIshlash papkasi: {os.getcwd()}")
print(f"Python versiyasi: {sys.version.split()[0]}")

# ============================================================
# 1. PYTHON KUTUBXONALARI (eng ko'p uchraydigan xato manbai)
# ============================================================
print("\n[1] PYTHON KUTUBXONALARI (requirements.txt):")
required_packages = [
    ("flask", "Flask"),
    ("werkzeug", "Werkzeug"),
    ("reportlab", "reportlab"),
    ("qrcode", "qrcode"),
    ("PIL", "Pillow"),
    ("anthropic", "anthropic"),
    ("dotenv", "python-dotenv"),
    ("requests", "requests"),
    ("pywebpush", "pywebpush"),
    ("markdown", "Markdown"),
]
missing_packages = []
for import_name, pip_name in required_packages:
    try:
        __import__(import_name)
        print(f"    OK {pip_name}")
    except ImportError:
        print(f"    YOQ {pip_name}  <-- O'RNATILMAGAN!")
        missing_packages.append(pip_name)

if missing_packages:
    print(f"\n*** DIQQAT: {len(missing_packages)} ta kutubxona o'rnatilmagan! ***")
    print("    Quyidagi buyruqni ishga tushiring:")
    print("    pip install -r requirements.txt")
    print("    (yoki: pip install " + " ".join(missing_packages) + ")")
else:
    print("\n    Barcha kutubxonalar o'rnatilgan.")

# ============================================================
# 2. KERAKLI FAYLLAR
# ============================================================
print("\n[2] KERAKLI FAYLLAR:")
required_files = [
    "app.py",
    "treasury.py",
    "messaging.py",
    "coins.py",
    "pricing.py",
    "social.py",
    "startups.py",
    "hacker_lab.py",
    "telegram_verify.py",
    "database/cyber_shats.db",
    "templates/treasury_login.html",
    "templates/treasury_dashboard.html",
    "templates/hacker_lab.html",
    "templates/startups_list.html",
]
missing_files = []
for f in required_files:
    exists = os.path.exists(f)
    print(f"    {'OK' if exists else 'YOQ'} {f}")
    if not exists:
        missing_files.append(f)

if missing_files:
    print(f"\n*** XATO: {len(missing_files)} ta kerakli fayl YO'Q ***")
    print("Yangi zip arxivini to'liq ochmagansiz, yoki eski papka bilan aralashtirib yubordingiz.")
    sys.exit(1)

# ============================================================
# 3. DATABASE TEKSHIRISH
# ============================================================
print("\n[3] DATABASE TEKSHIRISH:")
try:
    import sqlite3
    conn = sqlite3.connect("database/cyber_shats.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    needed = ['treasury_accounts', 'treasury_fund', 'coin_transfers', 'private_messages',
              'premium_ids', 'groups', 'channels', 'stories', 'reels', 'startups',
              'telegram_verifications', 'hacker_lab_security_events']
    for t in needed:
        print(f"    {'OK' if t in tables else 'YOQ'} jadval: {t}")

    print("\n[4] HISOBLAR:")
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

    conn.close()
except Exception as e:
    print(f"    XATO: {e}")

# ============================================================
# 5. FLASK ILOVASI VA ASOSIY SAHIFALAR
# ============================================================
print("\n[5] FLASK ILOVASI VA ASOSIY SAHIFALAR:")
try:
    os.environ['SECRET_KEY'] = 'test'
    import app as application
    client = application.app.test_client()
    pages_to_check = [
        ("/login", "Login"),
        ("/treasury/login", "G'azna login"),
        ("/register", "Ro'yxatdan o'tish"),
    ]
    for path, label in pages_to_check:
        r = client.get(path)
        status = "OK" if r.status_code == 200 else "XATO"
        print(f"    {status} {label} ({path}): {r.status_code}")

    # Login qilib, asosiy sahifalarni tekshirish
    client.post('/login', data={'email': 'avazbek@mixridinov', 'password': 'av050619192009az'})
    inner_pages = [
        ("/dashboard", "Bosh sahifa"),
        ("/admin", "Admin panel"),
        ("/hacker-lab", "Hacker Lab"),
        ("/startups", "Startaplar"),
        ("/groups", "Guruhlar"),
        ("/channels", "Kanallar"),
    ]
    for path, label in inner_pages:
        r = client.get(path)
        status = "OK" if r.status_code in (200, 302) else "XATO"
        print(f"    {status} {label} ({path}): {r.status_code}")

except Exception as e:
    print(f"    XATO: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("DIAGNOSTIKA TUGADI")
print("=" * 70)
if missing_packages:
    print("\n!!! AVVAL KUTUBXONALARNI O'RNATING: pip install -r requirements.txt !!!")
else:
    print("\nAGAR HAMMASI 'OK' BO'LSA — loyiha to'g'ri ishlashga tayyor.")
    print("Ishga tushirish: python app.py")
    print("Brauzerda: http://localhost:5000")
print("\nMUHIM: Brauzerda Ctrl+Shift+R bosing (kesh tozalash)")
