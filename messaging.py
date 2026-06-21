"""
CYBER SHATS — Shaxsiy xabarlashuv (Telegram uslubidagi foydalanuvchidan-foydalanuvchiga chat) moduli.
"""
from db import query_one, query_all, execute


def get_conversations(user_id: int):
    """
    Foydalanuvchining barcha suhbatlari ro'yxati: har bir suhbatdosh uchun
    oxirgi xabar va o'qilmagan xabarlar soni bilan.
    """
    return query_all(
        """
        WITH pairs AS (
            SELECT CASE WHEN sender_id = ? THEN receiver_id ELSE sender_id END AS peer_id,
                   id, body, sender_id, created_at, is_read
            FROM private_messages
            WHERE sender_id = ? OR receiver_id = ?
        ),
        last_msg AS (
            SELECT peer_id, body, sender_id, created_at,
                   ROW_NUMBER() OVER (PARTITION BY peer_id ORDER BY id DESC) rn
            FROM pairs
        ),
        unread AS (
            SELECT sender_id AS peer_id, COUNT(*) c
            FROM private_messages
            WHERE receiver_id = ? AND is_read = 0
            GROUP BY sender_id
        )
        SELECT u.id, u.ism, u.familiya, u.avatar, u.plan, u.role,
               lm.body AS last_body, lm.sender_id AS last_sender_id, lm.created_at AS last_at,
               COALESCE(un.c, 0) AS unread_count
        FROM last_msg lm
        JOIN users u ON u.id = lm.peer_id
        LEFT JOIN unread un ON un.peer_id = lm.peer_id
        WHERE lm.rn = 1
        ORDER BY lm.created_at DESC
        """,
        (user_id, user_id, user_id, user_id)
    )


def get_thread(user_id: int, peer_id: int, limit: int = 100):
    """Ikki foydalanuvchi orasidagi xabarlar tarixi (eskidan yangiga)."""
    rows = query_all(
        """SELECT * FROM (
               SELECT * FROM private_messages
               WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)
               ORDER BY id DESC LIMIT ?
           ) sub ORDER BY id ASC""",
        (user_id, peer_id, peer_id, user_id, limit)
    )
    return rows


def send_message(sender_id: int, receiver_id: int, body: str) -> tuple[bool, str]:
    body = (body or "").strip()
    if not body:
        return False, "Xabar matni bo'sh bo'lishi mumkin emas."
    if len(body) > 2000:
        return False, "Xabar juda uzun (maksimal 2000 belgi)."
    if sender_id == receiver_id:
        return False, "O'zingizga xabar yubora olmaysiz."
    receiver = query_one("SELECT id, is_blocked FROM users WHERE id=?", (receiver_id,))
    if not receiver:
        return False, "Foydalanuvchi topilmadi."
    execute(
        "INSERT INTO private_messages (sender_id, receiver_id, body) VALUES (?,?,?)",
        (sender_id, receiver_id, body)
    )
    return True, "OK"


def mark_thread_read(user_id: int, peer_id: int):
    execute(
        "UPDATE private_messages SET is_read=1 WHERE sender_id=? AND receiver_id=? AND is_read=0",
        (peer_id, user_id)
    )


def get_unread_total(user_id: int) -> int:
    row = query_one(
        "SELECT COUNT(*) c FROM private_messages WHERE receiver_id=? AND is_read=0",
        (user_id,)
    )
    return row["c"] if row else 0


def search_users(query: str, exclude_user_id: int, limit: int = 15):
    """Yangi suhbat boshlash uchun foydalanuvchi qidirish."""
    q = f"%{query.strip()}%"
    return query_all(
        """SELECT id, ism, familiya, avatar, plan, custom_id
           FROM users
           WHERE id != ? AND is_blocked = 0
                 AND (ism LIKE ? OR familiya LIKE ? OR email LIKE ? OR custom_id LIKE ?)
           ORDER BY ism LIMIT ?""",
        (exclude_user_id, q, q, q, q, limit)
    )
