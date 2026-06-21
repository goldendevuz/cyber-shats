"""
CYBER SHATS — Admin boshqaruvi moduli
- Har bir admin/mentor/super_admin uchun 4 xonali unikal admin_id
- admin_id ni FAQAT super_admin o'zgartira oladi
- Yangi admin: parol bilan yangi foydalanuvchi YOKI mavjud foydalanuvchini admin qilish
"""
import random
from werkzeug.security import generate_password_hash
from db import query_one, query_all, execute


def generate_admin_id() -> str:
    """4 xonali (1000-9999) unikal admin ID yaratadi."""
    for _ in range(500):
        cid = str(random.randint(1000, 9999))
        exists = query_one("SELECT id FROM users WHERE admin_id=?", (cid,))
        if not exists:
            return cid
    raise RuntimeError("Bo'sh admin_id topilmadi (4 xonali kombinatsiyalar tugagan)")


def get_all_admins():
    """Barcha admin/mentor/super_admin foydalanuvchilarni qaytaradi."""
    return query_all(
        "SELECT id, ism, familiya, email, role, admin_id, is_blocked, created_at "
        "FROM users WHERE role IN ('admin','mentor','super_admin') ORDER BY role='super_admin' DESC, created_at ASC"
    )


def create_new_admin(ism: str, familiya: str, email: str, password: str, role: str = "admin") -> tuple[bool, str]:
    """Yangi login/parol bilan admin foydalanuvchi yaratadi va unga 4 xonali admin_id beradi."""
    ism = (ism or "").strip()
    email = (email or "").strip().lower()
    if not ism or not email or not password:
        return False, "Ism, email va parol majburiy."
    if len(password) < 6:
        return False, "Parol kamida 6 belgidan iborat bo'lishi kerak."
    if role not in ("admin", "mentor", "super_admin"):
        return False, "Noto'g'ri rol."
    existing = query_one("SELECT id FROM users WHERE email=?", (email,))
    if existing:
        return False, "Bu email allaqachon ro'yxatdan o'tgan."

    from ids import generate_unique_id
    custom_id = generate_unique_id()
    admin_id = generate_admin_id()
    pw_hash = generate_password_hash(password)

    execute(
        """INSERT INTO users (ism, familiya, email, password_hash, role, custom_id, admin_id, plan)
           VALUES (?,?,?,?,?,?,?,'enterprise')""",
        (ism, familiya or "", email, pw_hash, role, custom_id, admin_id)
    )
    return True, f"Yangi admin yaratildi. Admin ID: #{admin_id}"


def promote_user_to_admin(user_id: int, role: str = "admin") -> tuple[bool, str]:
    """Mavjud foydalanuvchini admin/mentor qilib tayinlaydi va 4 xonali admin_id beradi."""
    if role not in ("admin", "mentor", "super_admin"):
        return False, "Noto'g'ri rol."
    user = query_one("SELECT * FROM users WHERE id=?", (user_id,))
    if not user:
        return False, "Foydalanuvchi topilmadi."
    if user["role"] in ("admin", "mentor", "super_admin"):
        return False, "Bu foydalanuvchi allaqachon administrator."
    admin_id = user.get("admin_id") or generate_admin_id()
    execute("UPDATE users SET role=?, admin_id=? WHERE id=?", (role, admin_id, user_id))
    return True, f"{user['ism']} endi {role}. Admin ID: #{admin_id}"


def demote_admin(user_id: int) -> tuple[bool, str]:
    """Adminlik huquqini olib tashlaydi (student qilib qaytaradi). admin_id saqlanib qoladi."""
    user = query_one("SELECT * FROM users WHERE id=?", (user_id,))
    if not user:
        return False, "Foydalanuvchi topilmadi."
    if user["role"] == "super_admin":
        return False, "Super adminni shu yo'l bilan tushirib bo'lmaydi."
    execute("UPDATE users SET role='student' WHERE id=?", (user_id,))
    return True, f"{user['ism']} endi oddiy foydalanuvchi (admin huquqlari olib tashlandi)."


def super_admin_change_admin_id(user_id: int, new_admin_id: str) -> tuple[bool, str]:
    """FAQAT super_admin chaqirishi mumkin (route darajasida tekshiriladi).
    Boshqa adminning 4 xonali ID raqamini o'zgartiradi."""
    new_admin_id = (new_admin_id or "").strip()
    if len(new_admin_id) != 4 or not new_admin_id.isdigit():
        return False, "Admin ID aniq 4 ta raqamdan iborat bo'lishi kerak."
    user = query_one("SELECT * FROM users WHERE id=?", (user_id,))
    if not user:
        return False, "Foydalanuvchi topilmadi."
    if user["role"] not in ("admin", "mentor", "super_admin"):
        return False, "Bu foydalanuvchi administrator emas."
    clash = query_one("SELECT id FROM users WHERE admin_id=? AND id!=?", (new_admin_id, user_id))
    if clash:
        return False, "Bu Admin ID allaqachon band."
    execute("UPDATE users SET admin_id=? WHERE id=?", (new_admin_id, user_id))
    return True, f"Admin ID #{new_admin_id} ga o'zgartirildi."
