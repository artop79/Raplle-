"""
Скрипт для создания таблиц HR-моделей в базе данных напрямую через SQLAlchemy.
"""
import os
import sys
from sqlalchemy import create_engine, inspect, text
from app.database.models import Base, User
from app.config import settings
# Импортируем SQLite-совместимые модели
from app.database.sqlite_hr_models import Vacancy, Interview, InterviewQuestion, InterviewAnswer, InterviewReport, Notification, InterviewResult

def create_hr_tables():
    print("Начинаем создание таблиц для HR-моделей...")
    
    # Получаем URL базы данных из настроек
    database_url = getattr(settings, 'DATABASE_URL', None)
    if not database_url:
        database_url = getattr(settings, 'SQLALCHEMY_DATABASE_URI', None)
    
    if not database_url:
        # Если URL не найден в настройках, используем SQLite по умолчанию
        database_url = 'sqlite:///./app.db'
        print(f"URL базы данных не найден в настройках. Используем SQLite: {database_url}")
    
    # Создаем подключение к базе данных
    print(f"Подключаемся к базе данных: {database_url}")
    engine = create_engine(database_url)
    
    try:
        # Создаем таблицы для HR-моделей
        print("Создаем таблицы HR-моделей...")
        
        # Используем инспектор для проверки существующих таблиц
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        print(f"Существующие таблицы: {existing_tables}")
        
        # Проверяем, нужно ли создавать каждую таблицу
        # или вносить изменения, если таблица уже существует
        if 'vacancies' not in existing_tables:
            print("Создаем таблицу 'vacancies'...")
            Vacancy.__table__.create(engine)
        
        if 'interviews' not in existing_tables:
            print("Создаем таблицу 'interviews'...")
            Interview.__table__.create(engine)
        else:
            print("Таблица 'interviews' уже существует. Проверим нужные колонки...")
            # Проверяем наличие необходимых колонок в существующей таблице interviews
            existing_columns = [c['name'] for c in inspector.get_columns('interviews')]
            
            # Список колонок, которые должны быть в таблице interviews
            required_columns = {
                'vacancy_id': 'INTEGER', 
                'candidate_name': 'VARCHAR(255)',
                'candidate_email': 'VARCHAR(255)',
                'access_link': 'VARCHAR(255)'
            }
            
            # Добавляем отсутствующие колонки
            with engine.connect() as conn:
                for col_name, col_type in required_columns.items():
                    if col_name not in existing_columns:
                        print(f"Добавляем колонку '{col_name}' в таблицу 'interviews'...")
                        conn.execute(text(f"ALTER TABLE interviews ADD COLUMN {col_name} {col_type}"))
        
        if 'interview_questions' not in existing_tables:
            print("Создаем таблицу 'interview_questions'...")
            InterviewQuestion.__table__.create(engine)
        
        if 'interview_answers' not in existing_tables:
            print("Создаем таблицу 'interview_answers'...")
            InterviewAnswer.__table__.create(engine)
        
        if 'interview_reports' not in existing_tables:
            print("Создаем таблицу 'interview_reports'...")
            InterviewReport.__table__.create(engine)
        
        if 'notifications' not in existing_tables:
            print("Создаем таблицу 'notifications'...")
            Notification.__table__.create(engine)
            
        print("Таблицы успешно созданы!")
        
    except Exception as e:
        print(f"ОШИБКА при создании таблиц: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    create_hr_tables()
