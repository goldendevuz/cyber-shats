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

# Saytdagi va botdagi bir xil karta ma'lumotlari (bitta joydan boshqarish uchun)
PAYMENT_CARDS = {
    "uzcard": "8600 1234 5678 9012",
    "humo":   "9860 1234 5678 9012",
}

# Tavsiya etilgan tezkor paketlar (foydalanuvchi shulardan birini tanlashi yoki o'zi yozishi mumkin)
SUGGESTED_PACKAGES = [1_000, 5_000, 10_000, 20_000, 30_000, 50_000, 70_000, 100_000]

MIN_AMOUNT = 1_000
MAX_AMOUNT = 100_000_000


def create_site_purchase_request(user_id: int, custom_id: str, amount: int,
                                  receipt_file_path: str) -> tuple[bool, str, int]:
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

    price_uzs = amount  # 1 CODE = 1 so'm

    rid = execute(
        """INSERT INTO bot_purchase_requests
           (request_type, code_amount, price_uzs, target_custom_id, site_user_id,
            receipt_file_path, source, status)
           VALUES ('code', ?, ?, ?, ?, ?, 'site', 'pending')""",
        (amount, price_uzs, custom_id, user["id"], receipt_file_path)
    )
    log_action(user_id, "site_code_purchase_request", details=f"amount:{amount},req:{rid}")
    return True, "So'rov yuborildi! G'azna tekshirib, tez orada tasdiqlaydi.", rid


def get_user_purchase_requests(user_id: int, limit: int = 20):
    return query_all(
        """SELECT * FROM bot_purchase_requests
           WHERE site_user_id=? AND source='site'
           ORDER BY id DESC LIMIT ?""",
        (user_id, limit)
    )
