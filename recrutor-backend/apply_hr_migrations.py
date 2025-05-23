"""
Скрипт для применения миграций HR-моделей к базе данных.
Применяет миграцию из файла app/database/2025_05_07_01_add_hr_models.py
"""
import os
import sys
import importlib.util
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from alembic import op
from app.config import settings

def apply_migration():
    print("Начинаем применение миграций для HR-моделей...")
    
    # Получаем URL базы данных из настроек
    database_url = settings.DATABASE_URL
    if not database_url:
        database_url = settings.SQLALCHEMY_DATABASE_URI
    
    if not database_url:
        print("ОШИБКА: URL базы данных не найден в настройках.")
        sys.exit(1)
    
    # Создаем подключение к базе данных
    engine = create_engine(database_url)
    
    # Импортируем файл миграции
    migration_path = os.path.join('app', 'database', '2025_05_07_01_add_hr_models.py')
    if not os.path.exists(migration_path):
        print(f"ОШИБКА: Файл миграции {migration_path} не найден.")
        sys.exit(1)
    
    spec = importlib.util.spec_from_file_location("migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    
    # Создаем контекст для выполнения миграции
    connection = engine.connect()
    try:
        # Назначаем соединение для операций Alembic
        migration_context = op.get_context()
        if hasattr(migration_context, "configure"):
            migration_context.configure(connection=connection)
        
        # Выполняем миграцию
        print("Выполняем upgrade()...")
        migration.upgrade()
        print("Миграция успешно применена!")
        
    except Exception as e:
        print(f"ОШИБКА при применении миграции: {str(e)}")
        connection.close()
        sys.exit(1)
    finally:
        connection.close()

if __name__ == "__main__":
    apply_migration()
