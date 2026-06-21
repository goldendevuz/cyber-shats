"""
CYBER SHATS — G'azna (Code Panel) moduli.
Bu tizim foydalanuvchilar (users) jadvalidan BUTUNLAY MUSTAQIL:
- G'azna xodimlari (treasury_accounts) o'z email+parol bilan kiradi
- G'aznaning o'z jamg'arma balansi bor (treasury_fund), 0 dan boshlanadi
- Jamg'arma faqat foydalanuvchilar sarflagan coinlardan (Pro, kurs, AI) va
  P2P o'tkazma komissiyasidan to'ladi (qarang: coins.py -> _treasury_fund_in)
- G'azna xodimi foydalanuvchilarga coin chiqarganda, bu summa jamg'armadan kamayadi.
  Agar jamg'armada yetarli mablag' bo'lmasa, chiqarib bera olmaydi.
- G'azna xodimining o'zining alohida foydalanuvchi profili yo'q, shuning uchun
  u "o'ziga-o'ziga" coin tashlay olmaydi — bu cheklov arxitektura jihatidan ta'minlangan.
"""
from werkzeug.security import generate_password_hash, check_password_hash
from db import query_one, query_all, execute


# ---------------------------------------------------------------
# G'AZNA XODIMLARI — autentifikatsiya
# ---------------------------------------------------------------

def treasury_accounts_count() -> int:
    row = query_one("SELECT COUNT(*) c FROM treasury_accounts")
    return row["c"] if row else 0


def get_treasury_account(account_id: int):
    return query_one("SELECT * FROM treasury_accounts WHERE id=?", (account_id,))


def get_treasury_account_by_email(email: str):
    return query_one("SELECT * FROM treasury_accounts WHERE email=?", (email.strip().lower(),))


def create_treasury_account(ism: str, email: str, password: str) -> tuple[bool, str]:
    ism = (ism or "").strip()
    email = (email or "").strip().lower()
    if not ism or not email or not password:
        return False, "Barcha maydonlarni to'ldiring."
    if len(password) < 6:
        return False, "Parol kamida 6 ta belgidan iborat bo'lishi kerak."
    existing = get_treasury_account_by_email(email)
    if existing:
        return False, "Bu email bilan G'azna hisobi allaqachon mavjud."
    execute(
        "INSERT INTO treasury_accounts (ism, email, password_hash) VALUES (?,?,?)",
        (ism, email, generate_password_hash(password))
    )
    return True, "G'azna hisobi yaratildi."


def verify_treasury_login(email: str, password: str):
    """To'g'ri bo'lsa hisob (dict) qaytaradi, aks holda None."""
    account = get_treasury_account_by_email(email)
    if not account or not account.get("is_active"):
        return None
    if not check_password_hash(account["password_hash"], password or ""):
        return None
    execute("UPDATE treasury_accounts SET last_login_at=datetime('now') WHERE id=?", (account["id"],))
    return account


def list_treasury_accounts():
    return query_all(
        "SELECT id, ism, email, is_active, created_at, last_login_at FROM treasury_accounts ORDER BY created_at ASC"
    )


def toggle_treasury_account(account_id: int):
    acc = get_treasury_account(account_id)
    if acc:
        execute("UPDATE treasury_accounts SET is_active=? WHERE id=?", (0 if acc["is_active"] else 1, account_id))


def reset_treasury_account_password(account_id: int, new_password: str) -> tuple[bool, str]:
    if len(new_password or "") < 6:
        return False, "Parol kamida 6 ta belgidan iborat bo'lishi kerak."
    execute("UPDATE treasury_accounts SET password_hash=? WHERE id=?",
            (generate_password_hash(new_password), account_id))
    return True, "Parol yangilandi."


# ---------------------------------------------------------------
# JAMG'ARMA — balans va kirim-chiqim
# ---------------------------------------------------------------

def get_fund_balance() -> int:
    row = query_one("SELECT balance FROM treasury_fund WHERE id=1")
    return row["balance"] if row else 0


def admin_deposit_to_fund(admin_user_id: int, amount: int, note: str = "") -> tuple[bool, str]:
    """Admin tomonidan g'aznaga to'g'ridan-to'g'ri code solib berish.
    Bu funksiya admin paneldan chaqiriladi — admin g'aznaga 'sovg'a' tarzida code qo'sha oladi.
    Log'da reason='admin_deposit' va user_id=admin_user_id deb yoziladi (chiqaruvchi sifatida)."""
    if amount <= 0:
        return False, "Miqdor musbat bo'lishi kerak."
    execute("UPDATE treasury_fund SET balance = balance + ?, updated_at = datetime('now') WHERE id=1", (amount,))
    reason = "admin_deposit"
    if note:
        reason = f"admin_deposit:{note[:50]}"
    execute(
        "INSERT INTO treasury_fund_log (direction, amount, reason, user_id) VALUES ('in', ?, ?, ?)",
        (amount, reason, admin_user_id)
    )
    return True, f"{amount:,} CODE g'azna jamg'armasiga qo'shildi."


