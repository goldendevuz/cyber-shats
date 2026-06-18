# ============================================================
# CYBER SHATS — AI Yordamchi backend logikasi
# Agar .env faylida ANTHROPIC_API_KEY mavjud bo'lsa — haqiqiy Claude API
# chaqiriladi. Aks holda — tayyor (canned) javob qaytariladi, shunda ham
# interfeys to'liq ishlaydi, faqat javoblar statik bo'ladi.
# ============================================================
import os

ASSISTANT_PROMPTS = {
    "umumiy": "Sen CYBER SHATS platformasining umumiy AI yordamchisisan. IT va dasturlash bo'yicha savollarga "
              "o'zbek tilida, qisqa va aniq javob ber.",
    "kod": "Sen tajribali dasturchisan. Foydalanuvchiga kod yozishda, xatolarni topishda va tushuntirishda "
           "yordam ber. Javoblarni o'zbek tilida ber, kod bloklarini saqlab qoldir.",
    "cyber": "Sen kiberxavfsizlik bo'yicha mutaxassissan (ethical hacking, pentest, tarmoq xavfsizligi). "
             "Faqat ta'lim maqsadida, qonuniy va axloqiy doirada maslahat ber. O'zbek tilida javob ber.",
    "design": "Sen UI/UX va veb-dizayn bo'yicha maslahatchisan. O'zbek tilida amaliy tavsiyalar ber.",
    "cloud": "Sen cloud computing (AWS, Docker, Kubernetes, DevOps) bo'yicha mutaxassissan. O'zbek tilida javob ber.",
    "tarix": "Sen IT va kompyuter texnologiyalari tarixi bo'yicha bilimdonsan. Qiziqarli va aniq faktlar bilan "
             "o'zbek tilida javob ber.",
}

FALLBACK_REPLIES = {
    "umumiy": "Salom! Men CYBER SHATS AI yordamchisiman. Hozircha demo rejimida ishlayapman — to'liq javob "
              "olish uchun platforma administratori ANTHROPIC_API_KEY sozlamasini .env faylga qo'shishi kerak. "
              "Savolingizni saqlab qoldim, key qo'shilgandan so'ng to'liq javob bera olaman.",
    "kod": "Bu demo javob: real kod tahlili uchun .env faylga ANTHROPIC_API_KEY qo'shilishi kerak. Hozircha "
           "namuna: `for i in range(10): print(i)` — Python'da 0 dan 9 gacha sonlarni chop etadi.",
    "cyber": "Demo rejim: kiberxavfsizlik bo'yicha to'liq AI tahlili uchun API kalit kerak. Eslatma: barcha "
             "pentest amaliyotlari faqat o'ziga tegishli yoki ruxsat berilgan tizimlarda qonuniy qilinishi kerak.",
    "design": "Demo rejim: to'liq dizayn maslahati uchun API kalit kerak. Umumiy maslahat: interfeysni sodda, "
              "izchil va foydalanuvchi uchun tushunarli qilib loyihalashtiring.",
    "cloud": "Demo rejim: to'liq javob uchun API kalit kerak. Umumiy maslahat: ishlab chiqishni boshlashdan "
             "oldin arxitekturani diagram orqali rejalashtiring.",
    "tarix": "Demo rejim: IT tarixi bo'yicha to'liq javob uchun API kalit kerak. Qiziqarli fakt: birinchi "
             "kompyuter virusi 'Creeper' 1971-yilda yaratilgan.",
}


def is_ai_configured():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def call_ai_assistant(assistant_type, user_message, history=None):
    """assistant_type: umumiy|kod|cyber|design|cloud|tarix
    Qaytaradi: (reply_text, is_live: bool)
    """
    assistant_type = assistant_type if assistant_type in ASSISTANT_PROMPTS else "umumiy"

    if not is_ai_configured():
        return FALLBACK_REPLIES[assistant_type], False

    try:
        import anthropic
        client = anthropic.Anthropic()
        messages = []
        for h in (history or [])[-8:]:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": user_message})

        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            system=ASSISTANT_PROMPTS[assistant_type],
            messages=messages,
        )
        text_parts = [b.text for b in resp.content if getattr(b, "type", "") == "text"]
        reply = "\n".join(text_parts).strip() or FALLBACK_REPLIES[assistant_type]
        return reply, True
    except Exception as e:
        return f"AI xizmatiga ulanishda xatolik yuz berdi ({type(e).__name__}). Birozdan so'ng qayta urinib ko'ring.", False
