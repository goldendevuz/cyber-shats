"""
CYBER SHATS V1.3 — Telegram bot (code tangalar sotuvi)

Ishga tushirish:
    python telegram_bot.py

Bot vazifalari:
1. /start — salomlashish va til tanlash
2. Menu: Code sotib olish | Kurs sotib olish
3. Code paketi (1K-100K) tanlash → ID so'rash → karta + chek skrin
4. Kurs sotib olish (1-10 ta tanlash) → ID so'rash → karta + chek skrin
5. Chek g'aznachiga yuboriladi (sayt orqali tasdiqlanadi)
6. Tasdiqdan keyin: g'azna jamg'armasidan code yoki kurs foydalanuvchiga beriladi

Bot 7 til qo'llab-quvvatlaydi (uz, ru, en, tr, kk, ky, tj).
"""
import os
import json
import time
import sqlite3
import logging
from urllib.parse import quote
import requests

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "database", "cyber_shats.db"))
ADMIN_CHAT_ID = os.environ.get("TELEGRAM_ADMIN_CHAT_ID", "").strip()

API_BASE = f"https://api.telegram.org/bot{TOKEN}"
CODE_TANGA_IMAGE = os.path.join(BASE_DIR, "static", "bot_images", "code_tanga.png")
INSTRUCTIONS_IMAGE = os.path.join(BASE_DIR, "static", "bot_images", "instructions.png")

# Karta raqami va to'lov ma'lumotlari
PAYMENT_CARDS = {
    "uzcard":   "8600 1234 5678 9012",
    "humo":     "9860 1234 5678 9012",
}

# Code paketlari (foydalanuvchi tanlovi uchun)
CODE_PACKAGES = [
    (1_000,   1_000),
    (5_000,   5_000),
    (10_000,  10_000),
    (20_000,  20_000),
    (30_000,  30_000),
    (50_000,  50_000),
    (70_000,  70_000),
    (100_000, 100_000),
]

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("telegram_bot")


