from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.session import get_db
from app.core.auth import get_current_active_user
from app.database.models import User
from app.database.hr_models import Vacancy, Interview
from app.schemas.hr_schemas import (
    VacancyCreate, VacancyResponse, VacancyUpdate, 
    VacancyListResponse, VacancyDetailResponse,
    VacancyStatsResponse
)

router = APIRouter()

@router.post("/", response_model=VacancyResponse, status_code=status.HTTP_201_CREATED)
async def create_vacancy(
    vacancy: VacancyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Создание новой вакансии.
    """
    db_vacancy = Vacancy(
        title=vacancy.title,
        description=vacancy.description,
        requirements=vacancy.requirements,
        interview_type=vacancy.interview_type,
        evaluation_criteria=vacancy.evaluation_criteria,
        user_id=current_user.id
    )
    
    db.add(db_vacancy)
    db.commit()
    db.refresh(db_vacancy)
    
    return db_vacancy

@router.get("/", response_model=VacancyListResponse)
async def get_vacancies(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получение списка вакансий текущего пользователя с возможностью поиска и фильтрации.
    """
    query = db.query(Vacancy).filter(Vacancy.user_id == current_user.id)
    
    # Применяем фильтр поиска по названию или описанию
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Vacancy.title.ilike(search_term)) | 
            (Vacancy.description.ilike(search_term))
        )
    
    # Применяем фильтр по статусу
    if status:
        if status == "active":
            query = query.filter(Vacancy.is_active == True)
        elif status == "inactive":
            query = query.filter(Vacancy.is_active == False)
    
    # Получаем общее количество вакансий с учетом фильтров
    total = query.count()
    
    # Применяем пагинацию
    vacancies = query.order_by(Vacancy.created_at.desc()).offset(skip).limit(limit).all()
    
    # Для каждой вакансии получаем количество интервью
    result = []
    for vacancy in vacancies:
        interview_count = db.query(func.count(Interview.id)).filter(
            Interview.vacancy_id == vacancy.id
        ).scalar()
        
        completed_interview_count = db.query(func.count(Interview.id)).filter(
            Interview.vacancy_id == vacancy.id,
            Interview.status == "завершено"
        ).scalar()
        
        result.append({
            "id": vacancy.id,
            "title": vacancy.title,
            "description": vacancy.description,
            "requirements": vacancy.requirements,
            "interview_type": vacancy.interview_type,
            "evaluation_criteria": vacancy.evaluation_criteria,
            "is_active": vacancy.is_active,
            "created_at": vacancy.created_at,
            "interview_count": interview_count,
            "completed_interview_count": completed_interview_count
        })
    
    return {
        "items": result,
        "total": total,
        "skip": skip,
        "limit": limit
    }

@router.get("/{vacancy_id}", response_model=VacancyDetailResponse)
async def get_vacancy(
    vacancy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получение детальной информации о вакансии.
    """
    vacancy = db.query(Vacancy).filter(
        Vacancy.id == vacancy_id,
        Vacancy.user_id == current_user.id
    ).first()
    
    if not vacancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вакансия не найдена"
        )
    
    # Получаем статистику по интервью
    interview_count = db.query(func.count(Interview.id)).filter(
        Interview.vacancy_id == vacancy_id
    ).scalar()
    
    completed_interview_count = db.query(func.count(Interview.id)).filter(
        Interview.vacancy_id == vacancy_id,
        Interview.status == "завершено"
    ).scalar()
    
    in_progress_interview_count = db.query(func.count(Interview.id)).filter(
        Interview.vacancy_id == vacancy_id,
        Interview.status == "в процессе"
    ).scalar()
    
    waiting_interview_count = db.query(func.count(Interview.id)).filter(
        Interview.vacancy_id == vacancy_id,
        Interview.status == "ожидается"
    ).scalar()
    
    # Получаем последние 5 интервью
    recent_interviews = db.query(Interview).filter(
        Interview.vacancy_id == vacancy_id
    ).order_by(Interview.created_at.desc()).limit(5).all()
    
    return {
        "id": vacancy.id,
        "title": vacancy.title,
        "description": vacancy.description,
        "requirements": vacancy.requirements,
        "interview_type": vacancy.interview_type,
        "evaluation_criteria": vacancy.evaluation_criteria,
        "is_active": vacancy.is_active,
        "created_at": vacancy.created_at,
        "stats": {
            "interview_count": interview_count,
            "completed_interview_count": completed_interview_count,
            "in_progress_interview_count": in_progress_interview_count,
            "waiting_interview_count": waiting_interview_count
        },
        "recent_interviews": recent_interviews
    }

@router.put("/{vacancy_id}", response_model=VacancyResponse)
async def update_vacancy(
    vacancy_id: int,
    vacancy_update: VacancyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновление информации о вакансии.
    """
    db_vacancy = db.query(Vacancy).filter(
        Vacancy.id == vacancy_id,
        Vacancy.user_id == current_user.id
    ).first()
    
    if not db_vacancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вакансия не найдена"
        )
    
    # Обновляем поля вакансии
    for key, value in vacancy_update.dict(exclude_unset=True).items():
        setattr(db_vacancy, key, value)
    
    db.commit()
    db.refresh(db_vacancy)
    
    return db_vacancy

