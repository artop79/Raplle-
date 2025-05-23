"""
OpenAI Chat Service - расширение OpenAI сервиса для работы с чатом
"""
from typing import Dict, Any, List, Optional
import hashlib
import json
import logging
import time
from datetime import datetime
import os

import openai
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

# Настройка логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenAIChatService:
    """Сервис для взаимодействия с OpenAI Chat API"""
    
    def __init__(self):
        """Инициализация сервиса OpenAI Chat"""
        self._cache_path = os.path.join(os.path.dirname(__file__), 'chat_cache.json')
        # Попробуем загрузить кэш из файла
        try:
            with open(self._cache_path, 'r', encoding='utf-8') as f:
                self.fixed_responses_cache = json.load(f)
        except Exception:
            self.fixed_responses_cache = {}
            
        self.api_key = settings.OPENAI_API_KEY
        openai.api_key = self.api_key
        
        # Флаг использования мок-данных (можно включить через окружение)
        self.mock_mode = settings.MOCK_OPENAI
        
        # Настройки для чата
        self.chat_settings = {
            "model": "gpt-4o",  # Для максимального качества. Для экономии можно использовать "gpt-4o-mini"
            "temperature": 0.7,  # Немного творчества для чата
            "max_tokens": 1000
        }
        
        # Модель, используемая для чата
        self.model = self.chat_settings["model"]
        
        logger.info(f"OpenAI Chat service initialized: mock_mode={self.mock_mode}, model={self.model}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def call_openai_chat_api(self, messages: List[Dict[str, str]]) -> str:
        """
        Вызывает OpenAI API Chat с возможностью повторных попыток в случае ошибки
        
        Args:
            messages: Список сообщений в формате {"role": "...", "content": "..."}
            
        Returns:
            str: Текст ответа от ассистента
        """
        try:
            start_time = time.time()
            logger.info(f"Calling OpenAI API Chat with model: {self.model}")
            
            # Проверка на мок-режим
            if self.mock_mode:
                # В мок-режиме возвращаем заготовленный ответ
                # Создаем хеш для детерминированности ответов
                messages_str = json.dumps([msg["content"] for msg in messages], ensure_ascii=False)
                messages_hash = hashlib.md5(messages_str.encode('utf-8')).hexdigest()
                
                # Проверяем кеш детерминированных ответов
                if messages_hash in self.fixed_responses_cache:
                    logger.info(f"Using cached response for hash: {messages_hash}")
                    return self.fixed_responses_cache[messages_hash]
                
                # Если нет в кеше, генерируем заготовленный ответ
                mock_responses = [
                    "Спасибо за ваше сообщение! Я рассмотрел вашу кандидатуру и хотел бы узнать больше о вашем опыте. Какие проекты вы реализовывали на предыдущем месте работы?",
                    "Благодарю за информацию. На данный момент мы ищем кандидатов с опытом работы в команде. Расскажите, пожалуйста, о вашем опыте командной работы.",
                    "Отлично! Наша компания заинтересована в вашей кандидатуре. Когда вам было бы удобно провести собеседование?",
                    "Ваше резюме выглядит впечатляюще. Я бы хотел обсудить возможность вашего трудоустройства. Какие у вас ожидания по заработной плате?",
                    "Благодарю за ваш интерес к нашей компании. К сожалению, в данный момент мы не можем предложить вам подходящую позицию, но мы сохраним ваше резюме в нашей базе данных."
                ]
                
                # Выбираем ответ на основе хеша для детерминированности
                hash_int = int(messages_hash, 16)
                mock_response = mock_responses[hash_int % len(mock_responses)]
                
                # Сохраняем в кеш
                self.fixed_responses_cache[messages_hash] = mock_response
                with open(self._cache_path, 'w', encoding='utf-8') as f:
                    json.dump(self.fixed_responses_cache, f, ensure_ascii=False, indent=2)
                
                logger.info(f"Generated mock response for hash: {messages_hash}")
                return mock_response
            
            # Реальный вызов API
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=messages,
                temperature=self.chat_settings["temperature"],
                max_tokens=self.chat_settings["max_tokens"]
            )
            
            # Извлекаем текст ответа
            response_text = response.choices[0].message.content.strip()
            
            # Логируем время выполнения запроса
            execution_time = time.time() - start_time
            logger.info(f"OpenAI API Chat completed in {execution_time:.2f} seconds")
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error in OpenAI API Chat call: {e}")
            raise
