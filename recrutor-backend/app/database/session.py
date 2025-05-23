from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import settings

# Создаем соединение с базой данных
engine = create_engine(settings.DATABASE_URL)

# Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Функция зависимости для FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
