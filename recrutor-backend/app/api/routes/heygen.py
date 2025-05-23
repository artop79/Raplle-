"""
Маршруты API для работы с Heygen видеоаватарами.
"""
from fastapi import APIRouter, HTTPException, Body, Depends
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import json
from app.services.heygen_service import HeygenService

router = APIRouter()

# Модели запросов и ответов
class StreamingSessionRequest(BaseModel):
    """Запрос на создание сессии стриминга"""
    quality: str = "medium"
    video_encoding: str = "VP8"
    stt_provider: str = "deepgram"
    stt_confidence: float = 0.55

class AvatarModel(BaseModel):
    """Модель аватара"""
    avatar_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    preview_url: Optional[str] = None

class StartSessionRequest(BaseModel):
    """Запрос на запуск сессии стриминга"""
    session_id: str
    avatar_id: str

class TextRequest(BaseModel):
    """Запрос на отправку текста аватару"""
    session_id: str
    text: str
    voice_id: Optional[str] = None

class CloseSessionRequest(BaseModel):
    """Запрос на закрытие сессии стриминга"""
    session_id: str

# Зависимость для сервиса Heygen
def get_heygen_service():
    return HeygenService()

@router.post("/streaming/new", response_model=Dict[str, Any])
def create_streaming_session(
    request: StreamingSessionRequest = Body(...),
    heygen_service: HeygenService = Depends(get_heygen_service)
):
    """
    Создает новую сессию стриминга для видеоаватара.
    """
    response = heygen_service.create_streaming_session(
        quality=request.quality,
        video_encoding=request.video_encoding,
        stt_provider=request.stt_provider,
        stt_confidence=request.stt_confidence
    )
    
    if "error" in response:
        raise HTTPException(status_code=400, detail=response["error"])
    
    return response

@router.get("/streaming/avatars", response_model=Dict[str, Any])
def list_streaming_avatars(
    heygen_service: HeygenService = Depends(get_heygen_service)
):
    """
    Получает список доступных аватаров для стриминга.
    """
    response = heygen_service.list_streaming_avatars()
    
    if "error" in response:
        raise HTTPException(status_code=400, detail=response["error"])
    
    return response

@router.post("/streaming/start", response_model=Dict[str, Any])
def start_streaming_session(
    request: StartSessionRequest,
    heygen_service: HeygenService = Depends(get_heygen_service)
):
    """
    Запускает сессию стриминга с выбранным аватаром.
    """
    response = heygen_service.start_streaming_session(
        session_id=request.session_id,
        avatar_id=request.avatar_id
    )
    
    if "error" in response:
        raise HTTPException(status_code=400, detail=response["error"])
    
    return response

@router.post("/streaming/text", response_model=Dict[str, Any])
def send_text_to_avatar(
    request: TextRequest,
    heygen_service: HeygenService = Depends(get_heygen_service)
):
    """
    Отправляет текст для озвучивания аватаром.
    """
    response = heygen_service.send_text_to_avatar(
        session_id=request.session_id,
        text=request.text,
        voice_id=request.voice_id
    )
    
    if "error" in response:
        raise HTTPException(status_code=400, detail=response["error"])
    
    return response

@router.post("/streaming/close", response_model=Dict[str, Any])
def close_streaming_session(
    request: CloseSessionRequest,
    heygen_service: HeygenService = Depends(get_heygen_service)
):
    """
    Закрывает сессию стриминга.
    """
    response = heygen_service.close_streaming_session(
        session_id=request.session_id
    )
    
    if "error" in response:
        raise HTTPException(status_code=400, detail=response["error"])
    
    return response

@router.get("/status", response_model=Dict[str, str])
def check_api_status(heygen_service: HeygenService = Depends(get_heygen_service)):
    """
    Проверяет статус подключения к API Heygen.
    """
    try:
        # Пробуем получить список аватаров для проверки активности API
        heygen_service.list_streaming_avatars()
        return {
            "status": "ok",
            "message": "API Heygen доступно"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"API Heygen недоступно: {str(e)}"
        }

@router.post("/interview/test", response_model=Dict[str, str])
def test_interview_session():
    """
    Тестовый эндпоинт для проверки интеграции с фронтендом.
    """
    return {
        "status": "success",
        "message": "Тестовое подключение к API интервью успешно"
    }
