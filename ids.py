"""
CYBER SHATS — User ID va Auktsion moduli
7 xonali unikal ID tizimi, premium IDlar (bazada saqlanadi, admin to'liq boshqaradi), auktsion
"""
import random
import string
from db import query_one, query_all, execute
from config import Config

# 4 xil raqam ID narxlari — avtomatik narx aniqlash uchun standart jadval
# (Admin alohida ID uchun bazada maxsus narx belgilashi mumkin, bu faqat fallback)
ID_PRICE_RULES = {
    "quad4": 40_000,   # 4 ta bir xil raqam
    "quad5": 50_000,   # 5 ta bir xil raqam
    "quad6": 60_000,   # 6 ta bir xil raqam
    "quad7": 100_000,  # 7 ta bir xil raqam
    "sequential": 120_000,  # 1234567 kabi
}


def _auto_id_type_and_price(custom_id: str) -> tuple[str, int]:
    """Bazada topilmagan yangi ID uchun avtomatik tur va narx aniqlaydi."""
    digits = list(custom_id)
    for count in [7, 6, 5, 4]:
        for d in "0123456789":
            if digits.count(d) >= count:
                key = f"quad{count}"
                return key, ID_PRICE_RULES[key]
    return "normal", 0


def _id_type_and_price(custom_id: str) -> tuple[str, int]:
    """ID turi va narxini aniqlaydi: avval bazadan, topilmasa avtomatik."""
    row = query_one("SELECT id_type, base_price FROM premium_ids WHERE custom_id=?", (custom_id,))
    if row:
        return row["id_type"], row["base_price"]
    return _auto_id_type_and_price(custom_id)


def generate_unique_id() -> str:
    """Yangi unikal 7 xonali ID yaratadi (avto-registratsiyada ishlatiladi)."""
    for _ in range(1000):
        num = random.randint(1_000_000, 9_999_999)
        cid = str(num)
        # Bazada premium sifatida ro'yxatdan o'tgan IDlarni o'tkazib yuborish
        is_premium = query_one("SELECT id FROM premium_ids WHERE custom_id=?", (cid,))
        if is_premium:
            continue
        # 4+ bir xil raqam bo'lsa ham premium hisoblanadi — avtomatik berilmasin
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
    """Bazadagi barcha premium IDlar va ularning holati (admin tomonidan qo'shilgan/tahrirlangan)."""
    return query_all("SELECT * FROM premium_ids ORDER BY created_at DESC")


def init_premium_ids():
    """Eski versiyalar bilan moslik uchun qoldirilgan — endi premium IDlar to'liq
    admin panel orqali (admin_create_premium_id) qo'shiladi va migrate_v2.py orqali seed qilinadi."""
    pass


def admin_create_premium_id(custom_id: str, base_price: int, id_type: str = "custom") -> tuple[bool, str]:
    """Admin yangi premium ID qo'shadi (istalgan 7 xonali raqam + narx)."""
    custom_id = custom_id.strip()
    if len(custom_id) != 7 or not custom_id.isdigit():
        return False, "ID 7 ta raqamdan iborat bo'lishi kerak."
    if base_price < 0:
        return False, "Narx manfiy bo'lishi mumkin emas."
    existing = query_one("SELECT id FROM premium_ids WHERE custom_id=?", (custom_id,))
    if existing:
        return False, "Bu ID allaqachon premium ro'yxatda mavjud."
    owned = query_one("SELECT id FROM users WHERE custom_id=?", (custom_id,))
    if owned:
        return False, "Bu ID allaqachon bir foydalanuvchiga tegishli."
    execute(
        "INSERT INTO premium_ids (custom_id, id_type, base_price, status) VALUES (?,?,?,'available')",
        (custom_id, id_type, base_price)
    )
    return True, f"#{custom_id} premium ID {base_price:,} code narx bilan qo'shildi."


def admin_update_premium_id_price(custom_id: str, base_price: int) -> tuple[bool, str]:
    """Admin mavjud premium IDning narxini o'zgartiradi."""
    if base_price < 0:
        return False, "Narx manfiy bo'lishi mumkin emas."
    pid = query_one("SELECT * FROM premium_ids WHERE custom_id=?", (custom_id,))
    if not pid:
        return False, "Bu ID mavjud emas."
    execute("UPDATE premium_ids SET base_price=? WHERE custom_id=?", (base_price, custom_id))
    return True, f"#{custom_id} narxi {base_price:,} code ga o'zgartirildi."


def admin_delete_premium_id(custom_id: str) -> tuple[bool, str]:
    """Admin premium IDni ro'yxatdan o'chiradi (faqat sotilmagan/auktsionda bo'lmaganlarni)."""
    pid = query_one("SELECT * FROM premium_ids WHERE custom_id=?", (custom_id,))
    if not pid:
        return False, "Bu ID mavjud emas."
    if pid["status"] != "available":
        return False, "Faqat 'bo'sh' holatdagi IDlarni o'chirish mumkin."
    execute("DELETE FROM premium_ids WHERE custom_id=?", (custom_id,))
    return True, f"#{custom_id} premium ID ro'yxatdan o'chirildi."


