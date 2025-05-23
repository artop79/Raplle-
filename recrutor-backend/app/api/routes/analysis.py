from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import os
from app.database.session import get_db
from app.services.analysis_service import AnalysisService
from app.services.file_service import FileService
from app.services.report_service import ReportService
from app.core.auth import get_current_user

router = APIRouter()
file_service = FileService()

# Сервис анализа должен создаваться для каждого запроса с правильными зависимостями
# Используем функцию для получения сервиса с нужными параметрами
from app.services.openai_service import OpenAIService

def get_analysis_service(db: Session = Depends(get_db)):
    openai_service = OpenAIService()
    return AnalysisService(openai_service, db)
    
def get_report_service(db: Session = Depends(get_db)):
    analysis_service = get_analysis_service(db)
    return ReportService(analysis_service)

@router.post("/compare")
async def compare_resume_with_job(
    background_tasks: BackgroundTasks,
    resume_file: UploadFile = File(...),
    job_description_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Сравнивает резюме с описанием вакансии по загруженным файлам, определяя процент соответствия"""
    
    # Извлекаем текст из файлов
    resume_text = await file_service.extract_text_from_file(resume_file)
    job_description_text = await file_service.extract_text_from_file(job_description_file)
    
    if not resume_text or not job_description_text:
        raise HTTPException(status_code=400, detail="Не удалось извлечь текст из файлов")
    
    # Анализируем с использованием метода для текста
    analysis_service = get_analysis_service(db)
    results = await analysis_service.analyze_resume_text(
        resume_text, 
        job_description_text,
        resume_file.filename,
        job_description_file.filename,
        current_user.id
    )
    
    return {
        "status": "success",
        "results": results
    }

@router.post("/compare-text")
async def compare_resume_text_with_job(
    resume_text: str = Form(...),
    job_description_text: str = Form(...),
    resume_filename: str = Form("resume.txt"),
    job_description_filename: str = Form("job.txt"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Сравнивает текст резюме с описанием вакансии, определяя процент соответствия"""
    
    if not resume_text or not job_description_text:
        raise HTTPException(status_code=400, detail="Текст резюме или описания вакансии отсутствует")
    
    # Анализируем с использованием метода для текста
    analysis_service = get_analysis_service(db)
    results = await analysis_service.analyze_resume_text(
        resume_text, 
        job_description_text,
        resume_filename,
        job_description_filename,
        current_user.id
    )
    
    return {
        "status": "success",
        "results": results
    }

@router.get("/history")
async def get_analysis_history(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Получает историю анализов пользователя из кэша"""
    analysis_service = get_analysis_service(db)
    history = analysis_service.get_analysis_history(db, current_user.id, limit)
    
    return {
        "status": "success",
        "history": history
    }

@router.get("/{analysis_id}")
async def get_analysis_by_id(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Получает результаты конкретного анализа по ID"""
    analysis_service = get_analysis_service(db)
    result = analysis_service.get_analysis_by_id(db, analysis_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Анализ не найден")
    
    # Проверяем, принадлежит ли анализ текущему пользователю
    if result["resume"]["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому анализу")
    
    return {
        "status": "success",
        "analysis": result
    }

@router.post("/clear-cache")
async def clear_old_cache(
    days: int = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Очищает устаревшие записи кэша (только для администраторов)"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Только администраторы могут очищать кэш")
    
    analysis_service = get_analysis_service(db)
    cleared_count = analysis_service.clear_old_cache(db)
    
    return {
        "status": "success",
        "message": f"Очищено {cleared_count} устаревших записей кэша"
    }

@router.get("/generate-pdf-report/{analysis_id}")
async def generate_pdf_report(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    report_service: ReportService = Depends(get_report_service)
):
    """Генерирует PDF-отчет по результатам анализа резюме"""
    # Проверяем, существует ли анализ
    analysis_service = get_analysis_service(db)
    analysis = analysis_service.get_analysis_by_id(db, analysis_id)
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Анализ не найден")
    
    # Проверяем, принадлежит ли анализ текущему пользователю
    if analysis["resume"]["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому анализу")
    
    try:
        # Генерируем PDF отчет
        report_path = report_service.generate_pdf_report(db, analysis_id)
        
        # Возвращаем сгенерированный файл
        return FileResponse(
            path=report_path,
            filename=os.path.basename(report_path),
            media_type="application/pdf"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при генерации отчета: {str(e)}")

@router.get("/generate-excel-report/{analysis_id}")
async def generate_excel_report(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    report_service: ReportService = Depends(get_report_service)
):
    """Генерирует Excel-отчет по результатам анализа резюме"""
    # Проверяем, существует ли анализ
    analysis_service = get_analysis_service(db)
    analysis = analysis_service.get_analysis_by_id(db, analysis_id)
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Анализ не найден")
    
    # Проверяем, принадлежит ли анализ текущему пользователю
    if analysis["resume"]["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому анализу")
    
    try:
        # Генерируем Excel отчет
        report_path = report_service.generate_excel_report(db, analysis_id)
        
        # Возвращаем сгенерированный файл
        return FileResponse(
            path=report_path,
            filename=os.path.basename(report_path),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при генерации отчета: {str(e)}")
