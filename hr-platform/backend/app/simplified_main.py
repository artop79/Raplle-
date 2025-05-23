from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import os
import json
import openai
import shutil
import uuid

# Создаем FastAPI приложение
app = FastAPI(title="HR Platform API", description="API для анализа резюме и видеоинтервью")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Для разработки, в продакшн указать конкретные домены 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Загружаем API ключ из .env
api_key = ""
with open(".env") as f:
    for line in f:
        if line.startswith("OPENAI_API_KEY="):
            api_key = line.strip().split("=", 1)[1]
            break

# Настройка OpenAI
openai.api_key = api_key

# Создаем директории для загрузки файлов
os.makedirs("uploads/resumes", exist_ok=True)
os.makedirs("uploads/videos", exist_ok=True)

@app.get("/")
async def root():
    return {"message": "HR Platform API работает", "docs_url": "/docs"}

@app.post("/api/analyze")
async def analyze_resume(
    resume_file: UploadFile = File(...),
    job_description_file: Optional[UploadFile] = None
):
    """
    Анализ резюме и сравнение с вакансией
    
    - **resume_file**: Файл резюме (PDF/DOCX)
    - **job_description_file**: Файл с описанием вакансии (опционально)
    """
    try:
        # Сохраняем файлы
        resume_path = f"uploads/resumes/{uuid.uuid4()}_{resume_file.filename}"
        with open(resume_path, "wb") as f:
            shutil.copyfileobj(resume_file.file, f)
        
        job_description_text = ""
        if job_description_file:
            job_path = f"uploads/resumes/{uuid.uuid4()}_{job_description_file.filename}"
            with open(job_path, "wb") as f:
                shutil.copyfileobj(job_description_file.file, f)
            job_description_text = f"Файл вакансии: {job_description_file.filename}"
        
        # Формируем запрос к OpenAI
        # Для MVP - просто используем имя файла, в реальном приложении нужно извлекать текст из файла
        prompt = f"""
        Проанализируйте это резюме: {resume_file.filename}
        
        {job_description_text}
        
        Предоставьте анализ в формате JSON с такими полями:
        1. "skills" - массив предполагаемых ключевых навыков кандидата (5-10 навыков)
        2. "experience" - предполагаемый опыт работы 
        3. "education" - предполагаемое образование
        4. "overall_score" - скоринг кандидата от 0 до 100
        5. "strengths" - массив с 3-5 предполагаемыми сильными сторонами
        6. "areas_for_improvement" - области для улучшения
        7. "recommendations" - рекомендации для HR

        Верните только JSON, без дополнительного текста.
        """
        
        # Вызываем OpenAI API
        response = await openai.chat.completions.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Вы HR-аналитик, анализирующий резюме кандидатов и предоставляющий структурированную информацию в формате JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Пытаемся извлечь JSON из ответа
        try:
            # Ищем JSON в ответе
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            
            if start != -1 and end > start:
                json_response = json.loads(response_text[start:end])
            else:
                # Если JSON не найден, возвращаем как строку
                json_response = {"analysis": response_text}
            
            # Добавляем информацию о файле
            json_response["filename"] = resume_file.filename
            
            # Добавляем цветовой код для визуализации
            score = json_response.get("overall_score", 50)
            if score >= 80:
                json_response["color_code"] = "#34d399"  # Зеленый - отлично
            elif score >= 60:
                json_response["color_code"] = "#4361ee"  # Синий - хорошо
            elif score >= 40:
                json_response["color_code"] = "#fbbf24"  # Желтый - средне
            else:
                json_response["color_code"] = "#f87171"  # Красный - плохо
                
            return {"status": "success", "results": json_response}
        except Exception as json_error:
            # В случае ошибки парсинга, возвращаем текстовый ответ
            return {
                "status": "success", 
                "results": {
                    "analysis": response_text,
                    "filename": resume_file.filename
                }
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")

@app.post("/api/video/upload")
async def upload_video(
    video_file: UploadFile = File(...),
    candidate_name: Optional[str] = Form(None)
):
    """
    Загрузка видеоинтервью
    
    - **video_file**: Файл видеоинтервью
    - **candidate_name**: Имя кандидата (опционально)
    """
    try:
        # Сохраняем файл видео
        video_path = f"uploads/videos/{uuid.uuid4()}_{video_file.filename}"
        with open(video_path, "wb") as f:
            shutil.copyfileobj(video_file.file, f)
        
        return {
            "status": "success",
            "message": "Видео успешно загружено",
            "video_info": {
                "filename": video_file.filename,
                "path": video_path,
                "candidate_name": candidate_name,
                "upload_time": str(uuid.uuid1())
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при загрузке видео: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("simplified_main:app", host="0.0.0.0", port=8000, reload=True)