def buy_premium_id(user_id: int, custom_id: str) -> tuple[bool, str]:
    """Admin tomonidan tayinlangan premium IDni code bilan sotib olish.
    To'langan code g'azna jamg'armasiga tushadi."""
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
    # Sotuvdan kelgan daromad g'azna jamg'armasiga tushadi
    from treasury import add_id_auction_revenue
    add_id_auction_revenue(price, user_id, custom_id)
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
    """Tugagan auktsionni yakunlash (cron yoki admin tugmasi orqali).
    G'olibning to'lagani g'azna jamg'armasiga tushadi."""
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
        try:
            import webpush_mod
            webpush_mod.send_push_to_user(
                auction["current_bidder_id"], "Auktsion g'olibi! 🏆",
                f"Siz #{auction['custom_id']} ID auktsionida g'olib bo'ldingiz!", "/profile"
            )
        except Exception:
            pass
        # G'olibning to'lagani g'azna jamg'armasiga tushadi
        from treasury import add_id_auction_revenue
        add_id_auction_revenue(auction["current_bid"], auction["current_bidder_id"], auction["custom_id"])
    execute("UPDATE premium_ids SET status='available' WHERE custom_id=? AND owner_user_id IS NULL",
            (auction["custom_id"],))


# =================================================================
# VIP MAXSUS ID'LAR — 1 xonali raqamlar (0-9), 10 ta, faqat admin beradi.
# Auksion yo'q, sotuv yo'q — faqat qo'lda admin tomonidan tayinlanadi.
# =================================================================

def get_vip_ids_list():
    """Barcha 10 ta VIP ID holatini qaytaradi (egasi ma'lumoti bilan)."""
    return query_all(
        """SELECT v.*, u.ism, u.familiya, u.email
           FROM vip_ids v
           LEFT JOIN users u ON u.id = v.owner_user_id
           ORDER BY v.digit ASC"""
    )


def assign_vip_id(admin_id: int, digit: str, user_id: int) -> tuple[bool, str]:
    """Admin tomonidan VIP ID (0-9) foydalanuvchiga tayinlanadi.
    Foydalanuvchining oddiy custom_id'i shu bitta raqamga almashtiriladi."""
    digit = str(digit).strip()
    if digit not in "0123456789" or len(digit) != 1:
        return False, "SHATS CYBER PRO ID faqat 0-9 oralig'idagi bitta raqam bo'lishi mumkin."
    vip_row = query_one("SELECT * FROM vip_ids WHERE digit=?", (digit,))
    if not vip_row:
        return False, "Bunday SHATS CYBER PRO ID topilmadi."
    if vip_row["status"] == "assigned":
        return False, f"SHATS CYBER PRO ID '{digit}' allaqachon band."
    user = query_one("SELECT id, custom_id FROM users WHERE id=?", (user_id,))
    if not user:
        return False, "Foydalanuvchi topilmadi."

    import datetime
    old_cid = user["custom_id"]
    execute(
        "UPDATE vip_ids SET status='assigned', owner_user_id=?, assigned_by=?, assigned_at=? WHERE digit=?",
        (user_id, admin_id, datetime.datetime.now().isoformat(), digit)
    )
    execute("UPDATE users SET custom_id=? WHERE id=?", (digit, user_id))
    execute(
        "INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
        (user_id, "SHATS CYBER PRO ID berildi! 🔥",
         f"Sizga maxsus SHATS CYBER PRO ID '#{digit}' tayinlandi! Eski ID: #{old_cid}", "success")
    )
    try:
        import webpush_mod
        webpush_mod.send_push_to_user(
            user_id, "SHATS CYBER PRO ID berildi! 🔥", f"Sizga maxsus SHATS CYBER PRO ID '#{digit}' tayinlandi!", "/profile"
        )
    except Exception:
        pass
    return True, f"SHATS CYBER PRO ID '#{digit}' foydalanuvchiga muvaffaqiyatli berildi."


def revoke_vip_id(digit: str) -> tuple[bool, str]:
    """VIP ID'ni egasidan qaytarib olish (yana 'available' qiladi)."""
    digit = str(digit).strip()
    vip_row = query_one("SELECT * FROM vip_ids WHERE digit=?", (digit,))
    if not vip_row or vip_row["status"] != "assigned":
        return False, "Bu SHATS CYBER PRO ID band emas."
    owner_id = vip_row["owner_user_id"]
    execute("UPDATE vip_ids SET status='available', owner_user_id=NULL, assigned_by=NULL, assigned_at=NULL WHERE digit=?",
            (digit,))
    if owner_id:
        # Foydalanuvchiga yangi oddiy ID beramiz (VIP ID'siz qolmasin)
        new_cid = generate_unique_id()
        execute("UPDATE users SET custom_id=? WHERE id=?", (new_cid, owner_id))
        execute(
            "INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (owner_id, "SHATS CYBER PRO ID qaytarib olindi",
             f"SHATS CYBER PRO ID '#{digit}' administrator tomonidan qaytarib olindi. Yangi ID: #{new_cid}", "info")
        )
    return True, f"SHATS CYBER PRO ID '#{digit}' bo'shatildi."
