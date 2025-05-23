"""
HR Agent Service - модуль для интеллектуального общения с кандидатами
использует OpenAI для обработки сообщений и генерации ответов
"""
from typing import Dict, Any, List, Optional
import logging
import json
import os
from datetime import datetime

from app.services.openai_chat import OpenAIChatService
from pydantic import BaseModel
from fastapi import HTTPException

# Настройка логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Модели данных
class Message(BaseModel):
    role: str  # 'system', 'user', 'assistant'
    content: str
    timestamp: Optional[datetime] = None

class Conversation(BaseModel):
    id: str
    candidate_id: str
    messages: List[Message]
    context: Dict[str, Any] = {}
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

class AgentPersonality(BaseModel):
    name: str
    description: str
    system_prompt: str

class HRAgentService:
    """Сервис HR агента для общения с кандидатами"""
    
    def __init__(self):
        """Инициализация сервиса HR агента"""
        self.openai_chat_service = OpenAIChatService()
        self.conversations = {}  # Хранилище бесед (в реальном проекте - база данных)
        self.personalities = self._initialize_personalities()
        self.conversation_storage_path = os.path.join(os.path.dirname(__file__), 'conversations')
        
        # Создаем папку для хранения бесед, если она не существует
        if not os.path.exists(self.conversation_storage_path):
            os.makedirs(self.conversation_storage_path)
            
        logger.info("HR Agent Service initialized")
    
    def _initialize_personalities(self) -> Dict[str, AgentPersonality]:
        """Инициализация доступных личностей HR агента"""
        return {
            "professional": AgentPersonality(
                name="Профессиональный",
                description="Деловой и эффективный стиль коммуникации",
                system_prompt=(
                    "Вы - профессиональный HR менеджер компании, общающийся с кандидатами. "
                    "Ваша задача - предоставить точную информацию о вакансии, процессе найма "
                    "и ответить на вопросы кандидата. Ваш стиль общения - деловой, четкий и конкретный. "
                    "Старайтесь быть информативным и помогать кандидату получить всю необходимую информацию. "
                    "Всегда сохраняйте профессиональный тон."
                )
            ),
            "friendly": AgentPersonality(
                name="Дружелюбный",
                description="Теплое и доброжелательное общение с кандидатами",
                system_prompt=(
                    "Вы - дружелюбный HR менеджер компании, общающийся с кандидатами. "
                    "Ваша задача - создать комфортную атмосферу общения, предоставить информацию о вакансии "
                    "и процессе найма, а также ответить на вопросы кандидата. Ваш стиль общения - теплый, "
                    "доброжелательный, с позитивным настроем. Используйте дружелюбные фразы, проявляйте эмпатию "
                    "и поддерживайте кандидата."
                )
            ),
            "formal": AgentPersonality(
                name="Формальный",
                description="Строгое соблюдение HR-протоколов и формальностей",
                system_prompt=(
                    "Вы - формальный HR менеджер компании, строго соблюдающий все корпоративные протоколы. "
                    "Ваша задача - предоставить информацию о вакансии и процессе найма, а также ответить на "
                    "вопросы кандидата, строго придерживаясь корпоративных стандартов. Ваш стиль общения - "
                    "формальный, с соблюдением всех официальных обращений и формулировок. Избегайте неформальных "
                    "выражений и всегда сохраняйте дистанцию."
                )
            )
        }
    
    def get_available_personalities(self) -> List[Dict[str, str]]:
        """
        Получение списка доступных личностей HR агента
        
        Returns:
            List[Dict[str, str]]: Список доступных личностей с их описаниями
        """
        return [
            {
                "id": personality_id,
                "name": personality.name,
                "description": personality.description
            }
            for personality_id, personality in self.personalities.items()
        ]
    
    def create_conversation(self, candidate_id: str, vacancy_id: Optional[str] = None, 
                           personality_id: str = "professional") -> str:
        """
        Создание новой беседы с кандидатом
        
        Args:
            candidate_id: ID кандидата
            vacancy_id: ID вакансии (опционально)
            personality_id: ID личности HR агента
            
        Returns:
            str: ID созданной беседы
        """
        # Проверяем, существует ли выбранная личность
        if personality_id not in self.personalities:
            raise HTTPException(status_code=400, detail=f"Personality {personality_id} not found")
        
        # Создаем новую беседу
        conversation_id = f"conv_{candidate_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Начальный контекст беседы
        context = {
            "vacancy_id": vacancy_id,
            "personality_id": personality_id,
            "stage": "greeting"  # Начальная стадия - приветствие
        }
        
        # Начальные сообщения в беседе
        messages = [
            Message(
                role="system",
                content=self.personalities[personality_id].system_prompt,
                timestamp=datetime.now()
            )
        ]
        
        # Если указана вакансия, добавляем информацию о ней в системное сообщение
        if vacancy_id:
            # В реальном проекте здесь будет загрузка данных о вакансии из БД
            vacancy_info = f"Вы общаетесь с кандидатом по вакансии с ID {vacancy_id}."
            messages.append(Message(
                role="system",
                content=vacancy_info,
                timestamp=datetime.now()
            ))
        
        # Создаем объект беседы
        conversation = Conversation(
            id=conversation_id,
            candidate_id=candidate_id,
            messages=messages,
            context=context
        )
        
        # Сохраняем беседу
        self.conversations[conversation_id] = conversation
        self._save_conversation(conversation)
        
        return conversation_id
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """
        Получение беседы по ID
        
        Args:
            conversation_id: ID беседы
            
        Returns:
            Optional[Conversation]: Объект беседы или None, если беседа не найдена
        """
        # Сначала проверяем в оперативной памяти
        if conversation_id in self.conversations:
            return self.conversations[conversation_id]
        
        # Если не найдено, пытаемся загрузить из файла
        conversation_path = os.path.join(self.conversation_storage_path, f"{conversation_id}.json")
        if os.path.exists(conversation_path):
            try:
                with open(conversation_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Преобразуем JSON в объект Conversation
                messages = [Message(**msg) for msg in data.get("messages", [])]
                conversation = Conversation(
                    id=data["id"],
                    candidate_id=data["candidate_id"],
                    messages=messages,
                    context=data.get("context", {}),
                    created_at=datetime.fromisoformat(data["created_at"]),
                    updated_at=datetime.fromisoformat(data["updated_at"])
                )
                
                # Сохраняем в оперативную память
                self.conversations[conversation_id] = conversation
                return conversation
            except Exception as e:
                logger.error(f"Error loading conversation {conversation_id}: {e}")
                return None
        
        return None
    
    def _save_conversation(self, conversation: Conversation) -> bool:
        """
        Сохранение беседы в файл
        
        Args:
            conversation: Объект беседы
            
        Returns:
            bool: True, если сохранение успешно, иначе False
        """
        try:
            # Преобразуем объект Conversation в JSON
            conversation_data = {
                "id": conversation.id,
                "candidate_id": conversation.candidate_id,
                "messages": [msg.dict() for msg in conversation.messages],
                "context": conversation.context,
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat()
            }
            
            # Сохраняем в файл
            conversation_path = os.path.join(self.conversation_storage_path, f"{conversation.id}.json")
            with open(conversation_path, 'w', encoding='utf-8') as f:
                json.dump(conversation_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Error saving conversation {conversation.id}: {e}")
            return False
    
    async def process_candidate_message(self, conversation_id: str, message_text: str) -> Dict[str, Any]:
        """
        Обработка сообщения от кандидата и генерация ответа
        
        Args:
            conversation_id: ID беседы
            message_text: Текст сообщения от кандидата
            
        Returns:
            Dict[str, Any]: Результат обработки сообщения с ответом HR агента
        """
        try:
            # Получаем беседу
            conversation = self.get_conversation(conversation_id)
            if not conversation:
                raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
            
            # Проверяем текст сообщения
            if not message_text or not message_text.strip():
                raise HTTPException(status_code=400, detail="Message text cannot be empty")
            
            # Добавляем сообщение кандидата в беседу
            user_message = Message(
                role="user",
                content=message_text,
                timestamp=datetime.now()
            )
            conversation.messages.append(user_message)
            conversation.updated_at = datetime.now()
            
            # Обновляем состояние беседы
            save_result = self._save_conversation(conversation)
            if not save_result:
                logger.error(f"Failed to save conversation {conversation_id} before generating response")
            
            # Генерируем ответ ассистента
            logger.info(f"Generating assistant response for conversation {conversation_id}")
            assistant_response = await self._generate_assistant_response(conversation)
            logger.info(f"Generated assistant response of length {len(assistant_response)}")
            
            # Добавляем ответ ассистента в беседу
            assistant_message = Message(
                role="assistant",
                content=assistant_response,
                timestamp=datetime.now()
            )
            conversation.messages.append(assistant_message)
            conversation.updated_at = datetime.now()
            
            # Сохраняем обновленную беседу
            save_result = self._save_conversation(conversation)
            if not save_result:
                logger.error(f"Failed to save conversation {conversation_id} after generating response")
            
            # Анализируем стадию беседы и определяем следующий шаг
            next_action = self._analyze_conversation_stage(conversation)
            
            # Формируем результат
            return {
                "conversation_id": conversation_id,
                "message": assistant_response,
                "next_action": next_action
            }
        except HTTPException:
            # Перебрасываем HTTP исключения для обработки в API маршрутах
            raise
        except Exception as e:
            # Логируем ошибку и возвращаем четкое сообщение
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500, 
                detail="Произошла ошибка при обработке сообщения. Пожалуйста, попробуйте еще раз позже."
            )
        """
        Генерация ответа HR агента с помощью OpenAI
        
        Args:
            conversation: Объект беседы
            
        Returns:
            str: Сгенерированный ответ HR агента
        """
        openai_messages = []
        
        # Добавляем системные сообщения
        for message in conversation.messages:
            if message.role in ["system", "user", "assistant"]:
                openai_messages.append({
                    "role": message.role,
                    "content": message.content
                })
        
        # Проверяем, что у нас есть хотя бы одно сообщение от пользователя
        user_messages = [msg for msg in openai_messages if msg["role"] == "user"]
        if not user_messages:
            logger.warning("No user messages found in the conversation. Adding a default message.")
            # Добавляем дефолтное сообщение
            openai_messages.append({
                "role": "user",
                "content": "Здравствуйте! Я хотел бы узнать о вакансии."
            })
        
        try:
            # Добавляем дополнительные параметры для вызова API
            logger.info(f"Calling OpenAI API with {len(openai_messages)} messages")
            
            # Вызываем OpenAI API для генерации ответа
            response = await self.openai_chat_service.call_openai_chat_api(openai_messages)
            
            # Проверяем результат
            if not response or not isinstance(response, str) or len(response.strip()) == 0:
                logger.error("Empty or invalid response received from OpenAI API")
                return "Извините, я не смог сформулировать ответ. Пожалуйста, повторите ваш вопрос."
            
            logger.info(f"Generated response of length {len(response)}")
            return response
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            # Возвращаем запасной ответ в случае ошибки
            return "Извините, в данный момент я испытываю технические трудности. Пожалуйста, попробуйте связаться с нами немного позже или напишите на нашу электронную почту."
    
    def _analyze_conversation_stage(self, conversation: Conversation) -> Dict[str, Any]:
        """
        Анализ стадии беседы и определение следующего шага
        
        Args:
            conversation: Объект беседы
            
        Returns:
            Dict[str, Any]: Информация о следующем шаге
        """
        # Получаем текущую стадию из контекста
        current_stage = conversation.context.get("stage", "greeting")
        
        # Определяем следующий шаг в зависимости от текущей стадии
        # Это упрощенная логика, в реальном проекте здесь будет более сложный анализ
        if current_stage == "greeting":
            # После приветствия переходим к стадии вопросов
            conversation.context["stage"] = "questions"
            return {
                "type": "continue",
                "stage": "questions",
                "description": "Кандидат может задавать вопросы о вакансии"
            }
        elif current_stage == "questions":
            # Продолжаем отвечать на вопросы
            return {
                "type": "continue",
                "stage": "questions",
                "description": "Продолжаем отвечать на вопросы кандидата"
            }
        
        # По умолчанию продолжаем беседу
        return {
            "type": "continue",
            "stage": current_stage,
            "description": "Продолжаем беседу с кандидатом"
        }
    
    def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """
        Получение истории сообщений беседы
        
        Args:
            conversation_id: ID беседы
            
        Returns:
            List[Dict[str, Any]]: История сообщений беседы
        """
        # Получаем беседу
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
        
        # Формируем историю сообщений (исключаем системные сообщения)
        history = []
        for message in conversation.messages:
            if message.role != "system":
                history.append({
                    "role": message.role,
                    "content": message.content,
                    "timestamp": message.timestamp.isoformat() if message.timestamp else None
                })
        
        return history
