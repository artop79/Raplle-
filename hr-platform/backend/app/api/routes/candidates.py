from fastapi import APIRouter, HTTPException, Depends, Form, UploadFile, File
from fastapi.responses import JSONResponse
from typing import Optional, List
from app.db.database import get_db
from sqlalchemy.orm import Session
from app.models.candidate import Candidate, Analysis
import os
from app.config import settings

router = APIRouter()

@router.post("/candidates")
async def create_candidate(
    name: str = Form(...),
    email: str = Form(...),
    phone: Optional[str] = Form(None),
    resume_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    Создание нового кандидата
    
    - **name**: Имя кандидата
    - **email**: Email кандидата
    - **phone**: Телефон кандидата (опционально)
    - **resume_file**: Файл резюме (опционально)
    """
    try:
        # Проверяем, существует ли кандидат с таким email
        existing_candidate = db.query(Candidate).filter(Candidate.email == email).first()
        if existing_candidate:
            raise HTTPException(status_code=400, detail="Кандидат с таким email уже существует")
        
        # Сохраняем резюме, если оно загружено
        resume_path = None
        if resume_file:
            # Создаем директорию для резюме, если не существует
            resume_dir = os.path.join(settings.UPLOAD_DIR, "resumes")
            os.makedirs(resume_dir, exist_ok=True)
            
            # Сохраняем файл
            resume_path = os.path.join(resume_dir, resume_file.filename)
            with open(resume_path, "wb") as f:
                content = await resume_file.read()
                f.write(content)
        
        # Создаем кандидата
        candidate = Candidate(
            name=name,
            email=email,
            phone=phone,
            resume_path=resume_path
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        
        return {
            "status": "success", 
            "message": "Кандидат успешно создан", 
            "candidate_id": candidate.id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/candidates")
async def get_candidates(
    skip: int = 0, 
    limit: int = 100,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Получение списка кандидатов с пагинацией и поиском
    
    - **skip**: Сколько кандидатов пропустить (для пагинации)
    - **limit**: Максимальное количество кандидатов в ответе
    - **search**: Поиск по имени или email
    """
    query = db.query(Candidate)
    
    # Если есть поисковый запрос
    if search:
        query = query.filter(
            (Candidate.name.ilike(f"%{search}%")) | 
            (Candidate.email.ilike(f"%{search}%"))
        )
    
    total = query.count()
    candidates = query.offset(skip).limit(limit).all()
    
    return {
        "status": "success",
        "total": total,
        "candidates": [
            {
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "phone": c.phone,
                "has_resume": bool(c.resume_path),
                "created_at": c.created_at
            } for c in candidates
        ]
    }

@router.get("/candidates/{candidate_id}")
async def get_candidate(candidate_id: int, db: Session = Depends(get_db)):
    """Получение информации о кандидате по ID"""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Кандидат не найден")
    
    # Получаем все анализы этого кандидата
    analyses = db.query(Analysis).filter(Analysis.candidate_id == candidate_id).all()
    
    return {
        "status": "success",
        "candidate": {
            "id": candidate.id,
            "name": candidate.name,
            "email": candidate.email,
            "phone": candidate.phone,
            "has_resume": bool(candidate.resume_path),
            "created_at": candidate.created_at,
            "analyses": [
                {
                    "id": a.id,
                    "analysis_date": a.analysis_date,
                    "overall_score": a.overall_score,
                    "vacancy_id": a.vacancy_id
                } for a in analyses
            ]
        }
    }

@router.delete("/candidates/{candidate_id}")
async def delete_candidate(candidate_id: int, db: Session = Depends(get_db)):
    """Удаление кандидата по ID"""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Кандидат не найден")
    
    # Удаляем файл резюме, если он существует
    if candidate.resume_path and os.path.exists(candidate.resume_path):
        os.remove(candidate.resume_path)
    
    # Удаляем кандидата из БД
    db.delete(candidate)
    db.commit()
    
    return {
        "status": "success",
        "message": "Кандидат успешно удален"
    }
