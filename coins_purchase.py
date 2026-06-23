"""
CYBER SHATS V1.3 — Saytdan to'g'ridan-to'g'ri CODE sotib olish moduli.

Foydalanuvchi o'z panelidan:
1. ID kiritadi (yoki o'z ID'si avtomatik)
2. CODE miqdorini tanlaydi yoki o'zi yozadi (1 CODE = 1 so'm)
3. Karta raqamlari ko'rsatiladi
4. To'lov chekini rasm/fayl sifatida yuklaydi
5. G'azna (botdagi kabi) tekshirib tasdiqlaydi yoki rad etadi
6. Tasdiqlansa — CODE jamg'armadan foydalanuvchiga o'tadi
"""
from db import query_one, query_all, execute, log_action
import datetime

PAYMENT_CARDS = {
    "uzcard": "8600 1234 5678 9012",
    "humo":   "9860 1234 5678 9012",
}

_DEFAULT_PACKAGES = [1_000, 5_000, 10_000, 20_000, 30_000, 50_000, 70_000, 100_000]

MIN_AMOUNT = 1_000
MAX_AMOUNT = 100_000_000


def get_packages_with_prices() -> list[dict]:
    """Bazadan paket narxlarini qaytaradi."""
    try:
        rows = query_all("SELECT key, value FROM pricing_settings WHERE key LIKE 'code_pack_%' ORDER BY CAST(REPLACE(key,'code_pack_','') AS INTEGER)")
        if rows:
            return [{"amount": int(r["key"].replace("code_pack_","")), "price": int(r["value"])} for r in rows]
    except Exception:
        pass
    return [{"amount": a, "price": a} for a in _DEFAULT_PACKAGES]


def get_suggested_packages() -> list[int]:
    pkgs = get_packages_with_prices()
    return [p["amount"] for p in pkgs]


# Eski mos kelish uchun
SUGGESTED_PACKAGES = _DEFAULT_PACKAGES


def validate_promo_code(code: str, user_id: int, amount: int) -> tuple[bool, str, int]:
    """
    Promo kodni tekshiradi.
    Returns: (valid, message, discount_amount_code)
    """
    if not code or not code.strip():
        return False, "", 0
    code = code.strip().upper()
    try:
        promo = query_one(
            "SELECT * FROM promo_codes WHERE code=? AND is_active=1",
            (code,)
        )
        if not promo:
            return False, "Promo kod topilmadi yoki faol emas.", 0

        # Muddati tekshirish
        if promo["expires_at"]:
            try:
                exp = datetime.datetime.fromisoformat(promo["expires_at"])
                if datetime.datetime.now() > exp:
                    return False, "Promo kodning muddati tugagan.", 0
            except Exception:
                pass

        # Foydalanish limiti
        if promo["max_uses"] > 0 and promo["used_count"] >= promo["max_uses"]:
            return False, "Promo kod foydalanish limiti tugagan.", 0

        # Bu foydalanuvchi allaqachon ishlatganmi?
        already = query_one(
            "SELECT id FROM promo_code_uses WHERE promo_id=? AND user_id=?",
            (promo["id"], user_id)
        )
        if already:
            return False, "Siz bu promo kodni allaqachon ishlatgansiz.", 0

        # Chegirma hisoblash
        if promo["discount_type"] == "pct":
            discount = int(amount * promo["discount_value"] / 100)
        else:  # fixed
            discount = min(promo["discount_value"], amount)

        msg = f"Promo kod qabul qilindi! Chegirma: {discount:,} so'm"
        return True, msg, discount

    except Exception as e:
        return False, "Promo kod tekshirishda xato.", 0


def apply_promo_code(promo_code_str: str, user_id: int, order_id: int = None) -> bool:
    """Promo kodni ishlatilgan deb belgilaydi."""
    try:
        promo = query_one("SELECT id FROM promo_codes WHERE code=?", (promo_code_str.strip().upper(),))
        if not promo:
            return False
        execute(
            "INSERT INTO promo_code_uses (promo_id, user_id, order_id) VALUES (?,?,?)",
            (promo["id"], user_id, order_id)
        )
        execute(
            "UPDATE promo_codes SET used_count=used_count+1 WHERE id=?",
            (promo["id"],)
        )
        return True
    except Exception:
        return False


def create_site_purchase_request(user_id: int, custom_id: str, amount: int,
                                  receipt_file_path: str, discount: int = 0,
                                  promo_code: str = None) -> tuple[bool, str, int]:
    """Foydalanuvchi saytdan CODE sotib olish so'rovini yaratadi (g'azna tasdiqlashi kerak)."""
    if amount < MIN_AMOUNT:
        return False, f"Minimal miqdor: {MIN_AMOUNT:,} CODE.", 0
    if amount > MAX_AMOUNT:
        return False, "Miqdor juda katta.", 0
    if not receipt_file_path:
        return False, "Chek rasmi/fayli majburiy.", 0

    user = query_one("SELECT id FROM users WHERE custom_id=?", (custom_id,))
    if not user:
        return False, "Bu ID saytda topilmadi.", 0

    # Paket narxini bazadan olish
    packages = get_packages_with_prices()
    price_uzs = amount  # standart 1:1
    for p in packages:
        if p["amount"] == amount:
            price_uzs = p["price"]
            break

    # Promo chegirma
    final_price = max(0, price_uzs - discount)

    rid = execute(
        """INSERT INTO bot_purchase_requests
           (request_type, code_amount, price_uzs, target_custom_id, site_user_id,
            receipt_file_path, source, status)
           VALUES ('code', ?, ?, ?, ?, ?, 'site', 'pending')""",
        (amount, final_price, custom_id, user["id"], receipt_file_path)
    )
    log_action(user_id, "site_code_purchase_request",
               details=f"amount:{amount},price:{final_price},promo:{promo_code},req:{rid}")

    msg = f"So'rov yuborildi! G'azna tekshirib, tez orada tasdiqlaydi."
    if discount > 0:
        msg += f" Promo chegirma: {discount:,} so'm qo'llanildi."
    return True, msg, rid


def get_user_purchase_requests(user_id: int, limit: int = 20):
    return query_all(
        """SELECT * FROM bot_purchase_requests
           WHERE site_user_id=? AND source='site'
           ORDER BY id DESC LIMIT ?""",
        (user_id, limit)
    )
