"""
CYBER SHATS — Code tangalari (coin) moduli
Barcha tangalar bilan bog'liq amallar shu yerda.
"""
from db import query_one, execute, log_action
from config import Config


def get_balance(user_id: int) -> int:
    row = query_one("SELECT code_balance FROM users WHERE id=?", (user_id,))
    return (row["code_balance"] or 0) if row else 0


def add_coins(user_id: int, amount: int, reason: str, ref_id=None):
    """Foydalanuvchiga code tangasi qo'shadi."""
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


def award_course_completion(user_id: int, course_id: int):
    """Kurs bitirilganda 100 code tangasi beradi (bir marta)."""
    existing = query_one(
        "SELECT id FROM code_transactions WHERE user_id=? AND reason='course_complete' AND ref_id=?",
        (user_id, course_id)
    )
    if existing:
        return  # Allaqachon berilgan
    add_coins(user_id, Config.COURSE_REWARD_CODE, "course_complete", course_id)
    # Reyting yangilash
    _update_rating(user_id)


def buy_pro_with_coins(user_id: int) -> tuple[bool, str]:
    """57,000 code tangasi evaziga Pro versiya sotib olish."""
    user = query_one("SELECT * FROM users WHERE id=?", (user_id,))
    if user and user.get("plan") == "pro":
        return False, "Siz allaqachon Pro foydalanuvchisiz."
    ok, msg = spend_coins(user_id, Config.PRO_COST_CODE, "buy_pro")
    if not ok:
        return False, msg
    execute("UPDATE users SET plan='pro' WHERE id=?", (user_id,))
    execute("INSERT INTO pro_payments (user_id, method, amount_code, status) VALUES (?,?,?,?)",
            (user_id, "code", Config.PRO_COST_CODE, "success"))
    log_action(user_id, "buy_pro_code", details=f"cost:{Config.PRO_COST_CODE}")
    return True, "Pro versiya faollashtirildi! Tabriklaymiz!"


def buy_course_with_coins(user_id: int, course_id: int) -> tuple[bool, str]:
    """Pulik kursni code tangasiga sotib olish (10,000 code)."""
    course = query_one("SELECT * FROM courses WHERE id=?", (course_id,))
    if not course:
        return False, "Kurs topilmadi."
    cost = course.get("code_price") or Config.PAID_COURSE_CODE
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
    return True, f"Kursga muvaffaqiyatli yozildingiz! ({cost:,} code sarflandi)"


def deduct_ai_usage(user_id: int) -> tuple[bool, str]:
    """AI javob uchun 200 code tangasi ayiradi."""
    user = query_one("SELECT plan, code_balance FROM users WHERE id=?", (user_id,))
    if not user:
        return False, "Foydalanuvchi topilmadi."
    # Pro foydalanuvchilar AI dan cheksiz foydalanadi
    if user.get("plan") == "pro":
        return True, "pro"
    return spend_coins(user_id, Config.AI_COST_PER_MSG, "ai_usage")


def get_transactions(user_id: int, limit: int = 20):
    return query_one.__module__ and __import__('db').query_all(
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
