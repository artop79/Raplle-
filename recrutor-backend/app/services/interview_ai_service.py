from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from app.services.openai_service import OpenAIService

# Настройка логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InterviewAIService:
    """
    Сервис для AI-функциональности, связанной с интервью:
    - Генерация вопросов для интервью
    - Анализ ответов кандидатов
    - Генерация отчетов по интервью
    """

    def __init__(self, openai_service: OpenAIService):
        """
        Инициализация сервиса.
        
        Args:
            openai_service: Экземпляр OpenAIService для работы с OpenAI API
        """
        self.openai_service = openai_service
        logger.info("InterviewAIService initialized")
    
    async def generate_interview_questions(
        self, 
        vacancy_title: str,
        vacancy_description: str,
        requirements: Dict[str, List[str]],
        num_questions: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Генерирует вопросы для интервью на основе требований вакансии.
        
        Args:
            vacancy_title: Название вакансии
            vacancy_description: Описание вакансии
            requirements: Требования к кандидату
            num_questions: Количество вопросов для генерации
            
        Returns:
            Список словарей с вопросами
        """
        prompt = self._create_questions_generation_prompt(
            vacancy_title, vacancy_description, requirements, num_questions
        )
        
        # Используем существующий OpenAI сервис для запроса
        response = await self.openai_service._make_openai_request(prompt)
        
        # Парсим ответ
        questions = self._parse_generated_questions(response)
        
        return questions
    
    def _create_questions_generation_prompt(
        self, 
        vacancy_title: str,
        vacancy_description: str,
        requirements: Dict[str, List[str]],
        num_questions: int
    ) -> str:
        """
        Создает промпт для генерации вопросов интервью.
        
        Args:
            vacancy_title: Название вакансии
            vacancy_description: Описание вакансии
            requirements: Требования к кандидату
            num_questions: Количество вопросов для генерации
            
        Returns:
            Текст промпта
        """
        # Преобразуем требования в текстовый формат
        requirements_text = ""
        for category, items in requirements.items():
            requirements_text += f"{category}:\n"
            for item in items:
                requirements_text += f"- {item}\n"
        
        prompt = f"""
        Ты опытный HR-специалист, проводящий технические интервью. Твоя задача - создать список вопросов для интервью на вакансию.

        Информация о вакансии:
        Название: {vacancy_title}
        Описание: {vacancy_description}
        
        Требования к кандидату:
        {requirements_text}
        
        Создай {num_questions} релевантных вопросов для интервью. Вопросы должны проверять технические навыки, опыт и соответствие требованиям вакансии.
        
        Для каждого вопроса укажи:
        1. Текст вопроса
        2. Категорию вопроса (например, "Технические навыки", "Опыт работы", "Софт-скиллы")
        3. Что именно оценивает этот вопрос
        
        Верни результат в формате JSON:
        [
            {{
                "question_text": "Вопрос...",
                "category": "Категория вопроса",
                "evaluates": "Что оценивает вопрос"
            }},
            ...
        ]
        """
        
        return prompt
    
    def _parse_generated_questions(self, response: str) -> List[Dict[str, Any]]:
        """
        Парсит ответ API с вопросами для интервью.
        
        Args:
            response: Ответ от API
            
        Returns:
            Список словарей с вопросами
        """
        import json
        
        try:
            # Ищем JSON в ответе
            start_pos = response.find('[')
            end_pos = response.rfind(']')
            
            if start_pos != -1 and end_pos != -1:
                json_str = response[start_pos:end_pos+1]
                questions = json.loads(json_str)
                
                # Добавляем поле order для сортировки
                for i, question in enumerate(questions):
                    question["order"] = i + 1
                
                return questions
            else:
                logger.error("Failed to extract JSON from response")
                return []
        except Exception as e:
            logger.error(f"Error parsing interview questions: {e}")
            return []
    
    async def analyze_interview_answer(
        self,
        question: str,
        answer: str,
        vacancy_requirements: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """
        Анализирует ответ кандидата на вопрос интервью.
        
        Args:
            question: Вопрос интервью
            answer: Ответ кандидата
            vacancy_requirements: Требования вакансии
            
        Returns:
            Результаты анализа
        """
        prompt = self._create_answer_analysis_prompt(question, answer, vacancy_requirements)
        
        # Используем существующий OpenAI сервис для запроса
        response = await self.openai_service._make_openai_request(prompt)
        
        # Парсим ответ
        analysis_result = self._parse_answer_analysis(response)
        
        return analysis_result
    
    def _create_answer_analysis_prompt(
        self,
        question: str,
        answer: str,
        vacancy_requirements: Dict[str, List[str]]
    ) -> str:
        """
        Создает промпт для анализа ответа.
        
        Args:
            question: Вопрос интервью
            answer: Ответ кандидата
            vacancy_requirements: Требования вакансии
            
        Returns:
            Текст промпта
        """
        # Преобразуем требования в текстовый формат
        requirements_text = ""
        for category, items in vacancy_requirements.items():
            requirements_text += f"{category}:\n"
            for item in items:
                requirements_text += f"- {item}\n"
        
        prompt = f"""
        Ты опытный HR-специалист, оценивающий ответы кандидатов на интервью. 
        Проанализируй ответ кандидата и оцени, насколько хорошо он соответствует требованиям вакансии.

        Вопрос интервью: {question}
        
        Ответ кандидата: {answer}
        
        Требования вакансии:
        {requirements_text}
        
        Проведи анализ ответа по следующим параметрам:
        1. Соответствие ответа заданному вопросу (0-10)
        2. Демонстрация релевантных навыков и опыта (0-10)
        3. Глубина понимания темы (0-10)
        4. Структурированность и ясность ответа (0-10)
        
        Верни результат в формате JSON:
        {{
            "relevance_score": оценка,
            "skills_demonstration_score": оценка,
            "depth_score": оценка,
            "clarity_score": оценка,
            "total_score": оценка (среднее арифметическое),
            "strengths": ["сильная сторона 1", "сильная сторона 2", ...],
            "weaknesses": ["слабая сторона 1", "слабая сторона 2", ...],
            "detailed_feedback": "подробный анализ ответа"
        }}
        """
        
        return prompt
    
    def _parse_answer_analysis(self, response: str) -> Dict[str, Any]:
        """
        Парсит ответ API с анализом ответа.
        
        Args:
            response: Ответ от API
            
        Returns:
            Словарь с результатами анализа
        """
        import json
        
        try:
            # Ищем JSON в ответе
            start_pos = response.find('{')
            end_pos = response.rfind('}')
            
            if start_pos != -1 and end_pos != -1:
                json_str = response[start_pos:end_pos+1]
                analysis = json.loads(json_str)
                return analysis
            else:
                logger.error("Failed to extract JSON from response")
                return {
                    "total_score": 5,
                    "detailed_feedback": "Не удалось проанализировать ответ."
                }
        except Exception as e:
            logger.error(f"Error parsing answer analysis: {e}")
            return {
                "total_score": 5,
                "detailed_feedback": "Произошла ошибка при анализе ответа."
            }
    
    async def generate_interview_report(
        self,
        vacancy_title: str,
        vacancy_requirements: Dict[str, List[str]],
        candidate_name: str,
        questions_and_answers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Генерирует итоговый отчет по результатам интервью.
        
        Args:
            vacancy_title: Название вакансии
            vacancy_requirements: Требования вакансии
            candidate_name: Имя кандидата
            questions_and_answers: Список вопросов и ответов с оценками
            
        Returns:
            Отчет по интервью
        """
        prompt = self._create_report_generation_prompt(
            vacancy_title, vacancy_requirements, candidate_name, questions_and_answers
        )
        
        # Используем существующий OpenAI сервис для запроса
        response = await self.openai_service._make_openai_request(prompt)
        
        # Парсим ответ
        report = self._parse_generated_report(response)
        
        return report
    
    def _create_report_generation_prompt(
        self,
        vacancy_title: str,
        vacancy_requirements: Dict[str, List[str]],
        candidate_name: str,
        questions_and_answers: List[Dict[str, Any]]
    ) -> str:
        """
        Создает промпт для генерации отчета по интервью.
        
        Args:
            vacancy_title: Название вакансии
            vacancy_requirements: Требования вакансии
            candidate_name: Имя кандидата
            questions_and_answers: Список вопросов и ответов с оценками
            
        Returns:
            Текст промпта
        """
        # Преобразуем требования в текстовый формат
        requirements_text = ""
        for category, items in vacancy_requirements.items():
            requirements_text += f"{category}:\n"
            for item in items:
                requirements_text += f"- {item}\n"
        
        # Преобразуем вопросы и ответы в текстовый формат
        qa_text = ""
        total_score = 0
        count = 0
        
        for i, qa in enumerate(questions_and_answers):
            if "question_text" in qa and "answer_text" in qa and qa.get("answer_text"):
                qa_text += f"Вопрос {i+1}: {qa.get('question_text')}\n"
                qa_text += f"Ответ: {qa.get('answer_text')}\n"
                
                if "analysis" in qa and isinstance(qa["analysis"], dict):
                    score = qa["analysis"].get("total_score", 0)
                    total_score += score
                    count += 1
                    qa_text += f"Оценка: {score}/10\n"
                    
                    if "detailed_feedback" in qa["analysis"]:
                        qa_text += f"Анализ: {qa['analysis']['detailed_feedback']}\n"
                
                qa_text += "\n"
        
        avg_score = total_score / count if count > 0 else 0
        
        prompt = f"""
        Ты опытный HR-специалист, составляющий итоговый отчет по результатам интервью. 
        На основе предоставленной информации о вакансии, требованиях и ответах кандидата создай детальный отчет.

        Вакансия: {vacancy_title}
        
        Требования:
        {requirements_text}
        
        Кандидат: {candidate_name}
        
        Средняя оценка по ответам: {avg_score:.1f}/10
        
        Вопросы и ответы:
        {qa_text}
        
        Создай итоговый отчет, включающий:
        1. Общую оценку кандидата (0-100)
        2. Сильные стороны кандидата (минимум 3)
        3. Области для развития (минимум 3)
        4. Рекомендацию (Рекомендовать / Рассмотреть дополнительно / Не рекомендовать)
        5. Подробное обоснование рекомендации
        
        Верни результат в формате JSON:
        {{
            "total_score": оценка,
            "strengths": ["сильная сторона 1", "сильная сторона 2", ...],
            "weaknesses": ["область для развития 1", "область для развития 2", ...],
            "recommendation": "Рекомендация",
            "analysis_summary": "Подробное обоснование"
        }}
        """
        
        return prompt
    
    def _parse_generated_report(self, response: str) -> Dict[str, Any]:
        """
        Парсит ответ API с отчетом по интервью.
        
        Args:
            response: Ответ от API
            
        Returns:
            Словарь с отчетом
        """
        import json
        
        try:
            # Ищем JSON в ответе
            start_pos = response.find('{')
            end_pos = response.rfind('}')
            
            if start_pos != -1 and end_pos != -1:
                json_str = response[start_pos:end_pos+1]
                report = json.loads(json_str)
                
                # Проверяем recommendation и нормализуем
                if "recommendation" in report:
                    recommendation = report["recommendation"].lower()
                    if "рекомендовать" in recommendation and "не" not in recommendation:
                        report["recommendation"] = "recommended"
                    elif "дополнительно" in recommendation or "рассмотреть" in recommendation:
                        report["recommendation"] = "additional_interview"
                    else:
                        report["recommendation"] = "not_recommended"
                
                return report
            else:
                logger.error("Failed to extract JSON from response")
                return {
                    "total_score": 50,
                    "strengths": ["Нет данных"],
                    "weaknesses": ["Нет данных"],
                    "recommendation": "additional_interview",
                    "analysis_summary": "Не удалось сгенерировать отчет."
                }
        except Exception as e:
            logger.error(f"Error parsing interview report: {e}")
            return {
                "total_score": 50,
                "strengths": ["Нет данных"],
                "weaknesses": ["Нет данных"],
                "recommendation": "additional_interview",
                "analysis_summary": "Произошла ошибка при генерации отчета."
            }
