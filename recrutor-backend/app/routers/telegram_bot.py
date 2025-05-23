"""
Router для управления Telegram ботом через REST API
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, List, Optional
import json
from pydantic import BaseModel
import asyncio
import os

from ..services.telegram_bot import TelegramBotService, run_bot

router = APIRouter(
    prefix="/api/integrations/telegram",
    tags=["telegram"],
    responses={404: {"description": "Not found"}},
)

# Глобальный экземпляр бота
bot_instance = None

# Модели данных
class TelegramConfig(BaseModel):
    token: str
    webhook_url: Optional[str] = None

class CandidateMessage(BaseModel):
    chat_id: int
    message: str
    reply_markup: Optional[Dict[str, Any]] = None

class InterviewInvitation(BaseModel):
    chat_id: int
    position: str
    company: str
    date_time: str

class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

# Запуск бота в фоновом режиме
async def start_bot_background(token: str, webhook_url: Optional[str] = None):
    import logging
    logging.info(f"Запуск Telegram бота в фоновом режиме...")
    
    global bot_instance
    try:
        # Инициализация сервиса бота
        bot_service = TelegramBotService(token, webhook_url)
        # Настройка и запуск
        setup_success = await bot_service.setup()
        
        if setup_success:
            logging.info("Бот успешно настроен и запущен")
            bot_instance = bot_service
            return bot_service
        else:
            logging.error("Не удалось настроить и запустить бота")
            return None
    except Exception as e:
        logging.error(f"Ошибка при запуске бота: {e}")
        return None

# API маршруты
@router.post("/configure", response_model=ApiResponse)
async def configure_bot(config: TelegramConfig, background_tasks: BackgroundTasks):
    """
    Настройка и запуск Telegram бота
    """
    try:
        global bot_instance
        
        # Проверка токена
        if not config.token or len(config.token.strip()) < 10:
            return {
                "success": False,
                "message": "Некорректный токен Telegram бота. Пожалуйста, проверьте токен.",
                "data": {"status": "error", "error": "invalid_token"}
            }
        
        # Если бот уже запущен, останавливаем его
        if bot_instance and bot_instance.is_running:
            try:
                await bot_instance.stop()
                # Даем немного времени на остановку
                await asyncio.sleep(1)
            except Exception as e:
                import logging
                logging.error(f"Ошибка при остановке предыдущего бота: {e}")
        
        # Запускаем бота напрямую, чтобы убедиться в его работоспособности
        test_bot = TelegramBotService(config.token, config.webhook_url)
        test_setup = await test_bot.setup()
        
        if not test_setup:
            return {
                "success": False,
                "message": "Не удалось настроить Telegram бота. Проверьте токен и сетевое подключение.",
                "data": {"status": "error", "error": "setup_failed"}
            }
            
        await test_bot.stop()
        
        # Запускаем бота в фоновом режиме
        bot_instance = None  # Сбрасываем предыдущий экземпляр
        background_tasks.add_task(start_bot_background, config.token, config.webhook_url)
        
        return {
            "success": True,
            "message": "Telegram бот успешно настроен и запускается",
            "data": {"status": "starting", "token_valid": True}
        }
    except Exception as e:
        import logging
        logging.error(f"Ошибка при настройке Telegram бота: {str(e)}")
        return {
            "success": False,
            "message": f"Ошибка при настройке Telegram бота: {str(e)}",
            "data": {"status": "error", "error": "exception", "details": str(e)}
        }

@router.get("/status", response_model=ApiResponse)
async def get_bot_status():
    """
    Получение статуса Telegram бота
    """
    global bot_instance
    import logging
    
    if not bot_instance:
        logging.info("Запрос статуса: Telegram бот не настроен")
        return {
            "success": True,
            "message": "Telegram бот не настроен",
            "data": {"status": "not_configured"}
        }
    
    # Проверяем активность бота
    is_running = bot_instance.is_running
    
    # Проверяем, что объект application существует
    has_application = hasattr(bot_instance, 'application') and bot_instance.application is not None
    
    # Проверяем токен
    has_token = hasattr(bot_instance, 'token') and bot_instance.token is not None and len(bot_instance.token) > 10
    
    status_details = {
        "status": "running" if is_running else "stopped",
        "webhook_url": getattr(bot_instance, 'webhook_url', None),
        "has_application": has_application,
        "has_token": has_token,
    }
    
    if is_running:
        message = "Бот активен и работает"
    else:
        if has_application and has_token:
            message = "Бот настроен, но не запущен"
        elif has_token:
            message = "Токен бота установлен, но не удалось настроить приложение бота"
        else:
            message = "Бот не настроен полностью"
    
    logging.info(f"Запрос статуса: {message}, детали: {status_details}")
    
    return {
        "success": True,
        "message": message,
        "data": status_details
    }

@router.post("/stop", response_model=ApiResponse)
async def stop_bot():
    """
    Остановка Telegram бота
    """
    global bot_instance
    
    if not bot_instance:
        return {
            "success": False,
            "message": "Telegram бот не настроен",
            "data": {"status": "not_configured"}
        }
    
    if bot_instance.is_running:
        await bot_instance.stop()
        return {
            "success": True,
            "message": "Telegram бот успешно остановлен",
            "data": {"status": "stopped"}
        }
    else:
        return {
            "success": False,
            "message": "Telegram бот уже остановлен",
            "data": {"status": "stopped"}
        }

@router.post("/send-message", response_model=ApiResponse)
async def send_message(message_data: CandidateMessage):
    """
    Отправка сообщения кандидату через Telegram
    """
    global bot_instance
    
    if not bot_instance or not bot_instance.is_running:
        raise HTTPException(status_code=400, detail="Telegram бот не запущен")
    
    try:
        success = await bot_instance.send_message_to_candidate(
            message_data.chat_id,
            message_data.message,
            message_data.reply_markup
        )
        
        if success:
            return {
                "success": True,
                "message": "Сообщение успешно отправлено",
                "data": None
            }
        else:
            return {
                "success": False,
                "message": "Не удалось отправить сообщение",
                "data": None
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при отправке сообщения: {str(e)}")

@router.post("/send-interview-invitation", response_model=ApiResponse)
async def send_invitation(invitation: InterviewInvitation):
    """
    Отправка приглашения на собеседование кандидату через Telegram
    """
    global bot_instance
    
    if not bot_instance or not bot_instance.is_running:
        raise HTTPException(status_code=400, detail="Telegram бот не запущен")
    
    try:
        success = await bot_instance.send_interview_invitation(
            invitation.chat_id,
            invitation.position,
            invitation.company,
            invitation.date_time
        )
        
        if success:
            return {
                "success": True,
                "message": "Приглашение на собеседование успешно отправлено",
                "data": None
            }
        else:
            return {
                "success": False,
                "message": "Не удалось отправить приглашение на собеседование",
                "data": None
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при отправке приглашения: {str(e)}")
