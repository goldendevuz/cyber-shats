"""
CYBER SHATS — Code tangalari (coin) moduli
Barcha tangalar bilan bog'liq amallar shu yerda.

Foydalanuvchi sarflagan har bir coin (Pro sotib olish, kurs sotib olish,
AI ishlatish) va har bir P2P o'tkazma komissiyasi G'AZNA JAMG'ARMASIGA tushadi
(treasury_fund). G'azna shu jamg'armadan foydalanuvchilarga coin chiqaradi —
agar jamg'armada yetarli mablag' bo'lmasa, chiqarib bera olmaydi.
"""
from db import query_one, execute, log_action
from config import Config
from pricing import get_price


def get_balance(user_id: int) -> int:
    row = query_one("SELECT code_balance FROM users WHERE id=?", (user_id,))
    return (row["code_balance"] or 0) if row else 0


def add_coins(user_id: int, amount: int, reason: str, ref_id=None):
    """Foydalanuvchiga code tangasi qo'shadi (G'aznadan mustaqil — masalan kurs mukofoti, bonus)."""
    execute("UPDATE users SET code_balance = code_balance + ? WHERE id=?", (amount, user_id))
    execute("INSERT INTO code_transactions (user_id, amount, reason, ref_id) VALUES (?,?,?,?)",
            (user_id, amount, reason, ref_id))


def spend_coins(user_id: int, amount: int, reason: str, ref_id=None) -> tuple[bool, str]:
    """Tangalarni sarflaydi. Returns: (success, message)"""
    balance = get_balance(user_id)
    if balance < amount:
        return False, f"Yetarli code tangasi yo'q. Kerak: {amount:,}, mavjud: {balance:,}"
    execute("UPDATE users SET code_balance = code_balance - ? WHERE id=?", (amount, user_id))
    execute("INSERT INTO code_transactions (user_id, amount, reason, ref_id) VALUES (?,?,?,?)",
            (user_id, -amount, reason, ref_id))
    return True, "OK"


def _treasury_fund_in(amount: int, reason: str, user_id: int = None):
    """Jamg'armaga kirim qo'shadi (foydalanuvchi sarfi yoki komissiya)."""
    if amount <= 0:
        return
    execute("UPDATE treasury_fund SET balance = balance + ?, updated_at = datetime('now') WHERE id=1", (amount,))
    execute(
        "INSERT INTO treasury_fund_log (direction, amount, reason, user_id) VALUES ('in', ?, ?, ?)",
        (amount, reason, user_id)
    )


def award_course_completion(user_id: int, course_id: int):
    """Kurs bitirilganda mukofot beradi (bir marta).
    Oddiy foydalanuvchi: 100 code (course_reward_code)
    Cyber Pro foydalanuvchi: + qo'shimcha 1000 code (cyber_pro_course_bonus)
    VIP foydalanuvchi: + qo'shimcha 2000 code (vip_course_bonus)"""
    existing = query_one(
        "SELECT id FROM code_transactions WHERE user_id=? AND reason='course_complete' AND ref_id=?",
        (user_id, course_id)
    )
    if existing:
        return  # Allaqachon berilgan
    add_coins(user_id, get_price("course_reward_code"), "course_complete", course_id)
    # Cyber Pro / VIP qo'shimcha bonus
    user = query_one("SELECT plan FROM users WHERE id=?", (user_id,))
    if user and user.get("plan") == "cyber_pro":
        bonus = get_price("cyber_pro_course_bonus")
        if bonus > 0:
            add_coins(user_id, bonus, "cyber_pro_course_bonus", course_id)
    elif user and user.get("plan") == "vip":
        bonus = get_price("vip_course_bonus")
        if bonus > 0:
            add_coins(user_id, bonus, "vip_course_bonus", course_id)
    # Reyting yangilash
    _update_rating(user_id)


