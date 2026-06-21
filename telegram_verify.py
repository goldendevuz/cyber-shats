"""
CYBER SHATS V1.3 — Telegram orqali majburiy ro'yxatdan o'tish tasdiqlash moduli.

Jarayon:
1. Foydalanuvchi ro'yxatdan o'tadi -> telegram_verified=0
2. Sayt 6 xonali kod yaratadi va telegram_verifications jadvaliga yozadi
3. Foydalanuvchi Telegram botga o'tib /start bosadi
4. Bot foydalanuvchidan kodni so'raydi (yoki u "/verify 123456" yuboradi)
5. Bot kodni tekshiradi -> to'g'ri bo'lsa users.telegram_verified=1, chat_id saqlanadi
6. Sayt buni avtomatik aniqlaydi (polling) va foydalanuvchini ichkariga kiritadi
"""
import random
import string
from db import query_one, query_all, execute, log_action


def generate_code() -> str:
    return "".join(random.choices(string.digits, k=6))


def create_verification(user_id: int, telegram_username: str) -> tuple[bool, str, str]:
    """Yangi tasdiqlash kodi yaratadi (10 daqiqa amal qiladi)."""
    telegram_username = (telegram_username or "").strip().lstrip("@")
    if not telegram_username:
        return False, "Telegram username kiritilishi shart.", ""
    if len(telegram_username) < 3:
        return False, "Telegram username noto'g'ri.", ""

    import datetime
    code = generate_code()
    expires_at = (datetime.datetime.now() + datetime.timedelta(minutes=10)).isoformat()

    # Eski tasdiqlanmagan kodlarni bekor qilamiz
    execute("UPDATE telegram_verifications SET is_used=1 WHERE user_id=? AND is_used=0", (user_id,))

    execute(
        "INSERT INTO telegram_verifications (user_id, code, telegram_username, expires_at) VALUES (?,?,?,?)",
        (user_id, code, telegram_username, expires_at)
    )
    execute("UPDATE users SET telegram_username=? WHERE id=?", (telegram_username, user_id))
    return True, "Tasdiqlash kodi yaratildi.", code


def get_pending_verification(user_id: int):
    return query_one(
        "SELECT * FROM telegram_verifications WHERE user_id=? AND is_used=0 ORDER BY id DESC LIMIT 1",
        (user_id,)
    )


def verify_code(telegram_username: str, code: str, chat_id: int) -> tuple[bool, str]:
    """
    Bot tomonidan chaqiriladi: foydalanuvchi botga kod yuborganda.
    Kod va username mos kelsa, foydalanuvchini tasdiqlaydi.
    """
    telegram_username = (telegram_username or "").strip().lstrip("@")
    code = (code or "").strip()

    row = query_one(
        """SELECT * FROM telegram_verifications
           WHERE code=? AND telegram_username=? AND is_used=0
           ORDER BY id DESC LIMIT 1""",
        (code, telegram_username)
    )
    if not row:
        return False, "Kod noto'g'ri yoki muddati o'tgan."

    import datetime
    try:
        expires = datetime.datetime.fromisoformat(row["expires_at"])
    except ValueError:
        expires = datetime.datetime.now()
    if datetime.datetime.now() > expires:
        return False, "Kod muddati o'tgan. Saytdan yangi kod so'rang."

    execute("UPDATE telegram_verifications SET is_used=1, verified_at=datetime('now') WHERE id=?", (row["id"],))
    execute(
        "UPDATE users SET telegram_verified=1, telegram_chat_id=? WHERE id=?",
        (chat_id, row["user_id"])
    )
    log_action(row["user_id"], "telegram_verified", details=f"username:{telegram_username}")
    return True, "Hisobingiz muvaffaqiyatli tasdiqlandi!"


def is_verified(user_id: int) -> bool:
    row = query_one("SELECT telegram_verified FROM users WHERE id=?", (user_id,))
    return bool(row and row["telegram_verified"])
