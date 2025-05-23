from fastapi import APIRouter, Depends, HTTPException, Body
from app.db.database import get_db
from sqlalchemy.orm import Session
from app.models.interview import Interview, InterviewCandidate
from app.models.candidate import Candidate, Vacancy
from typing import List, Optional
import datetime
import json

router = APIRouter()

@router.post("/interviews")
async def create_interview(
    title: str = Body(...),
    description: str = Body(...),
    vacancy_id: int = Body(...),
    custom_questions: Optional[List[str]] = Body(None),
    db: Session = Depends(get_db)
):
    """Создание нового интервью"""
    try:
        # Проверяем существование вакансии
        vacancy = db.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
        if not vacancy:
            raise HTTPException(status_code=404, detail="Вакансия не найдена")
        
        # Базовые вопросы, если не предоставлены пользовательские
        questions = custom_questions or [
            "Расскажите о своем опыте работы в данной области.",
            "Какие ваши сильные стороны?",
            "Почему вы хотите работать именно в нашей компании?",
            "Расскажите о сложном проекте, над которым вы работали.",
            "Какие у вас есть вопросы к нам?"
        ]
        
        # Создаем интервью
        interview = Interview(
            vacancy_id=vacancy_id,
            title=title,
            description=description,
            questions=questions,
            status="created"
        )
        
        db.add(interview)
        db.commit()
        db.refresh(interview)
        
        return {"status": "success", "interview_id": interview.id, "questions": questions}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при создании интервью: {str(e)}")

@router.post("/interviews/{interview_id}/schedule")
async def schedule_interview(
    interview_id: int,
    candidate_id: int = Body(...),
    scheduled_at: str = Body(...),
    db: Session = Depends(get_db)
):
    """Назначение интервью для кандидата"""
    try:
        # Проверяем существование интервью и кандидата
        interview = db.query(Interview).filter(Interview.id == interview_id).first()
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        
        if not interview:
            raise HTTPException(status_code=404, detail="Интервью не найдено")
        if not candidate:
            raise HTTPException(status_code=404, detail="Кандидат не найден")
        
        # Парсим дату и время
        scheduled_datetime = datetime.datetime.fromisoformat(scheduled_at)
        
        # В MVP версии просто создаем запись без интеграции с Zoom
        zoom_meeting_url = f"https://zoom.us/j/dummy_meeting_id_{interview_id}"
        interview.zoom_meeting_id = f"dummy_meeting_id_{interview_id}"
        interview.zoom_meeting_url = zoom_meeting_url
        interview.status = "scheduled"
        
        # Создаем связь кандидата с интервью
        interview_candidate = InterviewCandidate(
            interview_id=interview_id,
            candidate_id=candidate_id,
            scheduled_at=scheduled_datetime
        )
        
        db.add(interview_candidate)
        db.commit()
        
        return {
            "status": "success",
            "interview_url": zoom_meeting_url,
            "scheduled_at": scheduled_at
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при назначении интервью: {str(e)}")

@router.get("/interviews")
async def get_interviews(db: Session = Depends(get_db)):
    """Получение списка всех интервью"""
    interviews = db.query(Interview).all()
    
    result = []
    for interview in interviews:
        result.append({
            "id": interview.id,
            "title": interview.title,
            "description": interview.description,
            "status": interview.status,
            "zoom_meeting_url": interview.zoom_meeting_url,
            "created_at": interview.created_at,
            "vacancy_id": interview.vacancy_id
        })
    
    return {"status": "success", "interviews": result}

@router.get("/interviews/{interview_id}")
async def get_interview(interview_id: int, db: Session = Depends(get_db)):
    """Получение информации об интервью по ID"""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    
    if not interview:
        raise HTTPException(status_code=404, detail="Интервью не найдено")
    
    # Получаем информацию о назначенных кандидатах
    candidates = []
    for ic in interview.candidates:
        candidate = db.query(Candidate).filter(Candidate.id == ic.candidate_id).first()
        candidates.append({
            "id": candidate.id,
            "name": candidate.name,
            "email": candidate.email,
            "scheduled_at": ic.scheduled_at,
            "completed": ic.completed
        })
    
    return {
        "status": "success",
        "interview": {
            "id": interview.id,
            "title": interview.title,
            "description": interview.description,
            "status": interview.status,
            "zoom_meeting_url": interview.zoom_meeting_url,
            "created_at": interview.created_at,
            "vacancy_id": interview.vacancy_id,
            "questions": interview.questions,
            "candidates": candidates
        }
    }

@router.post("/generate_questions")
async def generate_interview_questions(
    job_description: str = Body(...),
    num_questions: int = Body(5)
):
    """
    Генерация вопросов для интервью на основе описания вакансии
    В MVP версии возвращает предустановленные вопросы
    """
    # В полной версии здесь будет вызов OpenAI для генерации вопросов
    # на основе job_description
    
    # Базовые вопросы для MVP
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
