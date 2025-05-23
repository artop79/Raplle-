import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()  # Загружаем переменные окружения из .env файла

class Settings(BaseSettings):
    # Основные настройки приложения
    PROJECT_NAME: str = "Recrutor API"
    API_V1_STR: str = "/api"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Настройки базы данных
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./test.db")
    
    # Настройки безопасности
    SECRET_KEY: str = os.getenv("SECRET_KEY", "very-secret-key-please-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 дней
    
    # Настройки OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    MOCK_OPENAI: bool = os.getenv("MOCK_OPENAI", "False").lower() == "true"
    
    # Настройки кэширования
    CACHE_EXPIRATION_DAYS: int = int(os.getenv("CACHE_EXPIRATION_DAYS", "30"))
    
    class Config:
        case_sensitive = True

settings = Settings()
