import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    database_url = os.getenv("DATABASE_URL")

    if database_url:
        database_url = database_url.replace(
            "postgres://",
            "postgresql://",
            1,
        )

    SQLALCHEMY_DATABASE_URI = database_url or "sqlite:///iruri.db"

    SQLALCHEMY_TRACK_MODIFICATIONS = False