def add_id_auction_revenue(amount: int, buyer_user_id: int, premium_id_str: str) -> None:
    """ID auksion sotuvi/sotib olish daromadini g'aznaga qo'shadi.
    Bu coins.py va ids.py'dan chaqiriladi har bir premium ID sotilishida."""
    if amount <= 0:
        return
    execute("UPDATE treasury_fund SET balance = balance + ?, updated_at = datetime('now') WHERE id=1", (amount,))
    execute(
        "INSERT INTO treasury_fund_log (direction, amount, reason, user_id) VALUES ('in', ?, ?, ?)",
        (amount, f"id_sale:{premium_id_str}", buyer_user_id)
    )


def issue_coins_to_user(treasury_account_id: int, user_id: int, amount: int) -> tuple[bool, str]:
    """
    G'azna jamg'armasidan foydalanuvchiga coin chiqaradi.
    Jamg'armada yetarli mablag' bo'lmasa rad etiladi.
    G'azna xodimining o'zi uchun alohida foydalanuvchi profili yo'qligi sababli
    "o'ziga-o'ziga tashlash" arxitektura jihatidan mumkin emas.
    """
    if amount <= 0:
        return False, "Miqdor musbat bo'lishi kerak."
    user = query_one("SELECT id, is_blocked FROM users WHERE id=?", (user_id,))
    if not user:
        return False, "Foydalanuvchi topilmadi."
    if user.get("is_blocked"):
        return False, "Bloklangan foydalanuvchiga coin chiqarib bo'lmaydi."

    balance = get_fund_balance()
    if balance < amount:
        return False, f"Jamg'armada yetarli mablag' yo'q. Kerak: {amount:,}, jamg'armada: {balance:,}."

    execute("UPDATE treasury_fund SET balance = balance - ?, updated_at = datetime('now') WHERE id=1", (amount,))
    execute(
        "INSERT INTO treasury_fund_log (direction, amount, reason, user_id, treasury_account_id) "
        "VALUES ('out', ?, 'issue_to_user', ?, ?)",
        (amount, user_id, treasury_account_id)
    )

    from coins import add_coins
    add_coins(user_id, amount, "treasury_issue", ref_id=treasury_account_id)

    execute(
        "INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
        (user_id, "CODE qo'shildi!", f"G'aznadan {amount:,} CODE hisobingizga qo'shildi.", "success")
    )
    try:
        import webpush_mod
        webpush_mod.send_push_to_user(
            user_id, "CODE qo'shildi! ⚡",
            f"G'aznadan {amount:,} CODE hisobingizga qo'shildi.", "/coins"
        )
    except Exception:
        pass

    return True, f"{amount:,} CODE foydalanuvchiga jamg'armadan chiqarildi."


def get_fund_log(limit: int = 60):
    return query_all(
        """SELECT l.*, u.ism as user_ism, u.familiya as user_familiya,
                  ta.ism as treasury_ism
           FROM treasury_fund_log l
           LEFT JOIN users u ON u.id = l.user_id
           LEFT JOIN treasury_accounts ta ON ta.id = l.treasury_account_id
           ORDER BY l.id DESC LIMIT ?""",
        (limit,)
    )


def get_fund_stats() -> dict:
    total_in = query_one("SELECT COALESCE(SUM(amount),0) s FROM treasury_fund_log WHERE direction='in'")["s"]
    total_out = query_one("SELECT COALESCE(SUM(amount),0) s FROM treasury_fund_log WHERE direction='out'")["s"]
    # reason'lar oldi qismi bo'yicha guruhlash (id_sale:1234 -> id_sale, admin_deposit:note -> admin_deposit)
    in_by_reason = query_all(
        """SELECT CASE
                    WHEN reason LIKE 'id_sale:%' THEN 'id_sale'
                    WHEN reason LIKE 'admin_deposit:%' THEN 'admin_deposit'
                    ELSE reason
                  END as reason,
                  COALESCE(SUM(amount),0) total
           FROM treasury_fund_log
           WHERE direction='in'
           GROUP BY 1
           ORDER BY total DESC"""
    )
    return {
        "balance": get_fund_balance(),
        "total_in": total_in,
        "total_out": total_out,
        "in_by_reason": in_by_reason,
    }
