import os
import logging
import json
import tempfile
import base64
from typing import Optional, Dict, Any, List, Tuple
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

# Настройка логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ElevenLabsService:
    """
    Сервис для преобразования текста в речь с использованием ElevenLabs API.
    """
    
    def __init__(self):
        """
        Инициализация сервиса.
        """
        self.api_key = settings.ELEVENLABS_API_KEY
        self.base_url = "https://api.elevenlabs.io/v1"
        
        # Стандартная модель для синтеза речи
        self.model = "eleven_multilingual_v2"
        
        # Стандартный голос (мужской, русский)
        self.default_voice_id = "pNInz6obpgDQGcFmaJgB"  # Adam (мужской голос)
        
        # Настройки стабильности и схожести
        self.stability = 0.5
        self.similarity_boost = 0.75
        
        # Таймаут для запросов в секундах
        self.timeout = 30
        
        # Флаг использования мок-данных
        self.mock_mode = getattr(settings, "MOCK_ELEVENLABS", False)
        
        logger.info(f"ElevenLabsService initialized: mock_mode={self.mock_mode}")
    
    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        Получает список доступных голосов.
        
        Returns:
            Список голосов
        """
        if self.mock_mode:
            return self._mock_voices()
        
        try:
            # Формируем URL и заголовки
            url = f"{self.base_url}/voices"
            headers = {
                "Accept": "application/json",
                "xi-api-key": self.api_key
            }
            
            # Отправляем запрос
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            # Парсим ответ
            voices_data = response.json()
            return voices_data.get("voices", [])
            
        except Exception as e:
            logger.error(f"Error getting available voices: {e}")
            return []
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_speech(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model: Optional[str] = None,
        stability: Optional[float] = None,
        similarity_boost: Optional[float] = None,
        return_as_base64: bool = False
    ) -> Tuple[bytes, str]:
        """
        Преобразует текст в речь.
        
        Args:
            text: Текст для преобразования
            voice_id: Идентификатор голоса (если None, используется стандартный)
            model: Модель для синтеза (если None, используется стандартная)
            stability: Стабильность голоса (от 0 до 1)
            similarity_boost: Коэффициент схожести (от 0 до 1)
            return_as_base64: Если True, возвращает аудио в формате base64
            
        Returns:
            Кортеж (аудио-данные, MIME-тип)
        """
        if self.mock_mode:
            return self._mock_speech_generation(return_as_base64)
        
        # Используем стандартные значения, если не указаны
        voice_id = voice_id or self.default_voice_id
        model = model or self.model
        stability = stability if stability is not None else self.stability
        similarity_boost = similarity_boost if similarity_boost is not None else self.similarity_boost
        
        try:
            # Формируем URL и заголовки
            url = f"{self.base_url}/text-to-speech/{voice_id}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
            
            # Формируем данные запроса
            request_data = {
                "text": text,
                "model_id": model,
                "voice_settings": {
                    "stability": stability,
                    "similarity_boost": similarity_boost
                }
            }
            
            # Отправляем запрос
            response = requests.post(
                url, 
                headers=headers, 
                json=request_data, 
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Получаем аудио
            audio_data = response.content
            mime_type = "audio/mpeg"
            
            # Если нужно вернуть в формате base64
            if return_as_base64:
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                return audio_base64, mime_type
            
            return audio_data, mime_type
            
        except Exception as e:
            logger.error(f"Error generating speech: {e}")
            
            # Возвращаем пустые данные в случае ошибки
            if return_as_base64:
                return "", "audio/mpeg"
            return b"", "audio/mpeg"
    
    async def save_speech_to_file(
        self,
        text: str,
        output_path: str,
        voice_id: Optional[str] = None,
        model: Optional[str] = None,
        stability: Optional[float] = None,
        similarity_boost: Optional[float] = None
    ) -> str:
        """
        Преобразует текст в речь и сохраняет в файл.
        
        Args:
            text: Текст для преобразования
            output_path: Путь для сохранения файла
            voice_id: Идентификатор голоса (если None, используется стандартный)
            model: Модель для синтеза (если None, используется стандартная)
            stability: Стабильность голоса (от 0 до 1)
            similarity_boost: Коэффициент схожести (от 0 до 1)
            
        Returns:
            Путь к сохраненному файлу или пустая строка в случае ошибки
        """
        try:
            # Генерируем речь
            audio_data, _ = await self.generate_speech(
                text=text,
                voice_id=voice_id,
                model=model,
                stability=stability,
                similarity_boost=similarity_boost,
                return_as_base64=False
            )
            
            # Если данные пустые, возвращаем ошибку
            if not audio_data:
                logger.error("No audio data generated")
                return ""
            
            # Создаем директории, если они не существуют
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            # Сохраняем в файл
            with open(output_path, "wb") as f:
                f.write(audio_data)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error saving speech to file: {e}")
            return ""
    
    def _mock_voices(self) -> List[Dict[str, Any]]:
        """
        Возвращает мок-список голосов.
        
        Returns:
            Список голосов
        """
        return [
            {
                "voice_id": "pNInz6obpgDQGcFmaJgB",
                "name": "Adam",
                "category": "premade",
                "labels": {
                    "gender": "male",
                    "language": "ru"
                }
            },
            {
                "voice_id": "EXAVITQu4vr4xnSDxMaL",
                "name": "Anna",
                "category": "premade",
                "labels": {
                    "gender": "female",
                    "language": "ru"
                }
            }
        ]
    
    def _mock_speech_generation(self, return_as_base64: bool) -> Tuple[bytes, str]:
        """
        Возвращает мок-данные для генерации речи.
        
        Args:
            return_as_base64: Если True, возвращает аудио в формате base64
            
        Returns:
            Кортеж (аудио-данные, MIME-тип)
        """
        # Путь к тестовому аудиофайлу
        mock_audio_path = os.path.join(
            os.path.dirname(__file__), 
            "mock_data", 
            "speech_sample.mp3"
        )
        
        # Если тестовый файл существует, используем его
        if os.path.exists(mock_audio_path):
            with open(mock_audio_path, "rb") as f:
                audio_data = f.read()
        else:
            # Иначе создаем пустой аудиофайл
            logger.warning(f"Mock audio file not found: {mock_audio_path}")
            audio_data = b""
        
        mime_type = "audio/mpeg"
        
        if return_as_base64:
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            return audio_base64, mime_type
        
        return audio_data, mime_type
