import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "test_bot_token")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./bek_arena.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super_secret_key")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    WEBAPP_URL: str = os.getenv("WEBAPP_URL", "https://your-frontend-url.onrender.com")
    # Backup/restore ruxsat berilgan adminlar: ADMIN_IDS="123456,789012"
    ADMIN_IDS: set = {
        int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x.isdigit()
    }
    # initData qancha vaqt (soniya) amal qiladi
    INIT_DATA_MAX_AGE: int = int(os.getenv("INIT_DATA_MAX_AGE", "86400"))

    def validate(self) -> None:
        """Productionda xavfli default qiymatlar bilan ishga tushishni to'xtatadi."""
        if self.ENVIRONMENT != "development":
            if self.BOT_TOKEN == "test_bot_token":
                raise RuntimeError("Productionda BOT_TOKEN o'rnatilishi shart!")
            if self.SECRET_KEY == "super_secret_key":
                raise RuntimeError("Productionda SECRET_KEY o'rnatilishi shart!")


settings = Settings()
settings.validate()