def buy_pro_with_coins(user_id: int) -> tuple[bool, str]:
    """Pro versiya sotib olish (narx bazadan, admin tomonidan o'zgartiriladi).
    Sarflangan coin G'azna jamg'armasiga tushadi. 1 oy amal qiladi."""
    user = query_one("SELECT * FROM users WHERE id=?", (user_id,))
    if user and user.get("plan") in ("pro", "cyber_pro", "vip"):
        return False, "Siz allaqachon Pro yoki yuqori versiya foydalanuvchisiz."
    cost = get_price("pro_price_code")
    ok, msg = spend_coins(user_id, cost, "buy_pro")
    if not ok:
        return False, msg
    expires_at = _calc_plan_expiry()
    execute("UPDATE users SET plan='pro', plan_expires_at=? WHERE id=?", (expires_at, user_id))
    execute("INSERT INTO pro_payments (user_id, method, amount_code, status) VALUES (?,?,?,?)",
            (user_id, "code", cost, "success"))
    log_action(user_id, "buy_pro_code", details=f"cost:{cost},expires:{expires_at}")
    _treasury_fund_in(cost, "buy_pro", user_id)
    return True, f"Pro versiya faollashtirildi! 1 oy amal qiladi ({expires_at[:10]} gacha). Tabriklaymiz!"


def buy_cyber_pro_with_coins(user_id: int) -> tuple[bool, str]:
    """Cyber Pro versiyasi — Pro'dan kuchliroq. Ingliz tili, matematika, Office yo'nalishlari ochiladi.
    Komissiyasiz P2P, 10,000 welcome bonus, har kurs bitirishda 1,000 code bonus. 1 oy amal qiladi."""
    user = query_one("SELECT * FROM users WHERE id=?", (user_id,))
    if user and user.get("plan") in ("cyber_pro", "vip"):
        return False, "Siz allaqachon Cyber Pro yoki yuqori versiya foydalanuvchisiz."
    cost = get_price("cyber_pro_price_code")
    ok, msg = spend_coins(user_id, cost, "buy_cyber_pro")
    if not ok:
        return False, msg
    expires_at = _calc_plan_expiry()
    execute("UPDATE users SET plan='cyber_pro', plan_expires_at=? WHERE id=?", (expires_at, user_id))
    execute("INSERT INTO pro_payments (user_id, method, amount_code, status) VALUES (?,?,?,?)",
            (user_id, "code", cost, "success"))
    log_action(user_id, "buy_cyber_pro_code", details=f"cost:{cost},expires:{expires_at}")
    _treasury_fund_in(cost, "buy_cyber_pro", user_id)
    # 10,000 welcome bonus
    welcome = get_price("cyber_pro_welcome_bonus")
    if welcome > 0:
        add_coins(user_id, welcome, "cyber_pro_welcome_bonus")
    return True, f"Cyber Pro faollashtirildi! 1 oy amal qiladi ({expires_at[:10]} gacha). +{welcome:,} CODE bonus berildi!"


def buy_vip_with_coins(user_id: int) -> tuple[bool, str]:
    """SHATS CYBER PRO — eng kuchli versiya. Pro va Cyber Pro'dagi hamma narsa + ko'proq bonus.
    Tilla-rang dizayn. 1 oy amal qiladi. Admin yoqib/o'chirib qo'yishi mumkin."""
    if get_price("vip_enabled") != 1 and get_price("vip_enabled") != "1":
        return False, "SHATS CYBER PRO versiya hozircha vaqtincha o'chirilgan."
    user = query_one("SELECT * FROM users WHERE id=?", (user_id,))
    if user and user.get("plan") == "vip":
        return False, "Siz allaqachon SHATS CYBER PRO foydalanuvchisiz."
    cost = get_price("vip_price_code")
    ok, msg = spend_coins(user_id, cost, "buy_vip")
    if not ok:
        return False, msg
    expires_at = _calc_plan_expiry()
    execute("UPDATE users SET plan='vip', plan_expires_at=? WHERE id=?", (expires_at, user_id))
    execute("INSERT INTO pro_payments (user_id, method, amount_code, status) VALUES (?,?,?,?)",
            (user_id, "code", cost, "success"))
    log_action(user_id, "buy_vip_code", details=f"cost:{cost},expires:{expires_at}")
    _treasury_fund_in(cost, "buy_vip", user_id)
    welcome = get_price("vip_welcome_bonus")
    if welcome > 0:
        add_coins(user_id, welcome, "vip_welcome_bonus")
    return True, f"🔥 SHATS CYBER PRO faollashtirildi! 1 oy amal qiladi ({expires_at[:10]} gacha). +{welcome:,} CODE bonus!"


def _calc_plan_expiry() -> str:
    """Joriy vaqtdan plan_duration_days kun keyingi sana (ISO format)."""
    import datetime
    days = get_price("plan_duration_days")
    try:
        days = int(days)
    except (ValueError, TypeError):
        days = 30
    return (datetime.datetime.now() + datetime.timedelta(days=days)).isoformat()


