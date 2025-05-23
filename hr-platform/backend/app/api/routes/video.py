from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from fastapi.responses import JSONResponse
from typing import Optional
import os
import uuid
from app.config import settings
from app.db.database import get_db
from sqlalchemy.orm import Session
from app.models.video import VideoInterview

router = APIRouter()

@router.post("/video/upload")
async def upload_video(
    video_file: UploadFile = File(...),
    candidate_id: Optional[int] = Form(None),
    vacancy_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Загрузка видеоинтервью
    
    - **video_file**: Файл видеоинтервью (webm, mp4)
    - **candidate_id**: ID кандидата (опционально)
    - **vacancy_id**: ID вакансии (опционально)
    """
    try:
        # Проверка размера файла (видео обычно больше)
        max_video_size = 50 * 1024 * 1024  # 50MB
        if video_file.size > max_video_size:
            raise HTTPException(status_code=400, detail="Файл видео слишком большой")
        
        # Создаем директорию для видео, если не существует
        video_dir = os.path.join(settings.UPLOAD_DIR, "videos")
        os.makedirs(video_dir, exist_ok=True)
        
        # Генерируем уникальное имя файла
        file_extension = os.path.splitext(video_file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        video_path = os.path.join(video_dir, unique_filename)
        
        # Сохраняем видео
        with open(video_path, "wb") as f:
            content = await video_file.read()
            f.write(content)
        
        # Сохраняем информацию о видео в БД
        video_interview = VideoInterview(
            file_path=video_path,
            candidate_id=candidate_id,
            vacancy_id=vacancy_id,
            original_filename=video_file.filename
        )
        db.add(video_interview)
        db.commit()
        db.refresh(video_interview)
        
        return {
            "status": "success", 
            "message": "Видео успешно загружено", 
            "video_id": video_interview.id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/video/{video_id}")
async def get_video_info(video_id: int, db: Session = Depends(get_db)):
    """Получение информации о видеоинтервью по ID"""
    video = db.query(VideoInterview).filter(VideoInterview.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Видео не найдено")
    
    return {
        "status": "success", 
        "video": {
            "id": video.id,
            "candidate_id": video.candidate_id,
            "vacancy_id": video.vacancy_id,
            "created_at": video.created_at,
            "duration": video.duration,
            "original_filename": video.original_filename
        }
    }
