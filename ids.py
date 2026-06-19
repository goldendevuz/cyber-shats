"""
CYBER SHATS — User ID va Auktsion moduli
7 xonali unikal ID tizimi, premium IDlar, auktsion
"""
import random
import string
from db import query_one, query_all, execute
from config import Config

# Maxsus (premium) IDlar va ularning narxlari
PREMIUM_IDS = {
    "1111111": ("quad7", 100_000),
    "2222222": ("quad7", 100_000),
    "3333333": ("quad7", 100_000),
    "4444444": ("quad7", 100_000),
    "5555555": ("quad7", 100_000),
    "6666666": ("quad7", 100_000),
    "7777777": ("quad7", 100_000),
    "8888888": ("quad7", 100_000),
    "9999999": ("quad7", 100_000),
    "1234567": ("sequential", 120_000),
}

# 4 xil raqam ID narxlari
ID_PRICE_RULES = {
    "quad4": 40_000,   # 4 ta bir xil raqam
    "quad5": 50_000,   # 5 ta bir xil raqam
    "quad6": 60_000,   # 6 ta bir xil raqam
    "quad7": 100_000,  # 7 ta bir xil raqam
    "sequential": 120_000,  # 1234567
}


def _id_type_and_price(custom_id: str) -> tuple[str, int]:
    """ID turi va narxini aniqlaydi."""
    if custom_id in PREMIUM_IDS:
        return PREMIUM_IDS[custom_id]
    digits = list(custom_id)
    for count in [7, 6, 5, 4]:
        for d in "0123456789":
            if digits.count(d) >= count:
                key = f"quad{count}"
                return key, ID_PRICE_RULES[key]
    return "normal", 0


def generate_unique_id() -> str:
    """Yangi unikal 7 xonali ID yaratadi (avto-registratsiyada ishlatiladi)."""
    forbidden = set(PREMIUM_IDS.keys())
    # 4+ bir xil raqamli IDlarni ham taqiqlaylik (ular premium)
    for _ in range(1000):
        num = random.randint(1_000_000, 9_999_999)
        cid = str(num)
        if cid in forbidden:
            continue
        # 4+ bir xil raqam bo'lsa premium
        has_quad = any(cid.count(d) >= 4 for d in "0123456789")
        if has_quad:
            continue
        # Mavjudligini tekshir
        exists = query_one("SELECT id FROM users WHERE custom_id=?", (cid,))
        if not exists:
            return cid
    # Fallback
    return str(random.randint(1_000_000, 9_999_999))


def set_user_id(user_id: int, new_custom_id: str) -> tuple[bool, str]:
    """Foydalanuvchi o'z IDni o'zgartiradi (agar ID bo'sh bo'lsa)."""
    existing = query_one("SELECT id FROM users WHERE custom_id=?", (new_custom_id,))
    if existing:
        return False, "Bu ID allaqachon band. Boshqa ID tanlang."
    execute("UPDATE users SET custom_id=? WHERE id=?", (new_custom_id, user_id))
    return True, "ID muvaffaqiyatli o'zgartirildi."


def get_premium_ids_list():
    """Barcha premium IDlar va ularning holati."""
    result = []
    for cid, (id_type, price) in PREMIUM_IDS.items():
        row = query_one(
            "SELECT * FROM premium_ids WHERE custom_id=?", (cid,)
        )
        if row:
            result.append(dict(row))
        else:
            result.append({
                "custom_id": cid,
                "id_type": id_type,
                "base_price": price,
                "status": "available",
                "owner_user_id": None,
            })
    return result


def init_premium_ids():
    """Premium IDlarni bazaga yozadi (bir marta)."""
    for cid, (id_type, price) in PREMIUM_IDS.items():
        execute(
            "INSERT OR IGNORE INTO premium_ids (custom_id, id_type, base_price, status) VALUES (?,?,?,?)",
            (cid, id_type, price, "available")
        )


