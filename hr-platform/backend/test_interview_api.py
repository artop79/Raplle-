from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import os
import json
import uuid

# Создаем FastAPI приложение
app = FastAPI(title="HR Platform Interview API", description="API для AI-интервью")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Создаем директорию для загрузки файлов
os.makedirs("uploads", exist_ok=True)

@app.get("/")
async def root():
    return {"message": "Interview API работает. Документация доступна по адресу /docs"}

@app.post("/api/interviews")
async def create_interview(
    title: str = Body(...),
    description: str = Body(...),
    vacancy_id: int = Body(...),
    custom_questions: Optional[List[str]] = Body(None)
):
    """Создание нового интервью"""
    interview_id = str(uuid.uuid4())[:8]
    
    # Базовые вопросы, если не предоставлены пользовательские
    questions = custom_questions or [
        "Расскажите о своем опыте работы в данной области.",
        "Какие ваши сильные стороны?",
        "Почему вы хотите работать именно в нашей компании?",
        "Расскажите о сложном проекте, над которым вы работали.",
        "Какие у вас есть вопросы к нам?"
    ]
    
    return {
        "status": "success", 
        "interview_id": interview_id, 
        "title": title,
        "description": description,
        "vacancy_id": vacancy_id,
        "questions": questions
    }

@app.post("/api/generate_questions")
async def generate_interview_questions(
    job_description: str = Body(...),
    num_questions: int = Body(5)
):
    """
    Генерация вопросов для интервью на основе описания вакансии
    """
    # Базовые вопросы для тестирования
    default_questions = [
        "Расскажите о вашем опыте работы в данной области.",
        "Какие технологии и инструменты вы использовали в последнем проекте?",
        "Расскажите о сложной задаче, которую вы решили, и как вы подошли к её решению.",
        "Как вы справляетесь со стрессовыми ситуациями на работе?",
        "Какие ваши сильные и слабые стороны?",
        "Почему вы считаете себя подходящим кандидатом на эту позицию?",
        "Какие у вас есть вопросы о компании или позиции?"
    ]
    
    # Ограничиваем количество вопросов
    num_questions = min(num_questions, len(default_questions))
    questions = default_questions[:num_questions]
    
    return {"status": "success", "questions": questions}

@app.get("/api/interviews")
async def get_interviews():
    """Получение списка всех интервью"""
    # Тестовые данные для интерфейса
    mockInterviews = [
        {
            "id": 1,
            "title": "Интервью на позицию Frontend-разработчика",
            "description": "Позиция для опытного разработчика со знаниями React и TypeScript",
            "status": "scheduled",
            "zoom_meeting_url": "https://zoom.us/j/123456789",
            "created_at": "2025-05-05T14:30:00",
            "candidates_count": 2,
            "vacancy_id": 1
        },
        {
            "id": 2,
            "title": "Интервью на позицию UX/UI дизайнера",
            "description": "Ищем креативного дизайнера с опытом в Figma и Adobe",
            "status": "created",
            "zoom_meeting_url": None,
            "created_at": "2025-05-06T10:15:00",
            "candidates_count": 0,
            "vacancy_id": 2
        },
        {
            "id": 3,
            "title": "Интервью на позицию Product Manager",
            "description": "Необходим опыт ведения IT-проектов от 3 лет",
            "status": "completed",
            "zoom_meeting_url": "https://zoom.us/j/987654321",
            "created_at": "2025-05-01T16:45:00",
            "candidates_count": 3,
            "vacancy_id": 3
        }
    ]
    
    return {"status": "success", "interviews": mockInterviews}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("test_interview_api:app", host="0.0.0.0", port=8000, reload=True)
