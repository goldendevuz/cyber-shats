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


# =================================================================
# STARTAPLAR AUKSIONI — admin tasdiqlangan loyihalarni auksionga qo'yadi,
# foydalanuvchilar CODE bilan tiklashadi (g'olib homiylik/egalik huquqini oladi).
# =================================================================

def create_auction(startup_id: int, admin_id: int, start_price: int = None,
                   duration_days: int = None) -> tuple[bool, str, int]:
    """Admin tasdiqlangan loyihani auksionga qo'yadi."""
    from pricing import get_price
    import datetime

    startup = query_one("SELECT * FROM startups WHERE id=?", (startup_id,))
    if not startup:
        return False, "Loyiha topilmadi.", 0
    if startup["status"] != "approved":
        return False, "Faqat tasdiqlangan loyihalarni auksionga qo'yish mumkin.", 0
    if startup["in_auction"]:
        return False, "Bu loyiha allaqachon auksionda.", 0

    if start_price is None:
        start_price = get_price("startup_auction_default_price")
    if duration_days is None:
        duration_days = get_price("startup_auction_default_days")

    ends_at = (datetime.datetime.now() + datetime.timedelta(days=duration_days)).isoformat()
    aid = execute(
        """INSERT INTO startup_auctions (startup_id, start_price, ends_at, created_by)
           VALUES (?,?,?,?)""",
        (startup_id, start_price, ends_at, admin_id)
    )
    execute("UPDATE startups SET in_auction=1 WHERE id=?", (startup_id,))

    execute(
        "INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
        (startup["user_id"], "Loyihangiz auksionga qo'yildi!",
         f"«{startup['name']}» loyihangiz auksionga qo'yildi. Boshlang'ich narx: {start_price:,} CODE.",
         "success")
    )
    log_action(admin_id, "startup_auction_created", details=f"startup:{startup_id},auction:{aid}")
    return True, "Auksion yaratildi!", aid


def get_active_auctions():
    return query_all(
        """SELECT a.*, s.name, s.description, s.image_path, s.category,
                  u.ism as bidder_ism, u.familiya as bidder_familiya
           FROM startup_auctions a
           JOIN startups s ON s.id = a.startup_id
           LEFT JOIN users u ON u.id = a.current_bidder_id
           WHERE a.status='active'
           ORDER BY a.ends_at ASC"""
    )


def get_auction(auction_id: int):
    return query_one(
        """SELECT a.*, s.name, s.description, s.image_path, s.category, s.link_url,
                  s.user_id as owner_id, ou.ism as owner_ism, ou.familiya as owner_familiya,
                  u.ism as bidder_ism, u.familiya as bidder_familiya
           FROM startup_auctions a
           JOIN startups s ON s.id = a.startup_id
           JOIN users ou ON ou.id = s.user_id
           LEFT JOIN users u ON u.id = a.current_bidder_id
           WHERE a.id=?""",
        (auction_id,)
    )


def get_auction_bids(auction_id: int):
    return query_all(
        """SELECT b.*, u.ism, u.familiya FROM startup_auction_bids b
           JOIN users u ON u.id = b.user_id
           WHERE b.auction_id=? ORDER BY b.id DESC""",
        (auction_id,)
    )


