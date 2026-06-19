import os
from decouple import config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    SECRET_KEY = config(
        "SECRET_KEY",
        default="cyber-shats-dev-secret-key-CHANGE-ME"
    )

    DB_PATH = config(
        "DB_PATH",
        default=os.path.join(BASE_DIR, "database", "cyber_shats.db")
    )

    ANTHROPIC_API_KEY = config(
        "ANTHROPIC_API_KEY",
        default=""
    )

    SITE_NAME = "CYBER SHATS"
    SITE_DOMAIN = config(
        "SITE_DOMAIN",
        default="cyber.shats.uz"
    )

    BUILD_DATE = "2026-01-01"

    # OAuth
    GOOGLE_CLIENT_ID = config(
        "GOOGLE_CLIENT_ID",
        default=""
    )

    GOOGLE_CLIENT_SECRET = config(
        "GOOGLE_CLIENT_SECRET",
        default=""
    )

    GITHUB_CLIENT_ID = config(
        "GITHUB_CLIENT_ID",
        default=""
    )

    GITHUB_CLIENT_SECRET = config(
        "GITHUB_CLIENT_SECRET",
        default=""
    )

    OAUTH_REDIRECT_BASE = config(
        "OAUTH_REDIRECT_BASE",
        default="http://localhost:8080"
    )

    # Code tangasi narxlar
    PRO_COST_CODE = 57_000
    COURSE_REWARD_CODE = 100
    AI_COST_PER_MSG = 200
    PAID_COURSE_CODE = 10_000

    # Xavfsizlik
    MAX_FAILED_LOGINS = 5
    LOCK_MINUTES = 30
    RATE_LIMIT_WINDOW = 60
    RATE_LIMIT_MAX = 60
