import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    """Настройки приложения"""
    # API OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "ваш_api_ключ")
    
    # База данных
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./hr_platform.db")
    
    # Настройки файлов
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # Настройки OpenAI
    GPT_MODEL: str = "gpt-3.5-turbo"
    MAX_TOKENS: int = 1500
    
    class Config:
        env_file = ".env"

settings = Settings()
