"""
CYBER SHATS — SMM/Targetolog va Logistika uchun alohida AI chat moduli
Faqat Pro foydalanuvchilar uchun
"""
from db import query_one, query_all, execute
from ai import call_ai_assistant, is_ai_configured

SMM_DIRECTIONS = {
    "smm": {
        "name": "SMM Menejeri",
        "icon": "share-2",
        "color": "pink",
        "system": """Siz professional SMM menejeri va ijtimoiy media ekspertiisiz.
O'zbek tilidagi bizneslar uchun Instagram, Telegram, TikTok, Facebook kabi platformalarda 
kontent strategiyasi, post yozish, auditoriya o'stirish, stories, reels, hashtaglar, 
brand storytelling va SMM analitikasi bo'yicha yordam berasiz.
Har doim amaliy, konkret maslahat bering.""",
    },
    "targetolog": {
        "name": "Targetolog",
        "icon": "target",
        "color": "orange",
        "system": """Siz professional targetolog — Facebook Ads, Instagram Ads, Google Ads, 
Telegram Ads va TikTok Ads ekspertiisiz.
Reklama kampaniyalarini sozlash, auditoriya segmentatsiyasi, CPM/CPC optimizatsiya,
A/B test, konversiya funnel, ROAS hisoblash va reklama kreatiflari bo'yicha
O'zbek tilidagi bizneslar uchun amaliy maslahat bering.""",
    },
    "logistika": {
        "name": "Logistika Menejeri",
        "icon": "truck",
        "color": "blue",
        "system": """Siz professional logistika va supply chain menejeriisiz.
Yuk tashish, omborxona boshqaruvi, import/eksport, bojxona, 
last-mile delivery, ERP tizimlar, logistika optimizatsiya,
O'zbekiston va xalqaro logistika qonunchilik bo'yicha
amaliy maslahat bering. Narxlar va marshrutlarni hisoblashga yordam bering.""",
    },
}


def get_smm_history(user_id: int, direction: str, limit: int = 30):
    return query_all(
        "SELECT role, content FROM smm_ai_messages WHERE user_id=? AND direction=? ORDER BY id ASC LIMIT ?",
        (user_id, direction, limit)
    )


def chat_smm(user_id: int, direction: str, message: str) -> tuple[str, bool]:
    """SMM/Logistika AI chati."""
    if direction not in SMM_DIRECTIONS:
        return "Noto'g'ri yo'nalish.", False
    history = get_smm_history(user_id, direction)
    # Xabar saqlash
    execute("INSERT INTO smm_ai_messages (user_id, direction, role, content) VALUES (?,?,?,?)",
            (user_id, direction, "user", message))
    config = SMM_DIRECTIONS[direction]
    # AI chaqiruvi
    reply, is_live = call_ai_assistant(direction, message, history, system_override=config["system"])
    execute("INSERT INTO smm_ai_messages (user_id, direction, role, content) VALUES (?,?,?,?)",
            (user_id, direction, "assistant", reply))
    return reply, is_live
