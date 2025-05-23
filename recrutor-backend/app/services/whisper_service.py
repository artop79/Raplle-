import os
import tempfile
import logging
from typing import Optional, Dict, Any
import base64

import openai
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

# Настройка логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WhisperService:
    """
    Сервис для преобразования речи в текст с использованием OpenAI Whisper API.
    """
    
    def __init__(self):
        """
        Инициализация сервиса.
        """
        self.api_key = settings.OPENAI_API_KEY
        openai.api_key = self.api_key
        
        # Модель для транскрибации
        self.model = "whisper-1"
        
        # Поддерживаемые форматы файлов
        self.supported_formats = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]
        
        # Максимальный размер файла (25 МБ)
        self.max_file_size = 25 * 1024 * 1024
        
        # Флаг использования мок-данных
        self.mock_mode = settings.MOCK_OPENAI
        
        logger.info(f"WhisperService initialized: mock_mode={self.mock_mode}")
    
    def _check_file_format(self, file_path: str) -> bool:
        """
        Проверяет, поддерживается ли формат файла.
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            True, если формат поддерживается, иначе False
        """
        ext = file_path.split('.')[-1].lower()
        return ext in self.supported_formats
    
    def _check_file_size(self, file_path: str) -> bool:
        """
        Проверяет, не превышает ли размер файла максимально допустимый.
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            True, если размер файла допустим, иначе False
        """
        return os.path.getsize(file_path) <= self.max_file_size
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def transcribe_audio(
        self, 
        audio_file_path: str,
        language: Optional[str] = "ru",
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Преобразует аудиофайл в текст.
        
        Args:
            audio_file_path: Путь к аудиофайлу
            language: Код языка (по умолчанию "ru" для русского)
            prompt: Подсказка для улучшения качества транскрибации
            
        Returns:
            Словарь с результатами транскрибации
        """
        if self.mock_mode:
            return self._mock_transcription()
        
        # Проверяем формат файла
        if not self._check_file_format(audio_file_path):
            logger.error(f"Unsupported file format: {audio_file_path}")
            return {
                "text": "",
                "error": "Неподдерживаемый формат файла."
            }
        
        # Проверяем размер файла
        if not self._check_file_size(audio_file_path):
            logger.error(f"File is too large: {audio_file_path}")
            return {
                "text": "",
                "error": "Файл слишком большой. Максимальный размер: 25 МБ."
            }
        
        try:
            # Открываем файл для чтения в двоичном режиме
            with open(audio_file_path, "rb") as audio_file:
                # Отправляем запрос на транскрибацию
                response = await openai.Audio.atranscribe(
                    model=self.model,
                    file=audio_file,
                    language=language,
                    prompt=prompt
                )
                
                # Возвращаем результат
                return {
                    "text": response.get("text", ""),
                    "language": language
                }
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return {
                "text": "",
                "error": f"Ошибка при транскрибации: {str(e)}"
            }
    
    async def transcribe_base64_audio(
        self, 
        base64_audio: str,
        file_format: str = "mp3",
        language: Optional[str] = "ru",
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Преобразует аудио в формате base64 в текст.
        
        Args:
            base64_audio: Аудио в формате base64
            file_format: Формат файла
            language: Код языка (по умолчанию "ru" для русского)
            prompt: Подсказка для улучшения качества транскрибации
            
        Returns:
            Словарь с результатами транскрибации
        """
        if self.mock_mode:
            return self._mock_transcription()
        
        # Проверяем формат файла
        if file_format.lower() not in self.supported_formats:
            logger.error(f"Unsupported file format: {file_format}")
            return {
                "text": "",
                "error": "Неподдерживаемый формат файла."
            }
        
        try:
            # Декодируем base64
            audio_data = base64.b64decode(base64_audio)
            
            # Проверяем размер данных
            if len(audio_data) > self.max_file_size:
                logger.error("Audio data is too large")
                return {
                    "text": "",
                    "error": "Аудио слишком большое. Максимальный размер: 25 МБ."
                }
            
            # Создаем временный файл
            with tempfile.NamedTemporaryFile(suffix=f".{file_format}", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            try:
                # Транскрибируем аудио из временного файла
                result = await self.transcribe_audio(
                    audio_file_path=temp_file_path,
                    language=language,
                    prompt=prompt
                )
                
                return result
            finally:
                # Удаляем временный файл
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                    
        except Exception as e:
            logger.error(f"Error transcribing base64 audio: {e}")
            return {
                "text": "",
                "error": f"Ошибка при транскрибации: {str(e)}"
            }
    
    def _mock_transcription(self) -> Dict[str, Any]:
        """
        Возвращает мок-ответ для транскрибации.
        
        Returns:
            Словарь с результатами транскрибации
        """
        return {
            "text": "Это тестовый текст транскрибации. В реальном режиме здесь будет расшифровка речи кандидата.",
            "language": "ru"
        }
