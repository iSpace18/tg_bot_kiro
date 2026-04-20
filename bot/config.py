from pydantic import BaseModel, field_validator
from typing import List, Optional
import os


class Settings(BaseModel):
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_IDS: List[int] = []
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/bot.db")

    VPN_PANEL_URL: str = os.getenv("VPN_PANEL_URL", "")
    VPN_PANEL_USERNAME: str = os.getenv("VPN_PANEL_USERNAME", "")
    VPN_PANEL_PASSWORD: str = os.getenv("VPN_PANEL_PASSWORD", "")

    TRIAL_DAYS: int = int(os.getenv("TRIAL_DAYS", "3"))
    REFERRAL_BONUS_PERCENT: int = int(os.getenv("REFERRAL_BONUS_PERCENT", "15"))

    YOOKASSA_SHOP_ID: Optional[str] = os.getenv("YOOKASSA_SHOP_ID")
    YOOKASSA_SECRET_KEY: Optional[str] = os.getenv("YOOKASSA_SECRET_KEY")

    WEBHOOK_URL: Optional[str] = os.getenv("WEBHOOK_URL")
    WEBHOOK_PORT: int = int(os.getenv("WEBHOOK_PORT", "8443"))

    def __init__(self):
        super().__init__()
        # Parse ADMIN_IDS from env
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        if admin_ids_str:
            if isinstance(admin_ids_str, str):
                self.ADMIN_IDS = [int(i.strip()) for i in admin_ids_str.replace("[", "").replace("]", "").split(",") if i.strip()]


settings = Settings()
