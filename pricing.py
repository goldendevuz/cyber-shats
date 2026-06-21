"""
CYBER SHATS — Narxlar va Plan sozlamalari moduli
Barcha narxlar (Pro, AI limit, kurs mukofoti) shu yerdan boshqariladi.
Admin panel orqali o'zgartirilganda DARHOL butun saytda ishlaydi.
"""
from db import query_all, query_one, execute

# Standart qiymatlar (baza bo'sh bo'lsa fallback)
DEFAULTS = {
    # Asosiy
    "pro_price_uzs": 99_000,
    "pro_price_code": 57_000,
    "cyber_pro_price_code": 150_000,
    "vip_price_code": 540_000,
    "pro_ai_limit": 100,
    "pro_duration_days": 30,
    "plan_duration_days": 30,              # Pro/Cyber Pro/VIP obuna muddati (kun)
    "free_ai_limit": 10,
    "free_test_limit": 30,
    "free_smm_access": 0,
    "vip_enabled": 1,                      # Admin VIP versiyani yoqib/o'chirishi
    # Mukofotlar va bonuslar
    "welcome_bonus_code": 7_000,           # yangi foydalanuvchi uchun majburiy bonus
    "course_reward_code": 100,             # oddiy kurs bitirish mukofoti
    "cyber_pro_course_bonus": 1_000,       # Cyber Pro foydalanuvchisi uchun kurs bonusi
    "cyber_pro_welcome_bonus": 10_000,     # Cyber Pro xush kelibsiz bonusi
    "vip_course_bonus": 2_000,             # VIP foydalanuvchisi uchun kurs bonusi
    "vip_welcome_bonus": 30_000,           # VIP xush kelibsiz bonusi
    # Sarflar
    "ai_cost_per_msg": 200,
    "paid_course_code_default": 10_000,
    "coin_transfer_fee_percent": 5,
    # Sertifikat
    "certificate_exam_fee": 5_000,         # yo'nalish oxiri sertifikat imtihoni to'lovi
    "hacker_lab_pro_price": 100_000,       # Pro foydalanuvchi uchun Hacker Lab kirish narxi (Cyber Pro/VIP bepul)
    "hacker_lab_violation_fine": 10_000_000,  # xavfsizlik qoidasini buzgan foydalanuvchiga jarima
    # Ping test (Pentesting)
    "ping_test_free_quota": 10,
    "ping_test_pro_quota": 20,
    "ping_test_cyber_pro_quota": 30,
    "ping_test_vip_quota": 50,
    "ping_test_cost_free": 2_000,
    "ping_test_cost_pro": 1_000,
    "ping_test_cost_cyber_pro": 500,
    "ping_test_cost_vip": 200,
    # ID toifalari uchun chegaralar (auksion ham, sotuvi ham shu oraliqlarda)
    "id_tier_A_min": 800_000, "id_tier_A_max": 1_000_000,
    "id_tier_B_min": 600_000, "id_tier_B_max": 800_000,
    "id_tier_C_min": 400_000, "id_tier_C_max": 600_000,
    "id_tier_D_min": 200_000, "id_tier_D_max": 400_000,
    "id_tier_E_min": 50_000,  "id_tier_E_max": 200_000,
}

_INT_KEYS = set(DEFAULTS.keys())


def get_pricing() -> dict:
    """Barcha narxlar/plan sozlamalarini dict sifatida qaytaradi (int qiymatlar bilan)."""
    rows = query_all("SELECT key, value FROM pricing_settings")
    result = dict(DEFAULTS)
    for row in rows:
        key = row["key"]
        if key in DEFAULTS:
            try:
                result[key] = int(row["value"])
            except (ValueError, TypeError):
                result[key] = DEFAULTS[key]
    return result


def get_price(key: str):
    """Bitta narx/sozlamani qaytaradi."""
    row = query_one("SELECT value FROM pricing_settings WHERE key=?", (key,))
    if row is None:
        return DEFAULTS.get(key, 0)
    try:
        return int(row["value"])
    except (ValueError, TypeError):
        return DEFAULTS.get(key, 0)


def set_prices(updates: dict, updated_by: int = None):
    """Bir nechta narx/sozlamani bazaga yozadi. Faqat ma'lum kalitlarga ruxsat."""
    for key, value in updates.items():
        if key not in DEFAULTS:
            continue
        execute(
            """INSERT INTO pricing_settings (key, value, updated_at, updated_by)
               VALUES (?, ?, datetime('now'), ?)
               ON CONFLICT(key) DO UPDATE SET
                   value=excluded.value,
                   updated_at=excluded.updated_at,
                   updated_by=excluded.updated_by""",
            (key, str(value), updated_by)
        )
