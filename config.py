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