def place_bid(auction_id: int, user_id: int, amount: int) -> tuple[bool, str]:
    """Auksionga tiklov qo'yish. Pul darhol yechilmaydi — faqat g'olib bo'lganda
    yechiladi (oddiy, ID auksioni bilan bir xil naqsh)."""
    import datetime

    auction = query_one("SELECT * FROM startup_auctions WHERE id=?", (auction_id,))
    if not auction:
        return False, "Auksion topilmadi."
    if auction["status"] != "active":
        return False, "Bu auksion allaqachon yakunlangan."
    try:
        ends = datetime.datetime.fromisoformat(auction["ends_at"])
    except Exception:
        ends = datetime.datetime.now()
    if datetime.datetime.now() > ends:
        return False, "Auksion muddati tugagan."

    min_bid = max(auction["start_price"], auction["current_bid"] + 1000)
    if amount < min_bid:
        return False, f"Tiklov kamida {min_bid:,} CODE bo'lishi kerak."

    from coins import get_balance
    if get_balance(user_id) < amount:
        return False, "Balansingizda yetarli CODE yo'q."

    execute(
        "UPDATE startup_auctions SET current_bid=?, current_bidder_id=? WHERE id=?",
        (amount, user_id, auction_id)
    )
    execute(
        "INSERT INTO startup_auction_bids (auction_id, user_id, amount) VALUES (?,?,?)",
        (auction_id, user_id, amount)
    )
    log_action(user_id, "startup_auction_bid", details=f"auction:{auction_id},amount:{amount}")
    return True, f"Tiklovingiz qabul qilindi: {amount:,} CODE!"


def finalize_auction(auction_id: int) -> tuple[bool, str]:
    """Auksion muddati tugaganda yakunlaydi: g'olibdan CODE yechiladi,
    g'azna jamg'armasiga tushadi."""
    auction = query_one("SELECT * FROM startup_auctions WHERE id=?", (auction_id,))
    if not auction or auction["status"] != "active":
        return False, "Auksion topilmadi yoki allaqachon yakunlangan."

    execute("UPDATE startup_auctions SET status='ended' WHERE id=?", (auction_id,))
    execute("UPDATE startups SET in_auction=0 WHERE id=?", (auction["startup_id"],))

    if not auction["current_bidder_id"]:
        return True, "Auksion g'olibsiz yakunlandi (tiklov bo'lmadi)."

    from coins import spend_coins, _treasury_fund_in
    ok, msg = spend_coins(auction["current_bidder_id"], auction["current_bid"], "startup_auction_win")
    if not ok:
        # Agar to'lay olmasa, auksion bekor qilinadi
        execute("UPDATE startup_auctions SET status='cancelled' WHERE id=?", (auction_id,))
        return False, f"G'olib to'lay olmadi: {msg}"

    _treasury_fund_in(auction["current_bid"], "startup_auction", auction["current_bidder_id"])

    startup = query_one("SELECT name, user_id FROM startups WHERE id=?", (auction["startup_id"],))
    execute(
        "INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
        (auction["current_bidder_id"], "Auksionda g'olib bo'ldingiz!",
         f"«{startup['name']}» loyihasiga homiylik huquqini {auction['current_bid']:,} CODE evaziga yutib oldingiz!",
         "success")
    )
    execute(
        "INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
        (startup["user_id"], "Loyihangiz auksioni yakunlandi",
         f"«{startup['name']}» loyihangiz auksioni {auction['current_bid']:,} CODE ga yakunlandi!",
         "success")
    )
    return True, f"Auksion yakunlandi! G'olib {auction['current_bid']:,} CODE to'ladi."


def check_and_finalize_expired_auctions():
    """Muddati o'tgan barcha faol auksionlarni yakunlaydi. Fon jarayoni shart
    emas — har sahifa yuklanganda chaqiriladi (Hacker Lab/plan tekshiruvi kabi)."""
    import datetime
    now = datetime.datetime.now().isoformat()
    expired = query_all(
        "SELECT id FROM startup_auctions WHERE status='active' AND ends_at <= ?", (now,)
    )
    for row in expired:
        finalize_auction(row["id"])
    return len(expired)


def cancel_auction(auction_id: int, admin_id: int) -> tuple[bool, str]:
    auction = query_one("SELECT * FROM startup_auctions WHERE id=?", (auction_id,))
    if not auction or auction["status"] != "active":
        return False, "Auksion topilmadi yoki allaqachon yakunlangan."
    execute("UPDATE startup_auctions SET status='cancelled' WHERE id=?", (auction_id,))
    execute("UPDATE startups SET in_auction=0 WHERE id=?", (auction["startup_id"],))
    log_action(admin_id, "startup_auction_cancelled", details=f"auction:{auction_id}")
    return True, "Auksion bekor qilindi."