def check_and_downgrade_expired_plan(user_id: int) -> bool:
    """
    Foydalanuvchining Pro/Cyber Pro/VIP muddati tugaganmi tekshiradi.
    Tugagan bo'lsa avtomatik 'free'ga tushiradi. True qaytaradi agar tushirilgan bo'lsa.
    Bu funksiya har bir muhim sahifa ochilganda chaqiriladi (fon jarayoni shart emas).
    """
    import datetime
    user = query_one("SELECT plan, plan_expires_at FROM users WHERE id=?", (user_id,))
    if not user or user["plan"] not in ("pro", "cyber_pro", "vip"):
        return False
    if not user["plan_expires_at"]:
        return False
    try:
        expires = datetime.datetime.fromisoformat(user["plan_expires_at"])
    except ValueError:
        return False
    if datetime.datetime.now() < expires:
        return False

    # Muddati tugagan — free'ga tushiramiz
    old_plan = user["plan"]
    execute("UPDATE users SET plan='free', plan_expires_at=NULL WHERE id=?", (user_id,))
    execute(
        "INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
        (user_id, "Obuna muddati tugadi",
         f"{old_plan.upper()} obunangiz muddati tugadi va FREE rejaga o'tkazildingiz. "
         f"Qayta faollashtirish uchun yangi to'lov qiling.", "info")
    )
    try:
        import webpush_mod
        webpush_mod.send_push_to_user(
            user_id, "Obuna muddati tugadi",
            f"{old_plan.upper()} obunangiz tugadi. Qayta faollashtiring.", "/pricing"
        )
    except Exception:
        pass
    log_action(user_id, "plan_auto_downgraded", details=f"from:{old_plan}")
    return True


def buy_course_with_coins(user_id: int, course_id: int) -> tuple[bool, str]:
    """Pulik kursni code tangasiga sotib olish. Sarflangan coin G'azna jamg'armasiga tushadi."""
    course = query_one("SELECT * FROM courses WHERE id=?", (course_id,))
    if not course:
        return False, "Kurs topilmadi."
    cost = course.get("code_price") or get_price("paid_course_code_default")
    if cost == 0:
        return True, "Bepul kurs"
    existing = query_one("SELECT id FROM enrollments WHERE user_id=? AND course_id=?", (user_id, course_id))
    if existing:
        return False, "Siz bu kursga allaqachon yozilgansiz."
    ok, msg = spend_coins(user_id, cost, "buy_course", course_id)
    if not ok:
        return False, msg
    execute("INSERT OR IGNORE INTO enrollments (user_id, course_id, progress_percent) VALUES (?,?,0)",
            (user_id, course_id))
    log_action(user_id, "buy_course_code", details=f"course:{course_id},cost:{cost}")
    _treasury_fund_in(cost, "buy_course", user_id)
    return True, f"Kursga muvaffaqiyatli yozildingiz! ({cost:,} code sarflandi)"


def deduct_ai_usage(user_id: int) -> tuple[bool, str]:
    """AI javob uchun code tangasi ayiradi. Sarflangan coin G'azna jamg'armasiga tushadi."""
    user = query_one("SELECT plan, code_balance FROM users WHERE id=?", (user_id,))
    if not user:
        return False, "Foydalanuvchi topilmadi."
    # Pro, Cyber Pro va VIP foydalanuvchilar AI dan cheksiz foydalanadi
    if user.get("plan") in ("pro", "cyber_pro", "vip"):
        return True, "pro"
    cost = get_price("ai_cost_per_msg")
    ok, msg = spend_coins(user_id, cost, "ai_usage")
    if ok:
        _treasury_fund_in(cost, "ai_usage", user_id)
    return ok, msg


