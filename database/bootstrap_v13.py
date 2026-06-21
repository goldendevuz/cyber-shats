"""
CYBER SHATS V1.3 — Bootstrap skripti.

Bu skript quyidagilarni yaratadi/yangilaydi:
1. Admin hisobi: avazbek@mixridinov / av050619192009az (super_admin)
2. G'aznachi hisobi: kassa@shats / sha9999ts
3. 137 ta soxta foydalanuvchi har xil darajada (8-15 oralig'ida), barchasi free
   Har biriga 7000 code welcome bonus avtomatik berildi

Ishga tushirish: python database/bootstrap_v13.py
"""
import sqlite3, os, random, string
from werkzeug.security import generate_password_hash

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyber_shats.db")

UZBEK_FIRST_NAMES = [
    "Aziz", "Bekzod", "Davron", "Elyor", "Farrux", "G'olib", "Husan", "Ilxom",
    "Jamshid", "Kamol", "Laziz", "Murod", "Nodir", "Otabek", "Pulat", "Qodir",
    "Rustam", "Sardor", "Toshpo'lat", "Ulug'bek", "Vali", "Xurshid", "Yusuf", "Zafar",
    "Akmal", "Bahodir", "Doniyor", "Eldor", "Fazliddin", "G'ofur", "Hasan", "Islom",
    "Jasur", "Karim", "Lutfullo", "Mansur", "Nuriddin", "Oybek", "Polat", "Ravshan",
    "Shavkat", "Temur", "Umid", "Valijon", "Xolmurod", "Yodgor", "Zohid", "Anvar",
    "Botir", "Diyor", "Erkin", "Faxriddin", "G'ayrat", "Hamza", "Iskandar",
    "Munisa", "Sevinch", "Nilufar", "Dilnoza", "Madina", "Shaxnoza", "Zarina",
    "Gulnoza", "Marjona", "Sabina", "Diyora", "Iroda", "Kamola", "Layla",
    "Mohinur", "Nodira", "Odina", "Parvina", "Robiya", "Sitora", "Tursunoy",
    "Umida", "Vazira", "Xolida", "Yulduz", "Zilola"
]

UZBEK_LAST_NAMES = [
    "Ahmedov", "Boboyev", "Choriyev", "Davlatov", "Ergashev", "Fayzullayev",
    "G'aniyev", "Hoshimov", "Islomov", "Jo'rayev", "Karimov", "Lutfullayev",
    "Mamatov", "Niyozov", "Otaboyev", "Pulatov", "Qodirov", "Rustamov",
    "Sobirov", "Tursunov", "Umarov", "Vohidov", "Xolmatov", "Yuldashev",
    "Zaripov", "Abdullayev", "Bobomurodov", "Chiniev", "Dadayev", "Eshqulov",
    "Fattoyev", "G'ulomov", "Hayitov", "Ibragimov", "Jalilov", "Komilov",
    "Latipov", "Mirzoyev", "Nurmatov", "Olimjonov", "Po'latov", "Qurbanov",
    "Raximov", "Saidov", "Tojiev", "Usmonov", "Valiyev", "Xamidov",
    "Yusupov", "Zoirov"
]


def random_user_id(used):
    while True:
        uid = ''.join(random.choices('0123456789', k=7))
        if uid[0] != '0' and uid not in used:
            used.add(uid)
            return uid


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # ---------- 1) Admin hisobi ----------
    admin_email = "avazbek@mixridinov"
    admin_password = "av050619192009az"
    existing = c.execute("SELECT id FROM users WHERE email=?", (admin_email,)).fetchone()
    admin_pw_hash = generate_password_hash(admin_password)
    if existing:
        c.execute("UPDATE users SET password_hash=?, role='super_admin', is_blocked=0 WHERE id=?",
                  (admin_pw_hash, existing["id"]))
        print(f"  ~ Admin hisobi yangilandi (id={existing['id']})")
    else:
        c.execute(
            "INSERT INTO users (ism, familiya, email, password_hash, role, admin_id, code_balance) VALUES (?,?,?,?,?,?,?)",
            ("Avazbek", "Mixridinov", admin_email, admin_pw_hash, "super_admin", "0001", 0)
        )
        admin_id = c.lastrowid
        used_ids = set(r["custom_id"] for r in c.execute("SELECT custom_id FROM users WHERE custom_id IS NOT NULL"))
        cid = random_user_id(used_ids)
        c.execute("UPDATE users SET custom_id=? WHERE id=?", (cid, admin_id))
        print(f"  + Admin hisobi yaratildi: {admin_email} (id={admin_id}, custom_id=#{cid})")

    # ---------- 2) G'aznachi hisobi ----------
    treasury_email = "kassa@shats"
    treasury_password = "sha9999ts"
    existing_t = c.execute("SELECT id FROM treasury_accounts WHERE email=?", (treasury_email,)).fetchone()
    tr_pw_hash = generate_password_hash(treasury_password)
    if existing_t:
        c.execute("UPDATE treasury_accounts SET password_hash=?, is_active=1 WHERE id=?",
                  (tr_pw_hash, existing_t["id"]))
        print(f"  ~ G'aznachi hisobi yangilandi (id={existing_t['id']})")
    else:
        c.execute(
            "INSERT INTO treasury_accounts (ism, email, password_hash, is_active) VALUES (?,?,?,1)",
            ("Bosh G'aznachi", treasury_email, tr_pw_hash)
        )
        print(f"  + G'aznachi hisobi yaratildi: {treasury_email}")

    conn.commit()
    conn.close()
    print("\n✓ Bootstrap V1.3 yakunlandi!")
    print(f"\n  Admin login:    {admin_email} / {admin_password}")
    print(f"  G'aznachi login: {treasury_email} / {treasury_password}  →  /treasury/login")
    print("\n  Eslatma: Soxta/demo foydalanuvchilar endi yaratilmaydi.")
    print("  Faqat real ro'yxatdan o'tgan foydalanuvchilar tizimda bo'ladi.")


if __name__ == "__main__":
    main()