def buy_premium_id(user_id: int, custom_id: str) -> tuple[bool, str]:
    """Admin tomonidan tayinlangan premium IDni code bilan sotib olish."""
    from coins import spend_coins
    pid = query_one("SELECT * FROM premium_ids WHERE custom_id=?", (custom_id,))
    if not pid:
        return False, "Bu ID mavjud emas."
    if pid["status"] != "available":
        return False, "Bu ID allaqachon band yoki auktsiyonda."
    price = pid["base_price"]
    ok, msg = spend_coins(user_id, price, "buy_premium_id", pid["id"])
    if not ok:
        return False, msg
    import datetime
    execute("UPDATE premium_ids SET status='sold', owner_user_id=?, sold_at=? WHERE custom_id=?",
            (user_id, datetime.datetime.now().isoformat(), custom_id))
    execute("UPDATE users SET custom_id=? WHERE id=?", (custom_id, user_id))
    return True, f"ID #{custom_id} muvaffaqiyatli sotib olindi!"


def get_active_auctions():
    return query_all(
        """SELECT a.*, p.id_type, p.base_price,
                  u.ism as bidder_ism, u.familiya as bidder_familiya
           FROM id_auctions a
           JOIN premium_ids p ON p.id=a.premium_id_id
           LEFT JOIN users u ON u.id=a.current_bidder_id
           WHERE a.status='active' AND a.ends_at > datetime('now')
           ORDER BY a.ends_at ASC"""
    )


def place_bid(user_id: int, auction_id: int, bid_amount: int) -> tuple[bool, str]:
    """Auktsiyonda taklif qo'yish."""
    from coins import spend_coins, add_coins
    auction = query_one("SELECT * FROM id_auctions WHERE id=? AND status='active'", (auction_id,))
    if not auction:
        return False, "Auktsion topilmadi yoki tugagan."
    min_bid = max(auction["current_bid"] + 1000, auction["start_price"])
    if bid_amount < min_bid:
        return False, f"Minimal taklif: {min_bid:,} code"
    # Avvalgi bidder puli qaytarilsin
    if auction["current_bidder_id"] and auction["current_bidder_id"] != user_id:
        add_coins(auction["current_bidder_id"], auction["current_bid"], "auction_refund", auction_id)
    # Yangi bidder
    ok, msg = spend_coins(user_id, bid_amount, "auction_bid", auction_id)
    if not ok:
        return False, msg
    execute("UPDATE id_auctions SET current_bid=?, current_bidder_id=? WHERE id=?",
            (bid_amount, user_id, auction_id))
    execute("INSERT INTO auction_bids (auction_id, user_id, bid_amount) VALUES (?,?,?)",
            (auction_id, user_id, bid_amount))
    return True, f"Taklif qabul qilindi: {bid_amount:,} code"


def finalize_auction(auction_id: int):
    """Tugagan auktsionni yakunlash (cron yoki admin tugmasi orqali)."""
    import datetime
    auction = query_one("SELECT * FROM id_auctions WHERE id=?", (auction_id,))
    if not auction or auction["status"] != "active":
        return
    execute("UPDATE id_auctions SET status='ended' WHERE id=?", (auction_id,))
    if auction["current_bidder_id"]:
        execute("UPDATE premium_ids SET status='sold', owner_user_id=?, sold_at=? WHERE custom_id=?",
                (auction["current_bidder_id"], datetime.datetime.now().isoformat(), auction["custom_id"]))
        execute("UPDATE users SET custom_id=? WHERE id=?",
                (auction["custom_id"], auction["current_bidder_id"]))
        execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                (auction["current_bidder_id"],
                 f"Auktsion g'olibi!",
                 f"Siz #{auction['custom_id']} ID auktsionida g'olib bo'ldingiz!",
                 "success"))
    execute("UPDATE premium_ids SET status='available' WHERE custom_id=? AND owner_user_id IS NULL",
            (auction["custom_id"],))
