import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "test_bot_token")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./bek_arena.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super_secret_key")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

settings = Settings()