# =================================================================
# I18N — 7 til
# =================================================================
TEXTS = {
    "uz": {
        "lang_name": "🇺🇿 O'zbek",
        "welcome_named": "Salom, {name}! 👋\n\n*SHATS CYBER* botiga xush kelibsiz!\n\nBu yerdan siz CODE tangalar va kurslar sotib olishingiz mumkin.",
        "choose_lang": "Iltimos, til tanlang:",
        "lang_set": "Til o'rnatildi: {lang_name}",
        "main_menu": "🏠 *Asosiy menyu*\n\nKerakli xizmatni tanlang:",
        "btn_buy_code": "⚡ CODE sotib olish",
        "btn_buy_course": "📚 Kurs sotib olish",
        "btn_help": "❓ Yordam",
        "btn_change_lang": "🌐 Tilni o'zgartirish",
        "btn_back": "⬅️ Orqaga",
        "btn_main_menu": "🏠 Asosiy menyu",
        "btn_cancel": "❌ Bekor qilish",
        "choose_code_pkg": "💎 *Code paket tanlang*\n\nHar 1000 CODE = 1000 so'm\n\nQuyidagi paketlardan birini tanlang:",
        "code_pkg_format": "⚡ {code:,} CODE — {price:,} so'm",
        "choose_courses_title": "📚 *Kurslar — bir nechtasini tanlashingiz mumkin (1-10 ta)*",
        "course_done": "✅ Tanlash tugadi",
        "course_clear": "🗑 Tanlovni tozalash",
        "selected_courses": "Tanlangan: {n} ta · Jami: {total:,} CODE",
        "max_courses_reached": "Maksimal 10 ta kurs tanlash mumkin.",
        "no_paid_courses": "Hozircha pulli kurslar ro'yxati bo'sh.",
        "no_courses_selected": "Hech qanday kurs tanlanmadi.",
        "ask_id_for_code": "🆔 *Saytdagi ID raqamingizni kiriting*\n\nMasalan: 8520810\n\n(ID profilingizdagi \"Mening ID\" bo'limida ko'rish mumkin)",
        "ask_id_for_course": "🆔 *Saytdagi ID raqamingizni kiriting*\n\nMasalan: 8520810",
        "id_not_found": "❌ Bu ID saytda topilmadi. Iltimos, to'g'ri ID kiriting.",
        "id_invalid": "❌ ID raqami noto'g'ri. Faqat raqam kiriting (masalan: 8520810).",
        "id_confirmed": "✅ ID tasdiqlandi: #{cid}\n👤 Foydalanuvchi: {name}",
        "show_payment_for_code": "💳 *To'lov ma'lumoti*\n\n📦 Buyurtma: ⚡ {code:,} CODE\n💰 Summa: {price:,} so'm\n🆔 ID: #{cid}\n\n*Karta raqami:*\n💳 UZCARD: `{uzcard}`\n💳 HUMO: `{humo}`\n\n👇 To'lovni amalga oshirib, chekning skrinshotini yuboring",
        "show_payment_for_course": "💳 *To'lov ma'lumoti*\n\n📚 Kurslar: {n} ta\n💰 Jami summa: ⚡ {total:,} CODE\n🆔 ID: #{cid}\n\n*Karta raqami:*\n💳 UZCARD: `{uzcard}`\n💳 HUMO: `{humo}`\n\n👇 To'lovni amalga oshirib, chekning skrinshotini yuboring",
        "awaiting_receipt": "📸 Iltimos, *to'lov chekining rasmini* yuboring (faqat rasm qabul qilinadi).",
        "receipt_received": "✅ Chek qabul qilindi!\n\n⏳ Hozir g'aznachi tomonidan tekshiriladi.\n\nNatija tez orada xabar qilinadi. Iltimos kuting...",
        "receipt_not_image": "⚠️ Iltimos, rasm yuboring (fayl emas).",
        "purchase_approved_code": "✅ *Sotib olish tasdiqlandi!*\n\n⚡ {code:,} CODE hisobingizga qo'shildi!\n🆔 ID: #{cid}\n\nRahmat, qaytib kelishingizdan xursandmiz!",
        "purchase_approved_course": "✅ *Sotib olish tasdiqlandi!*\n\n📚 {n} ta kurs hisobingizga qo'shildi!\n🆔 ID: #{cid}\n\nKurslarga kirish: cyber.shats.uz",
        "purchase_rejected": "❌ *Sotib olish rad etildi.*\n\nSabab: {reason}\n\nIltimos, qaytadan urinib ko'ring.",
        "fund_insufficient": "⚠️ G'aznada hozir yetarli CODE yo'q. Iltimos, biroz keyin urinib ko'ring.",
        "help_text": "*SHATS CYBER bot yordami*\n\n🤖 Bu bot orqali siz:\n• CODE tangalar sotib olishingiz\n• Pullik kurslar sotib olishingiz mumkin\n\n📋 *Jarayon:*\n1. Paket/kurs tanlang\n2. Saytdagi ID raqamingizni kiriting\n3. Karta orqali to'lang\n4. Chek skrinini yuboring\n5. G'aznachi tekshirib tasdiqlaydi\n6. CODE/kurslar hisobingizga tushadi\n\n💬 Savol bo'lsa: @shats_cyber_bot",
        "unknown_message": "Tushunmadim. /start orqali asosiy menyuga qayting.",
        "operation_cancelled": "❌ Amal bekor qilindi.",
        "back_to_main": "🏠 Asosiy menyuga qaytdingiz.",
    },
    "ru": {
        "lang_name": "🇷🇺 Русский",
        "welcome_named": "Здравствуйте, {name}! 👋\n\nДобро пожаловать в *SHATS CYBER*!\n\nЗдесь вы можете купить CODE-монеты и курсы.",
        "choose_lang": "Пожалуйста, выберите язык:",
        "lang_set": "Язык установлен: {lang_name}",
        "main_menu": "🏠 *Главное меню*\n\nВыберите услугу:",
        "btn_buy_code": "⚡ Купить CODE",
        "btn_buy_course": "📚 Купить курс",
        "btn_help": "❓ Помощь",
        "btn_change_lang": "🌐 Сменить язык",
        "btn_back": "⬅️ Назад",
        "btn_main_menu": "🏠 Главное меню",
        "btn_cancel": "❌ Отмена",
        "choose_code_pkg": "💎 *Выберите пакет CODE*\n\nКаждые 1000 CODE = 1000 сум\n\nВыберите один из пакетов:",
        "code_pkg_format": "⚡ {code:,} CODE — {price:,} сум",
        "choose_courses_title": "📚 *Курсы — можно выбрать несколько (1-10)*",
        "course_done": "✅ Завершить выбор",
        "course_clear": "🗑 Очистить выбор",
        "selected_courses": "Выбрано: {n} · Итого: {total:,} CODE",
        "max_courses_reached": "Можно выбрать максимум 10 курсов.",
        "no_paid_courses": "Платных курсов пока нет.",
        "no_courses_selected": "Ни одного курса не выбрано.",
        "ask_id_for_code": "🆔 *Введите ваш ID на сайте*\n\nПример: 8520810",
        "ask_id_for_course": "🆔 *Введите ваш ID на сайте*\n\nПример: 8520810",
        "id_not_found": "❌ Этот ID не найден. Введите правильный ID.",
        "id_invalid": "❌ Неверный ID. Введите только цифры.",
        "id_confirmed": "✅ ID подтверждён: #{cid}\n👤 Пользователь: {name}",
        "show_payment_for_code": "💳 *Платёжная информация*\n\n📦 Заказ: ⚡ {code:,} CODE\n💰 Сумма: {price:,} сум\n🆔 ID: #{cid}\n\n*Номер карты:*\n💳 UZCARD: `{uzcard}`\n💳 HUMO: `{humo}`\n\n👇 Оплатите и пришлите скриншот чека",
        "show_payment_for_course": "💳 *Платёжная информация*\n\n📚 Курсов: {n}\n💰 Итого: ⚡ {total:,} CODE\n🆔 ID: #{cid}\n\n*Номер карты:*\n💳 UZCARD: `{uzcard}`\n💳 HUMO: `{humo}`\n\n👇 Оплатите и пришлите скриншот чека",
        "awaiting_receipt": "📸 Пожалуйста, отправьте *скриншот чека* (только изображение).",
        "receipt_received": "✅ Чек получен!\n\n⏳ Сейчас проверяется кассиром.\n\nРезультат скоро придёт. Пожалуйста, подождите...",
        "receipt_not_image": "⚠️ Пожалуйста, отправьте изображение.",
        "purchase_approved_code": "✅ *Покупка подтверждена!*\n\n⚡ {code:,} CODE начислено на ваш счёт!\n🆔 ID: #{cid}",
        "purchase_approved_course": "✅ *Покупка подтверждена!*\n\n📚 {n} курсов добавлены!\n🆔 ID: #{cid}",
        "purchase_rejected": "❌ *Покупка отклонена.*\n\nПричина: {reason}",
        "fund_insufficient": "⚠️ В казне недостаточно CODE. Попробуйте позже.",
        "help_text": "*Помощь SHATS CYBER*\n\n🤖 Бот для покупки CODE и курсов.\n\n📋 *Процесс:*\n1. Выберите пакет\n2. Введите ID на сайте\n3. Оплатите картой\n4. Отправьте скриншот чека\n5. Кассир проверит\n6. CODE/курсы поступят на счёт",
        "unknown_message": "Не понял. Используйте /start.",
        "operation_cancelled": "❌ Отменено.",
        "back_to_main": "🏠 Главное меню.",
    },
    "en": {
        "lang_name": "🇬🇧 English",
        "welcome_named": "Hello, {name}! 👋\n\nWelcome to *SHATS CYBER*!\n\nHere you can buy CODE tokens and courses.",
        "choose_lang": "Please choose a language:",
        "lang_set": "Language set: {lang_name}",
        "main_menu": "🏠 *Main menu*\n\nChoose a service:",
        "btn_buy_code": "⚡ Buy CODE",
        "btn_buy_course": "📚 Buy course",
        "btn_help": "❓ Help",
        "btn_change_lang": "🌐 Change language",
        "btn_back": "⬅️ Back",
        "btn_main_menu": "🏠 Main menu",
        "btn_cancel": "❌ Cancel",
        "choose_code_pkg": "💎 *Choose a CODE package*\n\n1000 CODE = 1000 UZS\n\nPick one:",
        "code_pkg_format": "⚡ {code:,} CODE — {price:,} UZS",
        "choose_courses_title": "📚 *Courses — pick 1-10*",
        "course_done": "✅ Done selecting",
        "course_clear": "🗑 Clear selection",
        "selected_courses": "Selected: {n} · Total: {total:,} CODE",
        "max_courses_reached": "You can pick max 10 courses.",
        "no_paid_courses": "No paid courses yet.",
        "no_courses_selected": "No courses selected.",
        "ask_id_for_code": "🆔 *Enter your site ID*\n\nExample: 8520810",
        "ask_id_for_course": "🆔 *Enter your site ID*\n\nExample: 8520810",
        "id_not_found": "❌ ID not found on the site.",
        "id_invalid": "❌ Invalid ID. Numbers only.",
        "id_confirmed": "✅ ID confirmed: #{cid}\n👤 User: {name}",
        "show_payment_for_code": "💳 *Payment info*\n\n📦 Order: ⚡ {code:,} CODE\n💰 Amount: {price:,} UZS\n🆔 ID: #{cid}\n\n*Cards:*\n💳 UZCARD: `{uzcard}`\n💳 HUMO: `{humo}`\n\n👇 Pay and send the receipt screenshot",
        "show_payment_for_course": "💳 *Payment info*\n\n📚 Courses: {n}\n💰 Total: ⚡ {total:,} CODE\n🆔 ID: #{cid}\n\n*Cards:*\n💳 UZCARD: `{uzcard}`\n💳 HUMO: `{humo}`\n\n👇 Pay and send the receipt screenshot",
        "awaiting_receipt": "📸 Please send the *receipt screenshot* (image only).",
        "receipt_received": "✅ Receipt received!\n\n⏳ Treasurer is reviewing.\n\nYou will be notified shortly.",
        "receipt_not_image": "⚠️ Please send an image.",
        "purchase_approved_code": "✅ *Purchase approved!*\n\n⚡ {code:,} CODE credited to ID #{cid}!",
        "purchase_approved_course": "✅ *Purchase approved!*\n\n📚 {n} courses added to ID #{cid}!",
        "purchase_rejected": "❌ *Purchase rejected.*\n\nReason: {reason}",
        "fund_insufficient": "⚠️ Treasury doesn't have enough CODE. Try later.",
        "help_text": "*SHATS CYBER Bot Help*\n\n🤖 Buy CODE and courses.\n\n📋 *Steps:*\n1. Pick a package\n2. Enter your site ID\n3. Pay by card\n4. Send receipt\n5. Treasurer verifies\n6. CODE/courses delivered",
        "unknown_message": "Use /start.",
        "operation_cancelled": "❌ Cancelled.",
        "back_to_main": "🏠 Back to main.",
    },
    "tr": {
        "lang_name": "🇹🇷 Türkçe",
        "welcome_named": "Merhaba {name}! 👋\n\n*SHATS CYBER*'e hoş geldiniz!\n\nBuradan CODE jeton ve kurs satın alabilirsiniz.",
        "choose_lang": "Lütfen dil seçin:",
        "lang_set": "Dil ayarlandı: {lang_name}",
        "main_menu": "🏠 *Ana menü*",
        "btn_buy_code": "⚡ CODE satın al",
        "btn_buy_course": "📚 Kurs satın al",
        "btn_help": "❓ Yardım",
        "btn_change_lang": "🌐 Dili değiştir",
        "btn_back": "⬅️ Geri",
        "btn_main_menu": "🏠 Ana menü",
        "btn_cancel": "❌ İptal",
        "choose_code_pkg": "💎 *CODE paketi seçin*\n\n1000 CODE = 1000 som",
        "code_pkg_format": "⚡ {code:,} CODE — {price:,} som",
        "choose_courses_title": "📚 *Kurslar — 1-10 tane seçin*",
        "course_done": "✅ Seçimi tamamla",
        "course_clear": "🗑 Temizle",
        "selected_courses": "Seçili: {n} · Toplam: {total:,} CODE",
        "max_courses_reached": "En fazla 10 kurs.",
        "no_paid_courses": "Henüz ücretli kurs yok.",
        "no_courses_selected": "Kurs seçilmedi.",
        "ask_id_for_code": "🆔 *Site ID'nizi girin*\n\nÖrnek: 8520810",
        "ask_id_for_course": "🆔 *Site ID'nizi girin*\n\nÖrnek: 8520810",
        "id_not_found": "❌ ID bulunamadı.",
        "id_invalid": "❌ Geçersiz ID.",
        "id_confirmed": "✅ ID onaylandı: #{cid}\n👤 Kullanıcı: {name}",
        "show_payment_for_code": "💳 *Ödeme*\n\n📦 ⚡ {code:,} CODE\n💰 {price:,} som\n🆔 #{cid}\n\nUZCARD: `{uzcard}`\nHUMO: `{humo}`\n\n👇 Fişin ekran görüntüsünü gönderin",
        "show_payment_for_course": "💳 *Ödeme*\n\n📚 {n} kurs\n💰 ⚡ {total:,} CODE\n🆔 #{cid}\n\nUZCARD: `{uzcard}`\nHUMO: `{humo}`\n\n👇 Fişin ekran görüntüsünü gönderin",
        "awaiting_receipt": "📸 Fiş ekran görüntüsünü gönderin.",
        "receipt_received": "✅ Fiş alındı! ⏳ Kontrol ediliyor.",
        "receipt_not_image": "⚠️ Lütfen resim gönderin.",
        "purchase_approved_code": "✅ *Onaylandı!* ⚡ {code:,} CODE eklendi (#{cid})",
        "purchase_approved_course": "✅ *Onaylandı!* {n} kurs eklendi (#{cid})",
        "purchase_rejected": "❌ Reddedildi: {reason}",
        "fund_insufficient": "⚠️ Hazinede yeterli CODE yok.",
        "help_text": "SHATS CYBER bot — CODE ve kurs satın al.",
        "unknown_message": "/start yazın.",
        "operation_cancelled": "❌ İptal.",
        "back_to_main": "🏠 Ana menü.",
    },
    "kk": {
        "lang_name": "🇰🇿 Қазақ",
        "welcome_named": "Сәлем, {name}! 👋\n\n*SHATS CYBER*-ге қош келдіңіз!",
        "choose_lang": "Тілді таңдаңыз:",
        "lang_set": "Тіл орнатылды: {lang_name}",
        "main_menu": "🏠 *Басты мәзір*",
        "btn_buy_code": "⚡ CODE сатып алу",
        "btn_buy_course": "📚 Курс сатып алу",
        "btn_help": "❓ Көмек",
        "btn_change_lang": "🌐 Тіл",
        "btn_back": "⬅️ Артқа",
        "btn_main_menu": "🏠 Басты мәзір",
        "btn_cancel": "❌ Бас тарту",
        "choose_code_pkg": "💎 *CODE топтаманы таңдаңыз*\n1000 CODE = 1000 сом",
        "code_pkg_format": "⚡ {code:,} CODE — {price:,} сом",
        "choose_courses_title": "📚 *Курстар — 1-10*",
        "course_done": "✅ Дайын",
        "course_clear": "🗑 Тазалау",
        "selected_courses": "Таңдалды: {n} · Барлығы: {total:,} CODE",
        "max_courses_reached": "Барынша 10.",
        "no_paid_courses": "Ақылы курс жоқ.",
        "no_courses_selected": "Курс жоқ.",
        "ask_id_for_code": "🆔 *ID-ні енгізіңіз*\n\nМысал: 8520810",
        "ask_id_for_course": "🆔 *ID-ні енгізіңіз*",
        "id_not_found": "❌ ID табылмады.",
        "id_invalid": "❌ ID қате.",
        "id_confirmed": "✅ ID: #{cid}\n👤 {name}",
        "show_payment_for_code": "💳 *Төлем*\n⚡ {code:,} CODE = {price:,} сом\n🆔 #{cid}\nUZCARD: `{uzcard}`\nHUMO: `{humo}`",
        "show_payment_for_course": "💳 *Төлем*\n📚 {n} курс = ⚡ {total:,} CODE\n🆔 #{cid}\nUZCARD: `{uzcard}`\nHUMO: `{humo}`",
        "awaiting_receipt": "📸 Чек суретін жіберіңіз.",
        "receipt_received": "✅ Қабылданды! ⏳ Тексерілуде.",
        "receipt_not_image": "⚠️ Сурет жіберіңіз.",
        "purchase_approved_code": "✅ Расталды! ⚡ {code:,} CODE (#{cid})",
        "purchase_approved_course": "✅ Расталды! {n} курс (#{cid})",
        "purchase_rejected": "❌ Қабылданбады: {reason}",
        "fund_insufficient": "⚠️ Қазынада жетіспейді.",
        "help_text": "SHATS CYBER бот.",
        "unknown_message": "/start теріңіз.",
        "operation_cancelled": "❌ Бас тартылды.",
        "back_to_main": "🏠 Басты мәзір.",
    },
    "ky": {
        "lang_name": "🇰🇬 Кыргыз",
        "welcome_named": "Салам, {name}! 👋\n\n*SHATS CYBER* кош келиңиз!",
        "choose_lang": "Тил тандаңыз:",
        "lang_set": "Тил: {lang_name}",
        "main_menu": "🏠 *Башкы меню*",
        "btn_buy_code": "⚡ CODE сатып алуу",
        "btn_buy_course": "📚 Курс сатып алуу",
        "btn_help": "❓ Жардам",
        "btn_change_lang": "🌐 Тил",
        "btn_back": "⬅️ Артка",
        "btn_main_menu": "🏠 Башкы",
        "btn_cancel": "❌ Жокко чыгаруу",
        "choose_code_pkg": "💎 *CODE пакет тандаңыз*",
        "code_pkg_format": "⚡ {code:,} CODE — {price:,} сом",
        "choose_courses_title": "📚 *Курстар (1-10)*",
        "course_done": "✅ Бүттү",
        "course_clear": "🗑 Тазалоо",
        "selected_courses": "Тандалды: {n} · Жалпы: {total:,} CODE",
        "max_courses_reached": "Эң көп 10.",
        "no_paid_courses": "Акы курстар жок.",
        "no_courses_selected": "Курс жок.",
        "ask_id_for_code": "🆔 *ID жазыңыз*",
        "ask_id_for_course": "🆔 *ID жазыңыз*",
        "id_not_found": "❌ ID жок.",
        "id_invalid": "❌ ID туура эмес.",
        "id_confirmed": "✅ #{cid} — {name}",
        "show_payment_for_code": "💳 ⚡{code:,} CODE = {price:,} сом · #{cid}\nUZCARD: `{uzcard}`",
        "show_payment_for_course": "💳 📚{n} курс = ⚡{total:,} CODE · #{cid}\nUZCARD: `{uzcard}`",
        "awaiting_receipt": "📸 Чек сүрөтүн жибериңиз.",
        "receipt_received": "✅ Кабыл алынды!",
        "receipt_not_image": "⚠️ Сүрөт жибериңиз.",
        "purchase_approved_code": "✅ Бекитилди! ⚡{code:,} CODE (#{cid})",
        "purchase_approved_course": "✅ Бекитилди! {n} курс (#{cid})",
        "purchase_rejected": "❌ Четке кагылды: {reason}",
        "fund_insufficient": "⚠️ Казынада жетишсиз.",
        "help_text": "SHATS CYBER бот.",
        "unknown_message": "/start.",
        "operation_cancelled": "❌ Жокко чыгарылды.",
        "back_to_main": "🏠 Башкы.",
    },
    "tj": {
        "lang_name": "🇹🇯 Тоҷикӣ",
        "welcome_named": "Салом, {name}! 👋\n\nБа *SHATS CYBER* хуш омадед!",
        "choose_lang": "Забонро интихоб кунед:",
        "lang_set": "Забон: {lang_name}",
        "main_menu": "🏠 *Менюи асосӣ*",
        "btn_buy_code": "⚡ CODE харидан",
        "btn_buy_course": "📚 Курс харидан",
        "btn_help": "❓ Кӯмак",
        "btn_change_lang": "🌐 Забон",
        "btn_back": "⬅️ Қафо",
        "btn_main_menu": "🏠 Меню",
        "btn_cancel": "❌ Бекор",
        "choose_code_pkg": "💎 *Пакети CODE интихоб кунед*",
        "code_pkg_format": "⚡ {code:,} CODE — {price:,} сом",
        "choose_courses_title": "📚 *Курсҳо (1-10)*",
        "course_done": "✅ Тайёр",
        "course_clear": "🗑 Тоза",
        "selected_courses": "Интихобшуда: {n} · Ҷамъ: {total:,} CODE",
        "max_courses_reached": "Максимум 10.",
        "no_paid_courses": "Курсҳои пулакӣ нест.",
        "no_courses_selected": "Курс интихоб нашуд.",
        "ask_id_for_code": "🆔 *ID-ро ворид кунед*",
        "ask_id_for_course": "🆔 *ID-ро ворид кунед*",
        "id_not_found": "❌ ID ёфт нашуд.",
        "id_invalid": "❌ ID нодуруст.",
        "id_confirmed": "✅ #{cid} — {name}",
        "show_payment_for_code": "💳 ⚡{code:,} CODE = {price:,} сом · #{cid}\nUZCARD: `{uzcard}`",
        "show_payment_for_course": "💳 📚{n} = ⚡{total:,} CODE · #{cid}\nUZCARD: `{uzcard}`",
        "awaiting_receipt": "📸 Расми чекро фиристед.",
        "receipt_received": "✅ Қабул шуд!",
        "receipt_not_image": "⚠️ Расм фиристед.",
        "purchase_approved_code": "✅ Тасдиқ шуд! ⚡{code:,} CODE (#{cid})",
        "purchase_approved_course": "✅ Тасдиқ шуд! {n} курс (#{cid})",
        "purchase_rejected": "❌ Рад шуд: {reason}",
        "fund_insufficient": "⚠️ Захира кам.",
        "help_text": "SHATS CYBER bot.",
        "unknown_message": "/start.",
        "operation_cancelled": "❌ Бекор.",
        "back_to_main": "🏠 Меню.",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    """Tarjima olish, fallback uz ga."""
    msg = TEXTS.get(lang, TEXTS["uz"]).get(key, TEXTS["uz"].get(key, key))
    try:
        return msg.format(**kwargs)
    except (KeyError, IndexError):
        return msg


# =================================================================
# DATABASE HELPERS
# =================================================================
def db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_or_create_tg_user(chat_id, first_name="", last_name="", username=""):
    conn = db_conn(); c = conn.cursor()
    row = c.execute("SELECT * FROM telegram_users WHERE chat_id=?", (chat_id,)).fetchone()
    if row:
        c.execute("UPDATE telegram_users SET last_seen_at=datetime('now') WHERE id=?", (row["id"],))
        conn.commit()
        result = dict(row)
        conn.close()
        return result
    c.execute(
        "INSERT INTO telegram_users (chat_id, first_name, last_name, username) VALUES (?,?,?,?)",
        (chat_id, first_name or "", last_name or "", username or "")
    )
    conn.commit()
    tg_id = c.lastrowid
    row = c.execute("SELECT * FROM telegram_users WHERE id=?", (tg_id,)).fetchone()
    conn.close()
    return dict(row)


def set_tg_state(chat_id, state, state_data=None):
    conn = db_conn(); c = conn.cursor()
    data_json = json.dumps(state_data) if state_data is not None else ""
    c.execute("UPDATE telegram_users SET state=?, state_data=? WHERE chat_id=?",
              (state, data_json, chat_id))
    conn.commit(); conn.close()


def get_tg_state(chat_id):
    conn = db_conn(); c = conn.cursor()
    row = c.execute("SELECT state, state_data FROM telegram_users WHERE chat_id=?", (chat_id,)).fetchone()
    conn.close()
    if not row: return ("main", {})
    data = {}
    try:
        if row["state_data"]: data = json.loads(row["state_data"])
    except Exception: pass
    return (row["state"], data)


def set_tg_language(chat_id, lang):
    conn = db_conn(); c = conn.cursor()
    c.execute("UPDATE telegram_users SET language=? WHERE chat_id=?", (lang, chat_id))
    conn.commit(); conn.close()


def find_site_user_by_custom_id(custom_id):
    conn = db_conn(); c = conn.cursor()
    row = c.execute("SELECT id, ism, familiya, custom_id, is_blocked FROM users WHERE custom_id=?",
                    (str(custom_id),)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_paid_courses():
    conn = db_conn(); c = conn.cursor()
    rows = c.execute(
        """SELECT c.id, c.title, c.subtitle, c.code_price, d.name_uz as direction_name
           FROM courses c JOIN directions d ON d.id = c.direction_id
           WHERE c.is_active=1 AND c.code_price > 0
           ORDER BY d.sort_order, c.id"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_purchase_request(chat_id, tg_user_id, request_type,
                            code_amount=0, price_uzs=0, courses_json="",
                            target_custom_id="", site_user_id=None, receipt_file_id=None):
    conn = db_conn(); c = conn.cursor()
    c.execute(
        """INSERT INTO bot_purchase_requests
           (chat_id, tg_user_id, request_type, code_amount, price_uzs, courses_json,
            target_custom_id, site_user_id, receipt_file_id, status)
           VALUES (?,?,?,?,?,?,?,?,?,'pending')""",
        (chat_id, tg_user_id, request_type, code_amount, price_uzs, courses_json,
         target_custom_id, site_user_id, receipt_file_id)
    )
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return rid


# =================================================================
# TELEGRAM API
# =================================================================
def tg_request(method, **payload):
    try:
        r = requests.post(f"{API_BASE}/{method}", json=payload, timeout=30)
        return r.json()
    except Exception as e:
        log.error(f"tg_request error: {e}")
        return {"ok": False, "error": str(e)}


def tg_send_photo(chat_id, photo_path, caption="", reply_markup=None, parse_mode="Markdown"):
    if not os.path.exists(photo_path):
        return tg_request("sendMessage", chat_id=chat_id, text=caption,
                          reply_markup=reply_markup, parse_mode=parse_mode)
    try:
        with open(photo_path, "rb") as f:
            data = {"chat_id": str(chat_id), "caption": caption, "parse_mode": parse_mode}
            if reply_markup:
                data["reply_markup"] = json.dumps(reply_markup)
            r = requests.post(f"{API_BASE}/sendPhoto", data=data, files={"photo": f}, timeout=60)
            return r.json()
    except Exception as e:
        log.error(f"tg_send_photo error: {e}")
        return {"ok": False}


def tg_send_message(chat_id, text, reply_markup=None, parse_mode="Markdown"):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup: payload["reply_markup"] = reply_markup
    return tg_request("sendMessage", **payload)


def tg_answer_callback(callback_id, text="", show_alert=False):
    return tg_request("answerCallbackQuery", callback_query_id=callback_id, text=text, show_alert=show_alert)


# =================================================================
# KEYBOARDS
# =================================================================
def kb_languages():
    return {"inline_keyboard": [
        [{"text": TEXTS["uz"]["lang_name"], "callback_data": "lang:uz"},
         {"text": TEXTS["ru"]["lang_name"], "callback_data": "lang:ru"}],
        [{"text": TEXTS["en"]["lang_name"], "callback_data": "lang:en"},
         {"text": TEXTS["tr"]["lang_name"], "callback_data": "lang:tr"}],
        [{"text": TEXTS["kk"]["lang_name"], "callback_data": "lang:kk"},
         {"text": TEXTS["ky"]["lang_name"], "callback_data": "lang:ky"}],
        [{"text": TEXTS["tj"]["lang_name"], "callback_data": "lang:tj"}],
    ]}


def kb_main_menu(lang):
    return {"inline_keyboard": [
        [{"text": t(lang, "btn_buy_code"), "callback_data": "menu:code"}],
        [{"text": t(lang, "btn_buy_course"), "callback_data": "menu:course"}],
        [{"text": t(lang, "btn_help"), "callback_data": "menu:help"},
         {"text": t(lang, "btn_change_lang"), "callback_data": "menu:lang"}],
    ]}


def kb_code_packages(lang):
    rows = []
    row = []
    for code, price in CODE_PACKAGES:
        row.append({"text": t(lang, "code_pkg_format", code=code, price=price),
                    "callback_data": f"code:{code}:{price}"})
        if len(row) == 1:
            rows.append(row); row = []
    if row: rows.append(row)
    rows.append([{"text": t(lang, "btn_main_menu"), "callback_data": "menu:main"}])
    return {"inline_keyboard": rows}


def kb_courses(lang, courses, selected_ids):
    """Kurslar ro'yxati, har bir kurs uchun toggle tugmasi."""
    rows = []
    for course in courses[:50]:  # cheklov
        marker = "✅" if course["id"] in selected_ids else "🔲"
        title = course["title"]
        if len(title) > 35: title = title[:33] + "..."
        rows.append([{
            "text": f"{marker} {title} — ⚡{course['code_price']:,}",
            "callback_data": f"course:{course['id']}"
        }])
    rows.append([
        {"text": t(lang, "course_clear"), "callback_data": "course_action:clear"},
        {"text": t(lang, "course_done"), "callback_data": "course_action:done"},
    ])
    rows.append([{"text": t(lang, "btn_main_menu"), "callback_data": "menu:main"}])
    return {"inline_keyboard": rows}


def kb_cancel_back(lang):
    return {"inline_keyboard": [
        [{"text": t(lang, "btn_cancel"), "callback_data": "menu:main"}],
    ]}


# =================================================================
# HANDLERS
# =================================================================
def handle_start(chat_id, user):
    tg_user = get_or_create_tg_user(
        chat_id,
        first_name=user.get("first_name", ""),
        last_name=user.get("last_name", ""),
        username=user.get("username", "")
    )
    name = user.get("first_name") or user.get("username") or "Foydalanuvchi"
    lang = tg_user.get("language", "uz")
    set_tg_state(chat_id, "main", {})

    # Salomlashish — til tanlash bosqichi YO'Q, darhol asosiy menyu chiqadi
    welcome = t(lang, "welcome_named", name=name)
    tg_send_message(chat_id, welcome)
    show_main_menu(chat_id, lang)


def show_main_menu(chat_id, lang):
    set_tg_state(chat_id, "main", {})
    tg_send_message(chat_id, t(lang, "main_menu"), reply_markup=kb_main_menu(lang))


def handle_code_menu(chat_id, lang):
    set_tg_state(chat_id, "choose_code", {})
    tg_send_photo(chat_id, CODE_TANGA_IMAGE, caption=t(lang, "choose_code_pkg"),
                  reply_markup=kb_code_packages(lang))


def handle_course_menu(chat_id, lang):
    courses = get_paid_courses()
    if not courses:
        tg_send_message(chat_id, t(lang, "no_paid_courses"), reply_markup=kb_main_menu(lang))
        return
    set_tg_state(chat_id, "choose_courses", {"selected": [], "courses": [c["id"] for c in courses]})
    tg_send_message(chat_id, t(lang, "choose_courses_title"), reply_markup=kb_courses(lang, courses, []))


def handle_callback(callback):
    callback_id = callback["id"]
    chat_id = callback["message"]["chat"]["id"]
    data = callback.get("data", "")
    user_info = callback.get("from", {})
    tg_user = get_or_create_tg_user(chat_id, first_name=user_info.get("first_name", ""),
                                     username=user_info.get("username", ""))
    lang = tg_user.get("language", "uz")
    state, state_data = get_tg_state(chat_id)

    tg_answer_callback(callback_id)

    if data.startswith("lang:"):
        new_lang = data.split(":", 1)[1]
        if new_lang in TEXTS:
            set_tg_language(chat_id, new_lang)
            lang_display_name = TEXTS[new_lang]["lang_name"]
            tg_send_message(chat_id, t(new_lang, "lang_set", lang_name=lang_display_name))
            show_main_menu(chat_id, new_lang)
        return

    if data == "menu:main":
        show_main_menu(chat_id, lang); return
    if data == "menu:code":
        handle_code_menu(chat_id, lang); return
    if data == "menu:course":
        handle_course_menu(chat_id, lang); return
    if data == "menu:lang":
        tg_send_message(chat_id, t(lang, "choose_lang"), reply_markup=kb_languages())
        return
    if data == "menu:help":
        tg_send_message(chat_id, t(lang, "help_text"), reply_markup=kb_main_menu(lang))
        return
        return

    # Code paketi tanlandi
    if data.startswith("code:"):
        parts = data.split(":")
        code_amount = int(parts[1])
        price = int(parts[2])
        set_tg_state(chat_id, "awaiting_id_for_code", {"code": code_amount, "price": price})
        tg_send_message(chat_id, t(lang, "ask_id_for_code"), reply_markup=kb_cancel_back(lang))
        return

    # Kurs tanlash (toggle)
    if data.startswith("course:"):
        cid = int(data.split(":")[1])
        selected = state_data.get("selected", [])
        if cid in selected:
            selected.remove(cid)
        else:
            if len(selected) >= 10:
                tg_answer_callback(callback_id, text=t(lang, "max_courses_reached"), show_alert=True)
                return
            selected.append(cid)
        state_data["selected"] = selected
        set_tg_state(chat_id, "choose_courses", state_data)
        courses = get_paid_courses()
        total = sum(c["code_price"] for c in courses if c["id"] in selected)
        text = (t(lang, "choose_courses_title") + "\n\n" +
                t(lang, "selected_courses", n=len(selected), total=total))
        tg_send_message(chat_id, text, reply_markup=kb_courses(lang, courses, selected))
        return

    if data == "course_action:clear":
        state_data["selected"] = []
        set_tg_state(chat_id, "choose_courses", state_data)
        courses = get_paid_courses()
        tg_send_message(chat_id, t(lang, "choose_courses_title"), reply_markup=kb_courses(lang, courses, []))
        return

    if data == "course_action:done":
        selected = state_data.get("selected", [])
        if not selected:
            tg_answer_callback(callback_id, text=t(lang, "no_courses_selected"), show_alert=True)
            return
        courses = get_paid_courses()
        chosen = [c for c in courses if c["id"] in selected]
        total = sum(c["code_price"] for c in chosen)
        set_tg_state(chat_id, "awaiting_id_for_course",
                     {"courses": [{"id": c["id"], "title": c["title"], "price": c["code_price"]} for c in chosen],
                      "total": total})
        tg_send_message(chat_id, t(lang, "ask_id_for_course"), reply_markup=kb_cancel_back(lang))
        return


def handle_text(chat_id, text, user_info):
    tg_user = get_or_create_tg_user(chat_id, first_name=user_info.get("first_name", ""),
                                     username=user_info.get("username", ""))
    lang = tg_user.get("language", "uz")
    state, state_data = get_tg_state(chat_id)

    if text.strip().startswith("/start"):
        handle_start(chat_id, user_info); return
    if text.strip() == "/help":
        tg_send_message(chat_id, t(lang, "help_text"), reply_markup=kb_main_menu(lang))
        return
    if text.strip() == "/menu":
        show_main_menu(chat_id, lang); return

    # ID kutmoqda (code uchun yoki kurs uchun)
    if state in ("awaiting_id_for_code", "awaiting_id_for_course"):
        cid = text.strip().lstrip("#").strip()
        if not cid.isdigit():
            tg_send_message(chat_id, t(lang, "id_invalid")); return
        site_user = find_site_user_by_custom_id(cid)
        if not site_user:
            tg_send_message(chat_id, t(lang, "id_not_found")); return
        # ID tasdiqlandi
        full_name = f"{site_user['ism']} {site_user.get('familiya','')}".strip()
        tg_send_message(chat_id, t(lang, "id_confirmed", cid=cid, name=full_name))
        # Karta ma'lumotini ko'rsatamiz
        state_data["custom_id"] = cid
        state_data["site_user_id"] = site_user["id"]
        if state == "awaiting_id_for_code":
            msg = t(lang, "show_payment_for_code",
                    code=state_data["code"], price=state_data["price"], cid=cid,
                    uzcard=PAYMENT_CARDS["uzcard"], humo=PAYMENT_CARDS["humo"])
            set_tg_state(chat_id, "awaiting_receipt_code", state_data)
        else:
            msg = t(lang, "show_payment_for_course",
                    n=len(state_data["courses"]), total=state_data["total"], cid=cid,
                    uzcard=PAYMENT_CARDS["uzcard"], humo=PAYMENT_CARDS["humo"])
            set_tg_state(chat_id, "awaiting_receipt_course", state_data)
        tg_send_message(chat_id, msg, reply_markup=kb_cancel_back(lang))
        tg_send_message(chat_id, t(lang, "awaiting_receipt"))
        return

    if state in ("awaiting_receipt_code", "awaiting_receipt_course"):
        tg_send_message(chat_id, t(lang, "receipt_not_image"))
        return

    tg_send_message(chat_id, t(lang, "unknown_message"), reply_markup=kb_main_menu(lang))


def handle_photo(message):
    chat_id = message["chat"]["id"]
    user_info = message.get("from", {})
    tg_user = get_or_create_tg_user(chat_id, first_name=user_info.get("first_name", ""),
                                     username=user_info.get("username", ""))
    lang = tg_user.get("language", "uz")
    state, state_data = get_tg_state(chat_id)
    if state not in ("awaiting_receipt_code", "awaiting_receipt_course"):
        tg_send_message(chat_id, t(lang, "unknown_message"))
        return

    # Eng yuqori sifatli rasm file_id
    photos = message.get("photo", [])
    if not photos:
        tg_send_message(chat_id, t(lang, "receipt_not_image"))
        return
    file_id = photos[-1]["file_id"]

    if state == "awaiting_receipt_code":
        rid = create_purchase_request(
            chat_id=chat_id, tg_user_id=tg_user["id"],
            request_type="code",
            code_amount=state_data.get("code", 0),
            price_uzs=state_data.get("price", 0),
            target_custom_id=state_data.get("custom_id", ""),
            site_user_id=state_data.get("site_user_id"),
            receipt_file_id=file_id
        )
    else:
        rid = create_purchase_request(
            chat_id=chat_id, tg_user_id=tg_user["id"],
            request_type="course",
            courses_json=json.dumps(state_data.get("courses", [])),
            price_uzs=state_data.get("total", 0),
            target_custom_id=state_data.get("custom_id", ""),
            site_user_id=state_data.get("site_user_id"),
            receipt_file_id=file_id
        )
    set_tg_state(chat_id, "main", {})
    tg_send_message(chat_id, t(lang, "receipt_received"), reply_markup=kb_main_menu(lang))

    # Admin chatga xabar (agar sozlangan bo'lsa)
    if ADMIN_CHAT_ID:
        try:
            kind = "💎 CODE" if state == "awaiting_receipt_code" else "📚 KURS"
            note = f"🔔 *Yangi to'lov so'rovi #{rid}*\n\nTip: {kind}\nID: #{state_data.get('custom_id')}\nChat: {chat_id}"
            tg_send_message(int(ADMIN_CHAT_ID), note)
        except Exception as e:
            log.error(f"Admin notify error: {e}")

    log.info(f"Purchase request #{rid} created (chat {chat_id}, state {state})")


def handle_update(update):
    chat_id_for_error = None
    try:
        if "callback_query" in update:
            chat_id_for_error = update["callback_query"]["message"]["chat"]["id"]
            handle_callback(update["callback_query"]); return
        msg = update.get("message")
        if not msg: return
        chat_id = msg["chat"]["id"]
        chat_id_for_error = chat_id
        user_info = msg.get("from", {})
        if "photo" in msg:
            handle_photo(msg); return
        if "text" in msg:
            handle_text(chat_id, msg["text"], user_info); return
    except Exception as e:
        log.exception(f"Error handling update: {e}")
        # Foydalanuvchi "jim qolib" botni tashlab ketmasligi uchun xabar yuboramiz
        if chat_id_for_error:
            try:
                tg_send_message(
                    chat_id_for_error,
                    "⚠️ Texnik xatolik yuz berdi. Iltimos /start buyrug'ini qayta yuboring.",
                    reply_markup=None
                )
            except Exception:
                pass


# =================================================================
# MAIN LOOP — uzun polling
# =================================================================
def main():
    if not TOKEN:
        log.error("TELEGRAM_BOT_TOKEN topilmadi. .env faylga qo'shing!")
        return

    log.info("CYBER SHATS Telegram bot ishga tushdi...")
    # Webhook'ni bekor qilish (agar oldin sozlangan bo'lsa)
    try:
        requests.get(f"{API_BASE}/deleteWebhook", timeout=10)
    except Exception:
        pass

    offset = 0
    while True:
        try:
            r = requests.get(f"{API_BASE}/getUpdates",
                             params={"offset": offset, "timeout": 30}, timeout=40)
            data = r.json()
            if not data.get("ok"):
                log.warning(f"getUpdates not ok: {data}")
                time.sleep(5); continue
            for upd in data.get("result", []):
                offset = upd["update_id"] + 1
                handle_update(upd)
        except KeyboardInterrupt:
            log.info("Bot to'xtatildi (Ctrl+C)")
            break
        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            log.exception(f"Loop error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
