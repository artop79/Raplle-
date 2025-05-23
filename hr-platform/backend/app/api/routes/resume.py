from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Optional
import os
from app.core.resume_analyzer import ResumeAnalyzer
from app.config import settings
from app.db.database import get_db
from sqlalchemy.orm import Session
from app.models.candidate import Analysis

router = APIRouter()
resume_analyzer = ResumeAnalyzer()

@router.post("/analyze")
async def analyze_resume(
    resume_file: UploadFile = File(...),
    job_description_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    Анализ резюме и сравнение с вакансией
    
    - **resume_file**: Файл резюме (PDF/DOCX)
    - **job_description_file**: Файл с описанием вакансии (опционально)
    """
    try:
        # Проверка размера файла
        if resume_file.size > settings.MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="Файл резюме слишком большой")
        
        if job_description_file and job_description_file.size > settings.MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="Файл вакансии слишком большой")
        
        # Создаем директорию для файлов, если не существует
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        # Сохраняем файлы
        resume_path = os.path.join(settings.UPLOAD_DIR, resume_file.filename)
        with open(resume_path, "wb") as f:
            content = await resume_file.read()
            f.write(content)
        
        job_description_path = None
        if job_description_file:
            job_description_path = os.path.join(settings.UPLOAD_DIR, job_description_file.filename)
            with open(job_description_path, "wb") as f:
                content = await job_description_file.read()
                f.write(content)
        
        # Извлекаем текст из файлов
        resume_text = await resume_analyzer.extract_text_from_pdf(resume_path)
        
        job_description_text = None
        if job_description_path:
            job_description_text = await resume_analyzer.extract_text_from_pdf(job_description_path)
        
        # Анализируем резюме через OpenAI
        result = await resume_analyzer.analyze(resume_text, job_description_text)
        
        # Сохраняем результат анализа в БД
        # В реальном приложении здесь будет более сложная логика
        # для связи с кандидатом и вакансией
        analysis = Analysis(
            analysis_results=result,
            overall_score=result.get("overall_score", 0),
        )
        db.add(analysis)
        db.commit()
        
        return {"status": "success", "results": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analysis/{analysis_id}")
async def get_analysis(analysis_id: int, db: Session = Depends(get_db)):
    """Получение результатов анализа по ID"""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Анализ не найден")
    
    return {"status": "success", "results": analysis.analysis_results}
