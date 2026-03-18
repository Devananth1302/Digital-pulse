import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

    # News API
    NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "")

    # App
    APP_ENV: str = os.getenv("APP_ENV", "development")
    SCRAPE_INTERVAL_MINUTES: int = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "15"))
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")

    # Virality weights
    VIRALITY_WEIGHT_SHARES: float = 0.4
    VIRALITY_WEIGHT_COMMENTS: float = 0.3
    VIRALITY_WEIGHT_LIKES: float = 0.2
    VIRALITY_WEIGHT_VELOCITY: float = 0.1

    # Emerging signal thresholds
    EMERGING_GROWTH_RATE_THRESHOLD: float = 1.5  # 150%
    EMERGING_TIME_WINDOW_HOURS: int = 6          # widened: captures enough posts per window


settings = Settings()
