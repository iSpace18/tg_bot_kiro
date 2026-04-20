import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from bot.models import Base
from bot.config import settings

os.makedirs("data", exist_ok=True)

# Use regular SQLite engine
engine = create_engine(settings.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    return SessionLocal()
