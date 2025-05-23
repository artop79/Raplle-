from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
import uuid
import json
from datetime import datetime

from app.database.session import get_db
from app.core.auth import get_current_active_user
from app.database.models import User
from app.database.hr_models import Vacancy, Interview, InterviewQuestion, InterviewReport, Notification
from app.schemas.hr_schemas import (
    InterviewCreate, InterviewResponse, InterviewDetailResponse,
    InterviewListResponse, InterviewReportResponse, 
    InterviewQuestionCreate, InterviewLinkResponse,
    CandidateInterviewResponse
)
from app.services.zoom_service import ZoomService

router = APIRouter()

@router.post("/", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED)
async def create_interview(
    interview_data: InterviewCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    zoom_service: ZoomService = Depends(ZoomService)
):
    """
    Создание нового интервью для вакансии.
    """
    # Проверяем, существует ли вакансия и принадлежит ли она текущему пользователю
    vacancy = db.query(Vacancy).filter(
        Vacancy.id == interview_data.vacancy_id,
        Vacancy.user_id == current_user.id
    ).first()
    
    if not vacancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вакансия не найдена или у вас нет прав доступа"
        )
    
    # Генерируем уникальную ссылку доступа
    access_link = f"{uuid.uuid4()}"
    
    # Создаем объект интервью
    new_interview = Interview(
        vacancy_id=interview_data.vacancy_id,
        candidate_name=interview_data.candidate_name,
        candidate_email=interview_data.candidate_email,
        status="ожидается",
        access_link=access_link,
        scheduled_at=interview_data.scheduled_at
    )
    
    db.add(new_interview)
    db.commit()
    db.refresh(new_interview)
    
    # Если указано время проведения интервью, планируем Zoom-встречу
    if interview_data.scheduled_at:
        try:
            # Создаем Zoom-встречу в фоновом режиме
            background_tasks.add_task(
                zoom_service.schedule_meeting,
                interview_id=new_interview.id,
                topic=f"Интервью: {vacancy.title}",
                start_time=interview_data.scheduled_at,
                duration=60,  # Длительность по умолчанию - 60 минут
                candidate_email=interview_data.candidate_email
            )
        except Exception as e:
            # Логируем ошибку, но не прерываем создание интервью
            print(f"Error scheduling Zoom meeting: {str(e)}")
    
    # Добавляем вопросы к интервью
    if interview_data.questions:
        for i, question_data in enumerate(interview_data.questions):
            question = InterviewQuestion(
                interview_id=new_interview.id,
                question_text=question_data.question_text,
                order=i + 1,
                category=question_data.category,
                is_required=question_data.is_required
            )
            db.add(question)
    
    # Если тип интервью - smart, генерируем вопросы автоматически
    elif vacancy.interview_type == "smart":
        # В фоновом режиме генерируем вопросы на основе требований вакансии
        background_tasks.add_task(
            generate_smart_interview_questions,
            db=db,
            interview_id=new_interview.id,
            vacancy=vacancy
        )
    
    db.commit()
    
    # Создаем уведомление о создании нового интервью
    notification = Notification(
        user_id=current_user.id,
        title="Создано новое интервью",
        message=f"Создано новое интервью для вакансии {vacancy.title}",
        type="interview_created",
        related_interview_id=new_interview.id,
        related_vacancy_id=vacancy.id
    )
    
    db.add(notification)
    db.commit()
    
    return new_interview

