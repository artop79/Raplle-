"""
Router для HR агента - обеспечивает API для взаимодействия с HR агентом
и управления логикой общения с кандидатами
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from app.services.hr_agent_service import HRAgentService

# Модели запросов и ответов
class CreateConversationRequest(BaseModel):
    candidate_id: str
    vacancy_id: Optional[str] = None
    personality_id: str = "professional"

class MessageRequest(BaseModel):
    message: str

class PersonalityInfo(BaseModel):
    id: str
    name: str
    description: str

class MessageResponse(BaseModel):
    conversation_id: str
    message: str
    next_action: Dict[str, Any]

class ConversationHistoryItem(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None

# Создаем экземпляр сервиса HR агента
hr_agent_service = HRAgentService()

# Создаем маршрутизатор
router = APIRouter(
    prefix="/api/hr-agent",
    tags=["hr-agent"],
    responses={404: {"description": "Not found"}},
)

@router.get("/personalities", response_model=List[PersonalityInfo])
async def get_personalities():
    """
    Получение списка доступных личностей HR агента
    """
    return hr_agent_service.get_available_personalities()

@router.post("/conversations", response_model=Dict[str, str])
async def create_conversation(request: CreateConversationRequest):
    """
    Создание новой беседы с кандидатом
    """
    try:
        conversation_id = hr_agent_service.create_conversation(
            request.candidate_id,
            request.vacancy_id,
            request.personality_id
        )
        return {"conversation_id": conversation_id}
    except Exception as e:
        # Более подробное логирование ошибки
        import logging
        logging.error(f"Error creating conversation: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Не удалось создать беседу: {str(e)}")

@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(conversation_id: str, request: MessageRequest):
    """
    Отправка сообщения HR агенту и получение ответа
    """
    try:
        # Проверяем, существует ли беседа
        conversation = hr_agent_service.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=404, 
                detail=f"Беседа с ID {conversation_id} не найдена"
            )
        
        response = await hr_agent_service.process_candidate_message(conversation_id, request.message)
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        import logging
        logging.error(f"Error processing message: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Ошибка при обработке сообщения: {str(e)}"
        )

@router.get("/conversations/{conversation_id}/history", response_model=List[ConversationHistoryItem])
async def get_conversation_history(conversation_id: str):
    """
    Получение истории сообщений беседы
    """
    try:
        # Проверяем, существует ли беседа
        conversation = hr_agent_service.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=404, 
                detail=f"Беседа с ID {conversation_id} не найдена"
            )
            
        history = hr_agent_service.get_conversation_history(conversation_id)
        return history
    except HTTPException as e:
        raise e
    except Exception as e:
        import logging
        logging.error(f"Error getting conversation history: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Ошибка при получении истории сообщений: {str(e)}"
        )
