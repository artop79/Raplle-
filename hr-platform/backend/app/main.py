from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import resume, video, candidates, interview

app = FastAPI(title="HR Platform API", description="API для анализа резюме, видеоинтервью и AI-собеседований")

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Для разработки. В продакшене нужно указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение маршрутов API
app.include_router(resume.router, prefix="/api", tags=["resume"])
app.include_router(video.router, prefix="/api", tags=["video"])
app.include_router(candidates.router, prefix="/api", tags=["candidates"])
app.include_router(interview.router, prefix="/api", tags=["interview"])

@app.get("/")
async def root():
    return {"message": "HR Platform API работает. Документация доступна по адресу /docs"}