@router.get("/", response_model=InterviewListResponse)
async def get_interviews(
    skip: int = 0,
    limit: int = 100,
    vacancy_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получение списка интервью с возможностью фильтрации.
    """
    # Базовый запрос для получения интервью пользователя
    query = db.query(Interview).join(
        Vacancy, Interview.vacancy_id == Vacancy.id
    ).filter(
        Vacancy.user_id == current_user.id
    )
    
    # Применяем фильтрацию по ID вакансии
    if vacancy_id:
        query = query.filter(Interview.vacancy_id == vacancy_id)
    
    # Применяем фильтрацию по статусу
    if status:
        query = query.filter(Interview.status == status)
    
    # Получаем общее количество интервью
    total = query.count()
    
    # Применяем пагинацию и сортировку
    interviews = query.order_by(Interview.created_at.desc()).offset(skip).limit(limit).all()
    
    # Для каждого интервью добавляем информацию о вакансии
    result = []
    for interview in interviews:
        vacancy = db.query(Vacancy).filter(Vacancy.id == interview.vacancy_id).first()
        
        # Проверяем, есть ли отчет по интервью
        has_report = db.query(InterviewReport).filter(
            InterviewReport.interview_id == interview.id
        ).first() is not None
        
        result.append({
            "id": interview.id,
            "vacancy_id": interview.vacancy_id,
            "vacancy_title": vacancy.title if vacancy else "Неизвестная вакансия",
            "candidate_name": interview.candidate_name,
            "candidate_email": interview.candidate_email,
            "status": interview.status,
            "access_link": interview.access_link,
            "scheduled_at": interview.scheduled_at,
            "completed_at": interview.completed_at,
            "created_at": interview.created_at,
            "has_report": has_report,
            "meeting_id": interview.meeting_id
        })
    
    return {
        "items": result,
        "total": total,
        "skip": skip,
        "limit": limit
    }

@router.get("/{interview_id}", response_model=InterviewDetailResponse)
async def get_interview(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получение детальной информации об интервью.
    """
    # Находим интервью, проверяя доступ
    interview = db.query(Interview).join(
        Vacancy, Interview.vacancy_id == Vacancy.id
    ).filter(
        Interview.id == interview_id,
        Vacancy.user_id == current_user.id
    ).first()
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Интервью не найдено или у вас нет прав доступа"
        )
    
    # Получаем информацию о вакансии
    vacancy = db.query(Vacancy).filter(Vacancy.id == interview.vacancy_id).first()
    
    # Получаем вопросы интервью
    questions = db.query(InterviewQuestion).filter(
        InterviewQuestion.interview_id == interview_id
    ).order_by(InterviewQuestion.order).all()
    
    # Получаем отчет, если он есть
    report = db.query(InterviewReport).filter(
        InterviewReport.interview_id == interview_id
    ).first()
    
    # Формируем детальный ответ
    return {
        "id": interview.id,
        "vacancy_id": interview.vacancy_id,
        "vacancy_title": vacancy.title if vacancy else "Неизвестная вакансия",
        "vacancy_description": vacancy.description if vacancy else "",
        "candidate_name": interview.candidate_name,
        "candidate_email": interview.candidate_email,
        "status": interview.status,
        "access_link": interview.access_link,
        "meeting_id": interview.meeting_id,
        "meeting_password": interview.meeting_password,
        "scheduled_at": interview.scheduled_at,
        "completed_at": interview.completed_at,
        "created_at": interview.created_at,
        "questions": questions,
        "report": report
    }

@router.get("/{interview_id}/report", response_model=InterviewReportResponse)
async def get_interview_report(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получение отчета по интервью.
    """
    # Находим интервью, проверяя доступ
    interview = db.query(Interview).join(
        Vacancy, Interview.vacancy_id == Vacancy.id
    ).filter(
        Interview.id == interview_id,
        Vacancy.user_id == current_user.id
    ).first()
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Интервью не найдено или у вас нет прав доступа"
        )
    
    # Проверяем, завершено ли интервью
    if interview.status != "завершено":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Отчет недоступен - интервью еще не завершено"
        )
    
    # Получаем отчет
    report = db.query(InterviewReport).filter(
        InterviewReport.interview_id == interview_id
    ).first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отчет по интервью не найден"
        )
    
    # Получаем вопросы и ответы
    questions_with_answers = db.query(InterviewQuestion).filter(
        InterviewQuestion.interview_id == interview_id
    ).order_by(InterviewQuestion.order).all()
    
    # Получаем информацию о вакансии
    vacancy = db.query(Vacancy).filter(Vacancy.id == interview.vacancy_id).first()
    
    # Формируем полный отчет
    return {
        "id": report.id,
        "interview_id": report.interview_id,
        "video_url": report.video_url,
        "total_score": report.total_score,
        "analysis_summary": report.analysis_summary,
        "strengths": report.strengths,
        "weaknesses": report.weaknesses,
        "recommendation": report.recommendation,
        "created_at": report.created_at,
        "candidate_name": interview.candidate_name,
        "vacancy_title": vacancy.title if vacancy else "Неизвестная вакансия",
        "questions_and_answers": questions_with_answers
    }

@router.post("/{interview_id}/generate-link", response_model=InterviewLinkResponse)
async def generate_interview_link(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Генерация новой ссылки доступа для интервью.
    """
    # Находим интервью, проверяя доступ
    interview = db.query(Interview).join(
        Vacancy, Interview.vacancy_id == Vacancy.id
    ).filter(
        Interview.id == interview_id,
        Vacancy.user_id == current_user.id
    ).first()
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Интервью не найдено или у вас нет прав доступа"
        )
    
    # Проверяем, не завершено ли уже интервью
    if interview.status == "завершено":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя обновить ссылку для завершенного интервью"
        )
    
    # Генерируем новую ссылку
    new_access_link = f"{uuid.uuid4()}"
    
    # Обновляем ссылку в базе данных
    interview.access_link = new_access_link
    db.commit()
    
    # Формируем полный URL для интервью
    interview_url = f"{interview.access_link}"
    
    return {
        "interview_id": interview.id,
        "access_link": interview.access_link,
        "full_url": interview_url
    }

