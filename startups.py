"""
CYBER SHATS V1.3 — Startaplar (foydalanuvchi loyihalari) moduli.

Foydalanuvchilar o'z loyihalarini (startaplarini) joylaydi: nomi, tavsifi, rasm.
Admin tasdiqlagandan keyin bosh sahifada "Foydalanuvchilar loyihalari" deb
har kuni aylanib turadigan (kunlik tasodifiy tartibda) ko'rinishda chiqadi.

"Har kuni aylanish" — fon jarayoni (cron) shart emas: har kuni bugungi sana
urug' (seed) sifatida ishlatilib, o'sha kun davomida barqaror, lekin
kundan-kunga farqli tasodifiy tartib hosil qilinadi.
"""
import random
import datetime
from db import query_one, query_all, execute, log_action

STARTUP_ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
STARTUP_UPLOAD_DIR = "static/uploads/startups"

CATEGORIES = [
    ("web", "Veb-sayt"), ("mobile", "Mobil ilova"), ("ai", "AI / ML"),
    ("game", "O'yin"), ("hardware", "IoT / Hardware"), ("saas", "SaaS"),
    ("boshqa", "Boshqa"),
]


def create_startup(user_id: int, name: str, description: str, image_path: str,
                   link_url: str = "", category: str = "boshqa") -> tuple[bool, str, int]:
    name = (name or "").strip()
    if not name:
        return False, "Loyiha nomi majburiy.", 0
    if len(name) > 120:
        return False, "Loyiha nomi juda uzun.", 0
    sid = execute(
        """INSERT INTO startups (user_id, name, description, image_path, link_url, category, status)
           VALUES (?,?,?,?,?,?, 'pending')""",
        (user_id, name, (description or "").strip(), image_path, (link_url or "").strip(), category)
    )
    log_action(user_id, "startup_created", details=f"startup:{sid}")
    return True, "Loyihangiz yuborildi! Admin tasdiqlagandan keyin bosh sahifada ko'rinadi.", sid


def get_startup(startup_id: int):
    return query_one(
        """SELECT s.*, u.ism, u.familiya, u.avatar
           FROM startups s JOIN users u ON u.id = s.user_id WHERE s.id=?""",
        (startup_id,)
    )


def get_user_startups(user_id: int):
    return query_all("SELECT * FROM startups WHERE user_id=? ORDER BY id DESC", (user_id,))


def get_approved_startups(limit: int = 100):
    return query_all(
        """SELECT s.*, u.ism, u.familiya, u.avatar
           FROM startups s JOIN users u ON u.id = s.user_id
           WHERE s.status='approved' ORDER BY s.id DESC LIMIT ?""",
        (limit,)
    )


def get_daily_rotating_startups(count: int = 6):
    """
    Bosh sahifa uchun: tasdiqlangan loyihalardan bugungi kunga xos tasodifiy
    tartibda 'count' tasini tanlaydi. Bugun davomida barqaror (bir xil),
    lekin ertaga boshqacha tartibda chiqadi — fon jarayoni shart emas.
    """
    all_approved = get_approved_startups(500)
    if not all_approved:
        return []
    today_seed = datetime.date.today().isoformat()  # masalan "2026-06-21"
    rng = random.Random(today_seed)
    shuffled = list(all_approved)
    rng.shuffle(shuffled)
    return shuffled[:count]


def increment_view(startup_id: int):
    execute("UPDATE startups SET view_count = view_count + 1 WHERE id=?", (startup_id,))


def is_liked(startup_id: int, user_id: int) -> bool:
    row = query_one("SELECT id FROM startup_likes WHERE startup_id=? AND user_id=?", (startup_id, user_id))
    return bool(row)


def toggle_like(startup_id: int, user_id: int) -> tuple[bool, int]:
    if is_liked(startup_id, user_id):
        execute("DELETE FROM startup_likes WHERE startup_id=? AND user_id=?", (startup_id, user_id))
        liked = False
    else:
        execute("INSERT INTO startup_likes (startup_id, user_id) VALUES (?,?)", (startup_id, user_id))
        liked = True
    row = query_one("SELECT COUNT(*) c FROM startup_likes WHERE startup_id=?", (startup_id,))
    return liked, row["c"] if row else 0


def get_like_count(startup_id: int) -> int:
    row = query_one("SELECT COUNT(*) c FROM startup_likes WHERE startup_id=?", (startup_id,))
    return row["c"] if row else 0


def delete_startup(startup_id: int, actor_id: int, is_admin: bool = False) -> tuple[bool, str]:
    startup = query_one("SELECT user_id FROM startups WHERE id=?", (startup_id,))
    if not startup:
        return False, "Loyiha topilmadi."
    if startup["user_id"] != actor_id and not is_admin:
        return False, "Faqat o'z loyihangizni o'chira olasiz."
    execute("DELETE FROM startup_likes WHERE startup_id=?", (startup_id,))
    execute("DELETE FROM startups WHERE id=?", (startup_id,))
    return True, "Loyiha o'chirildi."


# =================================================================
# ADMIN — tasdiqlash
# =================================================================

def get_pending_startups():
    return query_all(
        """SELECT s.*, u.ism, u.familiya, u.email
           FROM startups s JOIN users u ON u.id = s.user_id
           WHERE s.status='pending' ORDER BY s.id DESC"""
    )


def get_all_startups_admin(status: str = None):
    if status:
        return query_all(
            """SELECT s.*, u.ism, u.familiya, u.email
               FROM startups s JOIN users u ON u.id = s.user_id
               WHERE s.status=? ORDER BY s.id DESC""",
            (status,)
        )
    return query_all(
        """SELECT s.*, u.ism, u.familiya, u.email
           FROM startups s JOIN users u ON u.id = s.user_id
           ORDER BY s.id DESC"""
    )


def review_startup(startup_id: int, admin_id: int, decision: str) -> tuple[bool, str]:
    if decision not in ("approved", "rejected"):
        return False, "Noto'g'ri qaror."
    startup = query_one("SELECT * FROM startups WHERE id=?", (startup_id,))
    if not startup:
        return False, "Loyiha topilmadi."
    execute(
        "UPDATE startups SET status=?, reviewed_by=?, reviewed_at=datetime('now') WHERE id=?",
        (decision, admin_id, startup_id)
    )
    title = "Loyihangiz tasdiqlandi!" if decision == "approved" else "Loyihangiz rad etildi"
    body = (f"«{startup['name']}» loyihangiz bosh sahifada ko'rsatiladi."
            if decision == "approved" else f"«{startup['name']}» loyihangiz tasdiqlanmadi.")
    execute(
        "INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
        (startup["user_id"], title, body, "success" if decision == "approved" else "error")
    )
    try:
        import webpush_mod
        webpush_mod.send_push_to_user(startup["user_id"], title, body, "/startups")
    except Exception:
        pass
    log_action(admin_id, f"startup_{decision}", details=f"startup:{startup_id}")
    return True, f"Loyiha {'tasdiqlandi' if decision=='approved' else 'rad etildi'}."