def transfer_coins(from_user_id: int, to_user_id: int, amount: int) -> tuple[bool, str]:
    """
    Foydalanuvchidan-foydalanuvchiga code tangasi o'tkazadi.
    Oddiy (free) foydalanuvchidan har bir o'tkazmadan komissiya olinadi
    (pricing_settings.coin_transfer_fee_percent, default 5%).
    Pro foydalanuvchi uchun komissiya 0%.
    Komissiya G'azna jamg'armasiga tushadi.
    """
    if amount <= 0:
        return False, "Miqdor musbat bo'lishi kerak."
    if from_user_id == to_user_id:
        return False, "O'zingizga tanga o'tkaza olmaysiz."

    sender = query_one("SELECT id, plan, code_balance FROM users WHERE id=?", (from_user_id,))
    receiver = query_one("SELECT id, is_blocked FROM users WHERE id=?", (to_user_id,))
    if not sender:
        return False, "Jo'natuvchi topilmadi."
    if not receiver:
        return False, "Qabul qiluvchi foydalanuvchi topilmadi."
    if receiver.get("is_blocked"):
        return False, "Bu foydalanuvchi bloklangan, tanga o'tkazib bo'lmaydi."

    is_pro = sender.get("plan") in ("pro", "cyber_pro", "vip", "enterprise")
    fee_percent = 0 if is_pro else get_price("coin_transfer_fee_percent")
    fee_amount = (amount * fee_percent) // 100
    total_cost = amount + fee_amount

    balance = sender.get("code_balance") or 0
    if balance < total_cost:
        return False, (
            f"Yetarli code tangasi yo'q. Kerak: {total_cost:,} "
            f"(o'tkazma {amount:,} + komissiya {fee_amount:,}), mavjud: {balance:,}"
        )

    ok, msg = spend_coins(from_user_id, total_cost, "transfer_out", ref_id=to_user_id)
    if not ok:
        return False, msg
    add_coins(to_user_id, amount, "transfer_in", ref_id=from_user_id)

    execute(
        """INSERT INTO coin_transfers (from_user_id, to_user_id, amount_sent, fee_amount, amount_received)
           VALUES (?,?,?,?,?)""",
        (from_user_id, to_user_id, total_cost, fee_amount, amount)
    )
    log_action(from_user_id, "coin_transfer", details=f"to:{to_user_id},amount:{amount},fee:{fee_amount}")

    if fee_amount > 0:
        _treasury_fund_in(fee_amount, "transfer_fee", from_user_id)
        return True, f"{amount:,} CODE jo'natildi (komissiya: {fee_amount:,} CODE)."
    return True, f"{amount:,} CODE jo'natildi (Pro: komissiyasiz)."


def get_transactions(user_id: int, limit: int = 20):
    return __import__('db').query_all(
        "SELECT * FROM code_transactions WHERE user_id=? ORDER BY id DESC LIMIT ?",
        (user_id, limit)
    )


def get_leaderboard(limit: int = 20):
    """Faqat student va pro foydalanuvchilarni qaytaradi (admin/mentor chiqarilmaydi)."""
    return __import__('db').query_all(
        """SELECT u.id, u.ism, u.familiya, u.avatar, u.level, u.plan,
                  u.code_balance,
                  COALESCE(ur.total_score,0) as total_score,
                  COALESCE(ur.courses_done,0) as courses_done,
                  COALESCE(ur.rank_position,0) as rank_position
           FROM users u LEFT JOIN user_ratings ur ON ur.user_id=u.id
           WHERE u.is_blocked=0 AND u.role NOT IN ('admin','mentor')
           ORDER BY COALESCE(ur.total_score,0) DESC, u.xp DESC
           LIMIT ?""",
        (limit,)
    )


def _update_rating(user_id: int):
    from db import query_all
    courses_done = query_one(
        "SELECT COUNT(*) c FROM enrollments WHERE user_id=? AND progress_percent=100", (user_id,)
    )["c"]
    tests_passed = query_one(
        "SELECT COUNT(*) c FROM test_attempts WHERE user_id=? AND score * 100.0 / NULLIF(total,0) >= 60",
        (user_id,)
    )["c"]
    user = query_one("SELECT xp, code_balance FROM users WHERE id=?", (user_id,))
    total = (user["xp"] or 0) + (courses_done * 500) + (tests_passed * 100)
    execute(
        """INSERT INTO user_ratings (user_id, total_score, courses_done, tests_passed, updated_at)
           VALUES (?,?,?,?, datetime('now'))
           ON CONFLICT(user_id) DO UPDATE SET
               total_score=excluded.total_score,
               courses_done=excluded.courses_done,
               tests_passed=excluded.tests_passed,
               updated_at=excluded.updated_at""",
        (user_id, total, courses_done, tests_passed)
    )
    # Pozitsiyalarni yangilash
    execute("""
        UPDATE user_ratings SET rank_position = (
            SELECT COUNT(*) + 1 FROM user_ratings r2
            WHERE r2.total_score > user_ratings.total_score
        )
    """)
