# Web Push Notifications — qo'llanma

## Nima bu?

Foydalanuvchi saytdan **chiqib ketgan bo'lsa ham** (brauzer yopiq, lekin qurilma
yoqilgan va internetda), unga muhim bildirishnomalar keladi:

- CODE qo'shilganda (admin/g'azna tomonidan yoki bot orqali)
- Sertifikat tasdiqlanganda/rad etilganda
- ID auksionida g'olib bo'lganda
- Admin e'lon yuborganda

## Qanday ishlaydi

1. Foydalanuvchi saytda "🔔 Ovozli bildirishnomalar" tugmasini bosadi
   (yoki Sozlamalar → "Qurilma bildirishnomalari" → Yoqish)
2. Brauzer ruxsat so'raydi → foydalanuvchi "Allow" bosadi
3. Brauzer push-obunasi yaratiladi va serverga saqlanadi
4. Endi server istalgan vaqtda shu qurilmaga xabar yubora oladi

## VAPID kalitlar

`.env` faylda avtomatik generatsiya qilingan kalitlar bor:

```
VAPID_PUBLIC_KEY=...
VAPID_PRIVATE_KEY=...
VAPID_CLAIM_EMAIL=mailto:webpush@cybershats.uz
```

**Bu kalitlarni o'zgartirmang** — agar o'zgartirsangiz, barcha mavjud obunalar
ishlamay qoladi (foydalanuvchilar qaytadan ruxsat berishi kerak bo'ladi).

## ⚠️ MUHIM CHEKLOV: HTTPS talab qilinadi

Web Push **faqat HTTPS** (yoki `localhost`) ustida ishlaydi — bu brauzer
xavfsizlik talabi, hech qanday айланиб o'tib bo'lmaydi.

- **Lokal test:** `http://localhost:5000` — ishlaydi (brauzer localhost'ni istisno qiladi)
- **Production:** sizning domeningiz **SSL sertifikatga** ega bo'lishi shart
  (Let's Encrypt bepul, yoki hosting provayderingiz SSL beradi)
- Oddiy `http://` (sertifikatsiz) domenda **ishlamaydi**

## iOS cheklovi

- Faqat iOS 16.4+ versiyasida ishlaydi
- Foydalanuvchi saytni "Home Screen"ga qo'shishi kerak bo'lishi mumkin (PWA sifatida)
- Bu Apple'ning o'z cheklovi, bizning kodimiz bilan bog'liq emas

## Texnik fayllar

- `webpush_mod.py` — obuna saqlash/o'chirish, xabar yuborish funksiyalari
- `static/sw.js` — Service Worker (fon rejimida ishlovchi skript)
- `static/js/push-notifications.js` — frontend obuna logikasi
- `push_subscriptions` jadvali — har bir qurilma obunasi

## Sinash

1. Saytga kiring, "🔔" tugmasini bosing, ruxsat bering
2. Sozlamalar → "Sinov xabar yuborish" tugmasini bosing
3. Brauzerni yoping (yoki boshqa tabga o'ting)
4. Bir necha soniyada bildirishnoma kelishi kerak