@router.get("/access/{access_link}", response_model=CandidateInterviewResponse)
async def get_interview_by_link(
    access_link: str,
    db: Session = Depends(get_db)
):
    """
    Получение информации об интервью по уникальной ссылке (для кандидата).
    """
    # Находим интервью по ссылке доступа
    interview = db.query(Interview).filter(
        Interview.access_link == access_link
    ).first()
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Интервью не найдено. Возможно, ссылка недействительна."
        )
    
    # Проверяем статус интервью
    if interview.status == "завершено":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Интервью уже завершено"
        )
    
    # Получаем информацию о вакансии
    vacancy = db.query(Vacancy).filter(Vacancy.id == interview.vacancy_id).first()
    
    # Получаем вопросы (если интервью в процессе)
    questions = []
    if interview.status == "в процессе":
        questions = db.query(InterviewQuestion).filter(
            InterviewQuestion.interview_id == interview.id
        ).order_by(InterviewQuestion.order).all()
    
    # Формируем ответ для кандидата
    return {
        "interview_id": interview.id,
        "vacancy_title": vacancy.title if vacancy else "Неизвестная вакансия",
        "candidate_name": interview.candidate_name,
        "status": interview.status,
        "scheduled_at": interview.scheduled_at,
        "meeting_id": interview.meeting_id,
        "meeting_password": interview.meeting_password,
        "questions": questions if interview.status == "в процессе" else []
    }

@router.post("/access/{access_link}/start")
async def start_interview(
    access_link: str,
    db: Session = Depends(get_db),
    zoom_service: ZoomService = Depends(ZoomService)
):
    """
    Начало интервью кандидатом.
    """
    # Находим интервью по ссылке доступа
    interview = db.query(Interview).filter(
        Interview.access_link == access_link
    ).first()
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Интервью не найдено. Возможно, ссылка недействительна."
        )
    
    # Проверяем, что интервью еще не начато или не завершено
    if interview.status != "ожидается":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Невозможно начать интервью. Текущий статус: {interview.status}"
        )
    
    # Если нет информации о Zoom-встрече, создаем мгновенную встречу
    if not interview.meeting_id:
        try:
            # Получаем информацию о вакансии
            vacancy = db.query(Vacancy).filter(Vacancy.id == interview.vacancy_id).first()
            
            # Создаем Zoom-встречу
            meeting_info = zoom_service.create_instant_meeting(
                topic=f"Интервью: {vacancy.title if vacancy else 'Вакансия'}",
                duration=60
            )
            
            # Обновляем информацию о встрече
            interview.meeting_id = meeting_info.get('id')
            interview.meeting_password = meeting_info.get('password')
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка при создании Zoom-встречи: {str(e)}"
            )
    
    # Обновляем статус интервью
    interview.status = "в процессе"
    db.commit()
    
    # Создаем уведомление о начале интервью
    # Найдем ID HR-менеджера через вакансию
    vacancy = db.query(Vacancy).filter(Vacancy.id == interview.vacancy_id).first()
    
    if vacancy:
        notification = Notification(
            user_id=vacancy.user_id,
            title="Интервью началось",
            message=f"Кандидат {interview.candidate_name or 'Без имени'} начал интервью для вакансии {vacancy.title}",
            type="interview_started",
            related_interview_id=interview.id,
            related_vacancy_id=vacancy.id
        )
        
        db.add(notification)
        db.commit()
    
    # Возвращаем информацию о встрече
    return {
        "interview_id": interview.id,
        "status": interview.status,
        "meeting_id": interview.meeting_id,
        "meeting_password": interview.meeting_password,
        "message": "Интервью успешно начато"
    }

