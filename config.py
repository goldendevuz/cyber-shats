import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "cyber-shats-dev-secret-key-CHANGE-ME")
    DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "database", "cyber_shats.db"))
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    SITE_NAME = "CYBER SHATS"
    SITE_DOMAIN = os.environ.get("SITE_DOMAIN", "cyber.shats.uz")
    BUILD_DATE = "2026-01-01"

    # OAuth
    GOOGLE_CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    GITHUB_CLIENT_ID     = os.environ.get("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "")
    OAUTH_REDIRECT_BASE  = os.environ.get("OAUTH_REDIRECT_BASE", "http://localhost:5000")

    # Telegram bot — code tangalar sotish boti
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    # Bot username (masalan "shats_cyber_bot") - foydalanuvchini botga yo'naltirish uchun
    TELEGRAM_BOT_USERNAME = os.environ.get("TELEGRAM_BOT_USERNAME", "shats_cyber_bot")
    # Admin/g'aznachi xabar olish uchun (ixtiyoriy: yangi sotuv so'rovi haqida xabar)
    TELEGRAM_ADMIN_CHAT_ID = os.environ.get("TELEGRAM_ADMIN_CHAT_ID", "")

    # Web Push Notifications — foydalanuvchi saytdan chiqib ketgan bo'lsa ham
    # qurilmasiga bildirishnoma yuborish (brauzer push, native push emas)
    VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
    VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
    VAPID_CLAIM_EMAIL = os.environ.get("VAPID_CLAIM_EMAIL", "mailto:webpush@localhost")

    # Code tangasi narxlar
    PRO_COST_CODE      = 57_000   # Pro versiya narxi (code)
    COURSE_REWARD_CODE = 100      # Kurs bitirganda beriladigan code
    AI_COST_PER_MSG    = 200      # Har bir AI javob narxi (code)
    PAID_COURSE_CODE   = 10_000   # Pulik kurs narxi (code, standart)

    # Xavfsizlik
    MAX_FAILED_LOGINS  = 5        # Shuncha marta noto'g'ri parol → lock
    LOCK_MINUTES       = 30       # Lock davomiyligi (daqiqa)
    RATE_LIMIT_WINDOW  = 60       # Sekund
    RATE_LIMIT_MAX     = 60       # Oyna ichida maksimal so'rovlar