@router.delete("/{vacancy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vacancy(
    vacancy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Удаление вакансии.
    """
    db_vacancy = db.query(Vacancy).filter(
        Vacancy.id == vacancy_id,
        Vacancy.user_id == current_user.id
    ).first()
    
    if not db_vacancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вакансия не найдена"
        )
    
    db.delete(db_vacancy)
    db.commit()
    
    return None

@router.get("/{vacancy_id}/stats", response_model=VacancyStatsResponse)
async def get_vacancy_stats(
    vacancy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получение статистики по вакансии.
    """
    vacancy = db.query(Vacancy).filter(
        Vacancy.id == vacancy_id,
        Vacancy.user_id == current_user.id
    ).first()
    
    if not vacancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вакансия не найдена"
        )
    
    # Получаем статистику по интервью
    total_interview_count = db.query(func.count(Interview.id)).filter(
        Interview.vacancy_id == vacancy_id
    ).scalar()
    
    completed_interview_count = db.query(func.count(Interview.id)).filter(
        Interview.vacancy_id == vacancy_id,
        Interview.status == "завершено"
    ).scalar()
    
    in_progress_interview_count = db.query(func.count(Interview.id)).filter(
        Interview.vacancy_id == vacancy_id,
        Interview.status == "в процессе"
    ).scalar()
    
    waiting_interview_count = db.query(func.count(Interview.id)).filter(
        Interview.vacancy_id == vacancy_id,
        Interview.status == "ожидается"
    ).scalar()
    
    # Получаем средний балл интервью по этой вакансии
    from app.database.hr_models import InterviewReport
    avg_score = db.query(func.avg(InterviewReport.total_score)).join(
        Interview, InterviewReport.interview_id == Interview.id
    ).filter(
        Interview.vacancy_id == vacancy_id,
        Interview.status == "завершено"
    ).scalar() or 0
    
    # Получаем распределение рекомендаций
    from sqlalchemy import case
    recommendation_stats = db.query(
        InterviewReport.recommendation,
        func.count(InterviewReport.id)
    ).join(
        Interview, InterviewReport.interview_id == Interview.id
    ).filter(
        Interview.vacancy_id == vacancy_id,
        Interview.status == "завершено"
    ).group_by(InterviewReport.recommendation).all()
    
    recommendation_distribution = {
        "recommended": 0,
        "additional_interview": 0,
        "not_recommended": 0
    }
    
    for recommendation, count in recommendation_stats:
        if recommendation == "Подходит":
            recommendation_distribution["recommended"] = count
        elif recommendation == "Требует дополнительного интервью":
            recommendation_distribution["additional_interview"] = count
        elif recommendation == "Не подходит":
            recommendation_distribution["not_recommended"] = count
    
    return {
        "vacancy_id": vacancy_id,
        "title": vacancy.title,
        "interviews": {
            "total": total_interview_count,
            "completed": completed_interview_count,
            "in_progress": in_progress_interview_count,
            "waiting": waiting_interview_count
        },
        "avg_score": float(avg_score),
        "recommendation_distribution": recommendation_distribution
    }
