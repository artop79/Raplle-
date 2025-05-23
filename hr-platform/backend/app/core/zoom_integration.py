"""
Модуль для интеграции с Zoom API
В MVP версии используется заглушка, возвращающая фиктивные данные
"""

import os
import time
import datetime
from app.config import settings

async def create_zoom_meeting(topic, start_time, duration=60, candidate_email=None):
    """
    Создание Zoom встречи для интервью (MVP версия - заглушка)
    
    Args:
        topic: Тема встречи
        start_time: Время начала
        duration: Длительность в минутах
        candidate_email: Email кандидата для приглашения
    
    Returns:
        dict: Информация о созданной встрече
    """
    # Генерируем фиктивные данные для MVP
    meeting_id = f"1234567890_{int(time.time())}"
    join_url = f"https://zoom.us/j/{meeting_id}"
    
    # Конвертируем start_time в строку, если это объект datetime
    if isinstance(start_time, datetime.datetime):
        start_time_str = start_time.isoformat()
    else:
        start_time_str = str(start_time)
    
    # Возвращаем структуру данных, аналогичную ответу Zoom API
    meeting_info = {
        "id": meeting_id,
        "topic": topic,
        "start_time": start_time_str,
        "duration": duration,
        "join_url": join_url,
        "password": "123456",
        "status": "waiting",
    }
    
    # Логируем информацию о создании встречи
    print(f"[MVP] Created Zoom meeting: {meeting_id} for topic: {topic}")
    if candidate_email:
        print(f"[MVP] Would invite {candidate_email} to meeting {meeting_id}")
    
    return meeting_info

async def invite_to_meeting(meeting_id, email):
    """
    Отправка приглашения на встречу (MVP версия - заглушка)
    
    Args:
        meeting_id: ID встречи Zoom
        email: Email приглашаемого участника
    
    Returns:
        dict: Результат операции
    """
    # В реальной реализации здесь будет вызов Zoom API
    print(f"[MVP] Inviting {email} to meeting {meeting_id}")
    
    # Возвращаем фиктивные данные
    return {
        "id": "invite_" + str(int(time.time())),
        "email": email,
        "status": "pending"
    }

async def get_ai_bot_token():
    """
    Получение токена для AI-бота (MVP версия - заглушка)
    В реальной реализации здесь будет логика аутентификации бота
    
    Returns:
        str: Токен для подключения бота к встрече
    """
    # В реальной реализации здесь будет логика получения токена для бота
    return "dummy_bot_token_" + str(int(time.time()))
