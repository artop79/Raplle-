import json
import time
import requests
import base64
import hmac
import hashlib
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.security import create_jwt
from app.core.logger import logger


class ZoomService:
    """
    Сервис для работы с Zoom API.
    Позволяет создавать и управлять видеовстречами для проведения интервью.
    """

    def __init__(self):
        """
        Инициализация сервиса с настройками из конфигурации.
        """
        self.api_key = settings.ZOOM_API_KEY
        self.api_secret = settings.ZOOM_API_SECRET
        self.base_url = "https://api.zoom.us/v2"
        self.timeout = 30  # Таймаут для API запросов в секундах

    def _generate_token(self) -> str:
        """
        Генерация JWT токена для авторизации в Zoom API.
        """
        payload = {
            "iss": self.api_key,
            "exp": int(time.time() + 3600)  # Токен действителен 1 час
        }
        
        return create_jwt(
            payload=payload,
            secret_key=self.api_secret,
            algorithm="HS256"
        )

    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Общий метод для отправки запросов к Zoom API.
        
        Args:
            method: HTTP метод (GET, POST, PUT, DELETE)
            endpoint: Конечная точка API (без base_url)
            data: Данные для отправки в теле запроса
            params: Параметры запроса
            
        Returns:
            Ответ от API в виде словаря
        """
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self._generate_token()}",
            "Content-Type": "application/json"
        }
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=self.timeout)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=self.timeout)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=self.timeout)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=self.timeout)
            else:
                raise ValueError(f"Неподдерживаемый HTTP метод: {method}")
                
            response.raise_for_status()
            
            if response.status_code == 204:  # No content
                return {}
            
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Ошибка при отправке запроса в Zoom API: {e}")
            
            if hasattr(e, "response") and e.response is not None:
                status_code = e.response.status_code
                try:
                    error_data = e.response.json()
                    logger.error(f"Zoom API ответил с ошибкой {status_code}: {error_data}")
                except ValueError:
                    logger.error(f"Zoom API ответил с ошибкой {status_code}: {e.response.text}")
            
            raise Exception(f"Ошибка при отправке запроса в Zoom API: {e}")

    def create_meeting(
        self,
        topic: str,
        start_time: datetime,
        duration: int,
        description: Optional[str] = None,
        password: Optional[str] = None,
        settings: Optional[Dict] = None
    ) -> Dict:
        """
        Создать новую встречу в Zoom.
        
        Args:
            topic: Тема встречи
            start_time: Время начала встречи
            duration: Продолжительность встречи в минутах
            description: Описание встречи
            password: Пароль для входа во встречу (если None, будет сгенерирован автоматически)
            settings: Дополнительные настройки для встречи
            
        Returns:
            Информация о созданной встрече
        """
        data = {
            "topic": topic,
            "type": 2,  # Scheduled meeting
            "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "duration": duration,
            "timezone": "UTC",
            "agenda": description
        }
        
        if password:
            data["password"] = password
            
        if settings:
            data["settings"] = settings
        else:
            # Настройки по умолчанию
            data["settings"] = {
                "host_video": True,
                "participant_video": True,
                "join_before_host": False,
                "mute_upon_entry": True,
                "waiting_room": True,
                "auto_recording": "cloud"
            }
            
        return self._make_request("POST", "/users/me/meetings", data=data)
    
    def get_meeting(self, meeting_id: str) -> Dict:
        """
        Получить информацию о встрече.
        
        Args:
            meeting_id: Идентификатор встречи
            
        Returns:
            Информация о встрече
        """
        return self._make_request("GET", f"/meetings/{meeting_id}")
    
    def update_meeting(
        self,
        meeting_id: str,
        topic: Optional[str] = None,
        start_time: Optional[datetime] = None,
        duration: Optional[int] = None,
        description: Optional[str] = None,
        password: Optional[str] = None,
        settings: Optional[Dict] = None
    ) -> Dict:
        """
        Обновить информацию о встрече.
        
        Args:
            meeting_id: Идентификатор встречи
            topic: Новая тема встречи
            start_time: Новое время начала встречи
            duration: Новая продолжительность встречи в минутах
            description: Новое описание встречи
            password: Новый пароль для входа во встречу
            settings: Новые настройки для встречи
            
        Returns:
            Информация об обновленной встрече
        """
        data = {}
        
        if topic is not None:
            data["topic"] = topic
            
        if start_time is not None:
            data["start_time"] = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
            
        if duration is not None:
            data["duration"] = duration
            
        if description is not None:
            data["agenda"] = description
            
        if password is not None:
            data["password"] = password
            
        if settings is not None:
            data["settings"] = settings
            
        return self._make_request("PATCH", f"/meetings/{meeting_id}", data=data)
    
    def delete_meeting(self, meeting_id: str) -> None:
        """
        Удалить встречу.
        
        Args:
            meeting_id: Идентификатор встречи
        """
        self._make_request("DELETE", f"/meetings/{meeting_id}")
        
    def list_recordings(
        self,
        user_id: str = "me",
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> Dict:
        """
        Получить список записей для пользователя.
        
        Args:
            user_id: Идентификатор пользователя (по умолчанию текущий пользователь)
            from_date: Начальная дата для поиска записей
            to_date: Конечная дата для поиска записей
            
        Returns:
            Список записей
        """
        params = {}
        
        if from_date:
            params["from"] = from_date.strftime("%Y-%m-%d")
            
        if to_date:
            params["to"] = to_date.strftime("%Y-%m-%d")
            
        return self._make_request("GET", f"/users/{user_id}/recordings", params=params)
    
    def get_meeting_recordings(self, meeting_id: str) -> Dict:
        """
        Получить записи для конкретной встречи.
        
        Args:
            meeting_id: Идентификатор встречи
            
        Returns:
            Информация о записях встречи
        """
        return self._make_request("GET", f"/meetings/{meeting_id}/recordings")
    
    def generate_meeting_join_url(self, meeting_id: str, password: str) -> str:
        """
        Генерирует URL для быстрого присоединения к встрече.
        
        Args:
            meeting_id: Идентификатор встречи
            password: Пароль встречи
            
        Returns:
            URL для присоединения к встрече
        """
        return f"https://zoom.us/j/{meeting_id}?pwd={password}"
    
    def generate_signature(self, meeting_number: str, role: int) -> Dict[str, str]:
        """
        Генерирует подпись для SDK веб-клиента Zoom.
        
        Args:
            meeting_number: Номер встречи
            role: Роль в встрече (0 - участник, 1 - организатор)
            
        Returns:
            Словарь с данными для авторизации в SDK
        """
        timestamp = int(time.time() * 1000) - 30000
        msg = f"{self.api_key}{meeting_number}{timestamp}{role}"
        
        # Создаем HMAC-SHA256 подпись
        hmac_digest = hmac.new(
            self.api_secret.encode(),
            msg.encode(),
            hashlib.sha256
        ).digest()
        
        signature = base64.b64encode(hmac_digest).decode()
        
        return {
            "apiKey": self.api_key,
            "signature": signature,
            "meetingNumber": meeting_number,
            "timestamp": timestamp,
            "role": role
        }
    
    def schedule_interview(
        self,
        candidate_name: str,
        interview_id: int,
        vacancy_title: str,
        start_time: datetime,
        duration: int = 60
    ) -> Dict[str, str]:
        """
        Планирует встречу для интервью и возвращает необходимую информацию.
        
        Args:
            candidate_name: Имя кандидата
            interview_id: Идентификатор интервью
            vacancy_title: Название вакансии
            start_time: Время начала интервью
            duration: Продолжительность в минутах
            
        Returns:
            Словарь с информацией о встрече (meeting_id, password, join_url)
        """
        topic = f"Интервью на вакансию {vacancy_title}"
        description = f"Интервью с кандидатом {candidate_name} (ID: {interview_id})"
        
        # Создаем встречу
        meeting_info = self.create_meeting(
            topic=topic,
            start_time=start_time,
            duration=duration,
            description=description,
            settings={
                "host_video": True,
                "participant_video": True,
                "join_before_host": False,
                "mute_upon_entry": True,
                "waiting_room": True,
                "auto_recording": "cloud"
            }
        )
        
        # Извлекаем нужную информацию
        meeting_id = meeting_info.get("id")
        password = meeting_info.get("password")
        join_url = meeting_info.get("join_url")
        
        return {
            "meeting_id": str(meeting_id),
            "password": password,
            "join_url": join_url
        }
