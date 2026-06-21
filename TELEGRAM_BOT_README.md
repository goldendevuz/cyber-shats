# SHATS CYBER Telegram Bot — Ishga tushirish qo'llanmasi

## 1. Bot tokeni

`.env` faylda token mavjud (BotFather'dan olingan):

```
TELEGRAM_BOT_TOKEN=8855072375:AAGxxJltnukGjV0gUTXoEce6OAdoaSnd4uU
```

**⚠️ MUHIM:** Bu token shaxsiy. Hech qachon GitHubga yuklamang, jamoatchi joyga ko'rsatmang.
Agar token oshkor bo'lsa, @BotFather → `/revoke` orqali yangilang.

## 2. Botni ishga tushirish

Web ilovangiz ishlayotgan paytda **alohida terminal**dan:

```bash
python telegram_bot.py
```

Bot uzun polling rejimida ishlaydi (webhook kerakmas).

## 3. Birinchi sinov

1. Telegramda botni qidiring (BotFather sizga username bergan)
2. `/start` yuboring
3. Til tanlang (7 ta variant)
4. "CODE sotib olish" yoki "Kurs sotib olish" tanlang
5. ID raqamingizni kiriting (saytdagi `#XXXXXXX`)
6. Karta orqali to'lang
7. Chek skrinini botga yuboring

## 4. G'aznachi tomonida

- `https://yourdomain/login` orqali kiring: `kassa@shats` / `sha9999ts`
- G'azna panelda **"Bot to'lovlari"** tugmasini bosing
- Yangi so'rovlarni ko'ring, chekni "Ko'rish" tugmasi bilan oching
- Chek to'g'ri bo'lsa **Tasdiqlash** — g'azna jamg'armasidan code chiqariladi/kurs ochiladi
- Chek soxta bo'lsa **rad etish** — sabab yozing

Tasdiq/rad qarori darhol botda foydalanuvchiga xabar qiladi.

## 5. Texnik tafsilotlar

- **Tillar:** uz, ru, en, tr, kk, ky, tj (7 ta)
- **Code paketlari:** 1K, 5K, 10K, 20K, 30K, 50K, 70K, 100K — har 1K=1K so'm
- **Kurslar:** 1-10 ta tanlash mumkin
- **Chek skrini:** Telegram CDN'da saqlanadi (file_id), g'azna panelda ko'rinadi
- **Holat (FSM):** `telegram_users.state` ustunida saqlanadi
- **So'rovlar:** `bot_purchase_requests` jadvalida

## 6. Xavfsizlik

- ID tasdiqlash: faqat saytda mavjud ID raqamlar qabul qilinadi
- Karta raqami botda statik ko'rsatiladi (siz `telegram_bot.py` ichida `PAYMENT_CARDS` ni o'zgartirasiz)
- Chek tasdiqlanmaguncha hech narsa berilmaydi
- Tasdiq paytida g'azna balansi yetarli bo'lishi shart (aks holda rad etiladi)

## 7. Muammolar

- **Bot javob bermayapti:** `python telegram_bot.py` terminalida xato bormi?
- **Token noto'g'ri:** @BotFather → `/mybots` → tokenni qayta oling
- **Chek ko'rinmayapti:** Sayt ishlayotgan kompyuter internetda bo'lishi shart

## 8. Bot funksiyalarini kengaytirish

`telegram_bot.py` faylda quyidagilar bor:
- `TEXTS` — 7 tilning barchasi
- `CODE_PACKAGES` — sotuvga qo'yilgan paketlar
- `PAYMENT_CARDS` — karta raqamlari (siz o'zgartirasiz)
- `handle_text()`, `handle_photo()`, `handle_callback()` — handler'lar