@router.post("/access/{access_link}/complete")
async def complete_interview(
    access_link: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Завершение интервью кандидатом.
    """
    # Находим интервью по ссылке доступа
    interview = db.query(Interview).filter(
        Interview.access_link == access_link
    ).first()
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Интервью не найдено. Возможно, ссылка недействительна."
        )
    
    # Проверяем, что интервью в процессе
    if interview.status != "в процессе":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Невозможно завершить интервью. Текущий статус: {interview.status}"
        )
    
    # Обновляем статус интервью
    interview.status = "завершено"
    interview.completed_at = datetime.utcnow()
    db.commit()
    
    # В фоновом режиме создаем отчет по интервью
    background_tasks.add_task(
        generate_interview_report,
        db=db,
        interview_id=interview.id
    )
    
    # Создаем уведомление о завершении интервью
    # Найдем ID HR-менеджера через вакансию
    vacancy = db.query(Vacancy).filter(Vacancy.id == interview.vacancy_id).first()
    
    if vacancy:
        notification = Notification(
            user_id=vacancy.user_id,
            title="Интервью завершено",
            message=f"Кандидат {interview.candidate_name or 'Без имени'} завершил интервью для вакансии {vacancy.title}",
            type="interview_completed",
            related_interview_id=interview.id,
            related_vacancy_id=vacancy.id
        )
        
        db.add(notification)
        db.commit()
    
    return {
        "interview_id": interview.id,
        "status": interview.status,
        "completed_at": interview.completed_at,
        "message": "Интервью успешно завершено. Отчет будет сгенерирован в ближайшее время."
    }

async def generate_smart_interview_questions(db: Session, interview_id: int, vacancy: Vacancy):
    """
    Фоновая задача для генерации вопросов на основе требований вакансии.
    """
    try:
        # В реальном приложении здесь будет вызов к OpenAI для генерации вопросов
        # Но для MVP мы создадим несколько стандартных вопросов по категориям
        
        # Получаем требования из вакансии
        requirements = vacancy.requirements
        
        # Стандартные вопросы
        standard_questions = [
            {"text": "Расскажите о себе и своем опыте работы.", "category": "general", "order": 1},
            {"text": "Почему вы заинтересованы в этой должности?", "category": "motivation", "order": 2},
            {"text": "Какие у вас есть релевантные навыки для этой позиции?", "category": "skills", "order": 3},
            {"text": "Расскажите о вашем самом успешном проекте.", "category": "experience", "order": 4},
            {"text": "Как вы решаете сложные проблемы в работе?", "category": "problem_solving", "order": 5},
        ]
        
        # Создаем базовые вопросы
        for q in standard_questions:
            question = InterviewQuestion(
                interview_id=interview_id,
                question_text=q["text"],
                order=q["order"],
                category=q["category"],
                is_required=True
            )
            db.add(question)
        
        # Добавляем вопросы на основе требований
        if isinstance(requirements, dict) and "skills" in requirements:
            for i, skill in enumerate(requirements["skills"]):
                question = InterviewQuestion(
                    interview_id=interview_id,
                    question_text=f"Расскажите о вашем опыте работы с {skill}.",
                    order=len(standard_questions) + i + 1,
                    category="skills",
                    is_required=True
                )
                db.add(question)
        
        db.commit()
        
    except Exception as e:
        print(f"Error generating interview questions: {str(e)}")
        # В реальном приложении здесь должна быть запись в журнал ошибок

async def generate_interview_report(db: Session, interview_id: int):
    """
    Фоновая задача для генерации отчета по завершенному интервью.
    """
    try:
        # Получаем информацию об интервью
        interview = db.query(Interview).filter(Interview.id == interview_id).first()
        
        if not interview:
            print(f"Interview {interview_id} not found")
            return
        
        # Получаем вопросы и ответы
        questions = db.query(InterviewQuestion).filter(
            InterviewQuestion.interview_id == interview_id
        ).all()
        
        # В реальном приложении здесь будет обработка записи Zoom и анализ через GPT
        # Для MVP создадим простой отчет
        
        # Создаем отчет с временными данными
        report = InterviewReport(
            interview_id=interview_id,
            video_url="https://example.com/video123",  # Временная ссылка на видео
            total_score=4.2,  # Временная оценка
            analysis_summary="Кандидат показал хорошие знания и навыки, соответствующие требованиям позиции.",
            strengths=json.dumps(["Коммуникабельность", "Технические навыки", "Опыт работы"]),
            weaknesses=json.dumps(["Требуется больше практического опыта"]),
            recommendation="Подходит"
        )
        
        db.add(report)
        db.commit()
        
    except Exception as e:
        print(f"Error generating interview report: {str(e)}")
        # В реальном приложении здесь должна быть запись в журнал ошибок