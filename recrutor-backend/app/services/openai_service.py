from typing import Dict, Any, List
import hashlib
import json
import logging
import time
from datetime import datetime

import openai
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

# Настройка логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import os

class OpenAIService:
    def __init__(self):
        self._cache_path = os.path.join(os.path.dirname(__file__), 'deterministic_cache.json')
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
        
        # Информация о провайдере для сохранения в БД
        self.provider_name = "openai" if not self.mock_mode else "mock"
        
        # Настройки для анализа
        self.analysis_settings = {
            "model": "gpt-4o",  # Для максимального качества. Для экономии можно использовать "gpt-4o-mini"
            "temperature": 0,  # Устанавливаем в 0 для полной детерминированности
            "max_tokens": 1000
        }
        
        # Модель, используемая для анализа
        self.model = self.analysis_settings["model"]
        
        logger.info(f"OpenAI service initialized: mock_mode={self.mock_mode}, model={self.model}")

    
    def _normalize_result(self, result):
        # Округлить все числовые значения до ближайших 2
        def round_score(val):
            if isinstance(val, (int, float)):
                return int(round(val / 2.0) * 2)
            return val
            
        if 'score' in result:
            result['score'] = round_score(result['score'])
        if 'skills' in result:
            for skill in result['skills']:
                if 'match' in skill:
                    skill['match'] = round_score(skill['match'])
        if 'experience' in result and 'match' in result['experience']:
            result['experience']['match'] = round_score(result['experience']['match'])
        if 'education' in result and 'match' in result['education']:
            result['education']['match'] = round_score(result['education']['match'])
        return result

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _call_openai_api(self, prompt: str) -> Dict[str, Any]:
        """
        Вызывает OpenAI API с возможностью повторных попыток в случае ошибки
        """
        try:
            start_time = time.time()
            logger.info(f"Calling OpenAI API with model: {self.model}")
            
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise AI assistant that follows instructions exactly and outputs structured JSON data."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.analysis_settings["temperature"],
                max_tokens=self.analysis_settings["max_tokens"]
            )
            
            # Извлекаем JSON из ответа
            response_text = response.choices[0].message.content.strip()
            
            # Записываем время выполнения
            execution_time = time.time() - start_time
            logger.info(f"OpenAI API call completed in {execution_time:.2f} seconds")
            
            return response_text
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            raise
            
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _call_openai_api_chat(self, messages: List[Dict[str, str]]) -> str:
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
                temperature=0.7,  # Немного творчества для ответов в чате
                max_tokens=1000
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
            # Удаляем обертку ```json ... ``` если она есть
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '', 1)
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
            elif response_text.startswith('```'):
                response_text = response_text.replace('```', '', 1)
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
            
            # Парсим JSON
            result = json.loads(response_text)
            
            api_time = time.time() - start_time
            logger.info(f"OpenAI API call completed in {api_time:.2f}s")
            
            return result
        except Exception as e:
            logger.error(f"Error in OpenAI API call: {str(e)}")
            raise
    
    async def analyze_resume(self, resume_text: str, job_description_text: str) -> Dict[str, Any]:
        """
        Анализирует резюме по сравнению с описанием вакансии, используя OpenAI API.
        
        Args:
            resume_text: Текст резюме
            job_description_text: Текст описания вакансии
            
        Returns:
            Dict[str, Any]: Результаты анализа резюме
        """
        try:
            # Создаем стабильный хеш для идентификации уникальной пары документов
            content_hash = hashlib.sha256((resume_text + "#SEP#" + job_description_text).encode('utf-8')).hexdigest()
            
            logger.info(f"Content hash for analysis: {content_hash[:8]}...")
            
            # Проверяем, есть ли результат в кэше
            if content_hash in self.fixed_responses_cache:
                logger.info(f"Using cached result for content hash: {content_hash[:8]}...")
                return self.fixed_responses_cache[content_hash]
            
            # Создаем промпт для анализа
            prompt = self._create_analysis_prompt(resume_text, job_description_text)
            
            # Если режим мок-данных, возвращаем фиктивные данные
            if self.mock_mode:
                logger.info("Using mock data for resume analysis")
                result = self._create_mock_results(resume_text, job_description_text)
            else:
                # Вызываем OpenAI API для анализа
                logger.info("Calling OpenAI API for resume analysis")
                result = await self._call_openai_api(prompt)
            
            # Нормализуем результаты для большей стабильности
            result = self._normalize_result(result)
            
            # Сохраняем результат в кэше
            self.fixed_responses_cache[content_hash] = result
            
            # Пробуем сохранить кэш в файл
            try:
                with open(self._cache_path, 'w', encoding='utf-8') as f:
                    json.dump(self.fixed_responses_cache, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"Failed to save cache to file: {str(e)}")
            
            return result
            
        except Exception as e:
            # В случае ошибки возвращаем фиксированные результаты
            logger.error(f"Error during resume analysis: {str(e)}")
            return self._create_mock_results(resume_text, job_description_text)
    
    def _create_analysis_prompt(self, resume_text: str, job_description_text: str) -> str:
        """Создает запрос для анализа резюме"""
        return f"""
        Ты - профессиональный HR аналитик, специализирующийся на подборе персонала. Твоя задача - провести детальный анализ резюме кандидата и оценить его соответствие требованиям вакансии, предоставив точный процент соответствия и подробное обоснование.
        
        РЕЗЮМЕ КАНДИДАТА:
        {resume_text}
        
        ОПИСАНИЕ ВАКАНСИИ:
        {job_description_text}
        
        Выполни следующие задачи анализа:
        
        1. ТРЕБОВАНИЯ ВАКАНСИИ И СООТВЕТСТВИЕ:
           - Извлеки все обязательные и желательные требования из описания вакансии (hard skills, soft skills, опыт, образование).  
           - Для каждого требования проверь его наличие в резюме и определи степень соответствия (0-100%).
           - Для каждого требования приведи точную цитату из резюме, подтверждающую соответствие или его отсутствие.
           
        2. ОПЫТ РАБОТЫ:
           - Извлеки должности, компании, периоды работы.
           - Проанализируй соответствие опыта требованиям вакансии, учитывая релевантность опыта, позиции, стаж.
           - Определи, насколько опыт кандидата соответствует требуемому по вакансии (в процентах).
           - Приведи цитаты из резюме с примерами конкретных достижений и опыта.
           
        3. ОБРАЗОВАНИЕ: 
           - Проанализируй соответствие образования кандидата требованиям вакансии.
           - Оцени в процентах соответствие профиля образования, уровня образования и квалификации.
           
        4. КЛЮЧЕВЫЕ НАВЫКИ:
           - Извлеки из резюме все навыки (hard skills и soft skills).
           - Для каждого навыка определи, есть ли он в требованиях вакансии и насколько он релевантен.
           - Для каждого навыка приведи контекст его применения из резюме.
           
        5. ДОСТИЖЕНИЯ И РЕЗУЛЬТАТЫ:
           - Найди в резюме конкретные количественные и качественные достижения.
           - Проанализируй, насколько эти достижения соответствуют ожиданиям по вакансии.
           
        6. ОБЩАЯ ОЦЕНКА И ОБОСНОВАНИЕ:
           - Рассчитай точный общий процент соответствия кандидата вакансии (от 0 до 100).
           - Предоставь детальное обоснование оценки, с указанием сильных и слабых сторон кандидата.
           - Сформулируй 3-5 конкретных вопросов для интервью, которые помогут уточнить соответствие кандидата.
           
        7. ПОТЕНЦИАЛЬНЫЕ РИСКИ:
           - Выяви все несоответствия между требованиями вакансии и резюме кандидата.
           - Отметь пробелы в опыте работы, нерелевантные периоды, несоответствия навыков.
           
        ВАЖНО: Для оценки степени соответствия используй следующие критерии:
        - 90-100%: Превосходное соответствие - кандидат полностью соответствует всем требованиям и демонстрирует дополнительные ценные навыки.
        - 80-89%: Высокое соответствие - кандидат соответствует всем ключевым требованиям с небольшими пробелами.
        - 70-79%: Хорошее соответствие - кандидат соответствует большинству ключевых требований.
        - 60-69%: Среднее соответствие - кандидат соответствует некоторым ключевым требованиям, но имеет значительные пробелы.
        - 50-59%: Ниже среднего - кандидат частично соответствует основным требованиям.
        - Менее 50%: Слабое соответствие - кандидат не соответствует большинству требований.
        
        РЕЗУЛЬТАТ АНАЛИЗА представь в следующем детальном формате JSON:
        
        ```json
        {
          "overall_match": {
            "score": <общий процент соответствия от 0 до 100>,
            "summary": "<краткое резюме соответствия, 2-3 предложения>",
            "strengths": ["<сильная сторона 1>", "<сильная сторона 2>", ...],
            "weaknesses": ["<слабая сторона 1>", "<слабая сторона 2>", ...]
          },
          "requirements_analysis": {
            "mandatory": [
              {
                "requirement": "<обязательное требование>",
                "match": <процент соответствия от 0 до 100>,
                "evidence": "<цитата из резюме>",
                "comment": "<комментарий о соответствии>"
              },
              ...
            ],
            "preferred": [
              {
                "requirement": "<желательное требование>",
                "match": <процент соответствия от 0 до 100>,
                "evidence": "<цитата из резюме>",
                "comment": "<комментарий о соответствии>"
              },
              ...
            ]
          },
          "skills_analysis": [
            {
              "skill": "<название навыка>",
              "category": "<hard_skill|soft_skill>",
              "match": <процент соответствия от 0 до 100>,
              "context": "<контекст применения из резюме>",
              "relevance": "<насколько релевантен для вакансии>"
            },
            ...
          ],
          "experience": {
            "match": <процент соответствия опыта от 0 до 100>,
            "summary": "<общее описание соответствия опыта>",
            "details": [
              {
                "position": "<должность>",
                "company": "<компания>",
                "period": "<период работы>",
                "relevance": <процент релевантности от 0 до 100>,
                "highlights": ["<ключевое достижение или навык 1>", ...],
                "evidence": "<цитата из резюме>"
              },
              ...
            ]
          },
          "education": {
            "match": <процент соответствия образования от 0 до 100>,
            "summary": "<общее описание соответствия образования>",
            "details": [
              {
                "degree": "<степень/квалификация>",
                "institution": "<учебное заведение>",
                "year": "<год окончания>",
                "relevance": <процент релевантности от 0 до 100>,
                "comment": "<комментарий о соответствии>"
              },
              ...
            ]
          },
          "achievements": [
            {
              "description": "<описание достижения>",
              "evidence": "<цитата из резюме>",
              "relevance": <процент релевантности от 0 до 100>,
              "comment": "<комментарий о значимости для вакансии>"
            },
            ...
          ],
          "risks": [
            {
              "category": "<категория риска: experience_gap|skill_mismatch|education|other>",
              "description": "<описание риска>",
              "severity": "<high|medium|low>",
              "mitigation": "<возможные пути снижения риска>"
            },
            ...
          ],
          "interview_questions": [
            {
              "question": "<вопрос для интервью>",
              "purpose": "<цель вопроса>",
              "related_to": "<связь с требованием или навыком>"
            },
            ...
          ]
        }
        ```
        
        Проведи МАКСИМАЛЬНО ДЕТАЛЬНЫЙ анализ, учитывая все нюансы резюме и требований вакансии. Для каждого пункта анализа приводи конкретные цитаты из резюме в качестве доказательства.
        
        В итоговом общем проценте соответствия (overall_match.score) отрази объективную оценку пригодности кандидата для данной вакансии, учитывая все проанализированные аспекты.
        
        Возвращай только JSON без дополнительных пояснений.
        """
    
    async def _make_openai_request(self, prompt: str) -> str:
        """Выполняет запрос к OpenAI API"""
        response = await openai.ChatCompletion.acreate(
            model=self.analysis_settings["model"],
            messages=[
                {"role": "system", "content": "Ты - HR-аналитик, который оценивает соответствие резюме кандидатов требованиям вакансий."},
                {"role": "user", "content": prompt}
            ],
            temperature=self.analysis_settings["temperature"],
            max_tokens=self.analysis_settings["max_tokens"],
        )
        
        return response.choices[0].message.content
    
    def _parse_analysis_response(self, response_text: str) -> Dict[str, Any]:
        # ... (остальной код)
        results = ... # (ваш способ парсинга)
        results = self._normalize_result(results)
        return results
        """Парсит ответ от OpenAI в структурированный формат"""
        import json
        import re
        
        try:
            # Пытаемся извлечь JSON из ответа
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            
            if json_match:
                json_text = json_match.group(1)
                results = json.loads(json_text)
            else:
                # Если формат не соответствует ожидаемому, пробуем найти JSON напрямую
                json_text = response_text.strip()
                results = json.loads(json_text)
            
            # Проверяем обязательные поля
            self._validate_results(results)
            
            return results
        
        except Exception as e:
            print(f"Error parsing OpenAI response: {str(e)}")
            print(f"Response text: {response_text}")
            return self._create_mock_results("", "")
    
    def _validate_results(self, results: Dict[str, Any]) -> bool:
        """Проверяет наличие всех необходимых полей в результатах"""
        required_fields = ["score", "skills", "experience", "education", "recommendations"]
        
        for field in required_fields:
            if field not in results:
                raise ValueError(f"Missing required field: {field}")
        
        if not isinstance(results["skills"], list) or len(results["skills"]) == 0:
            raise ValueError("Skills must be a non-empty list")
        
        if not isinstance(results["recommendations"], list) or len(results["recommendations"]) == 0:
            raise ValueError("Recommendations must be a non-empty list")
        
        return True
    
    def _create_mock_results(self, resume_text: str, job_description_text: str) -> Dict[str, Any]:
        # ... (остальной код)
        results = ... # (ваш способ создания mock-результата)
        results = self._normalize_result(results)
        return results
        """Создает детерминистические тестовые данные для анализа"""
        # Создаем хеш для стабильной идентификации входных данных
        combined_hash = hashlib.sha256((resume_text + "#SEP#" + job_description_text).encode('utf-8')).hexdigest()
        
        logger.info(f"Generated content hash for analysis: {combined_hash[:8]}...")
        
        # ФИКСИРОВАННЫЕ значения - никакой диапазон, только константы
        # Для каждого комбинированного хеша должен быть ровно 1 результат
        
        # Вместо возврата разных значений, используем словарь фиксированных ответов
        # Каждый хеш будет соответствовать ровно одному результату

        # Список известных хешей
        fixed_responses = {
            # Тестовый ответ для разработки - если не найден хеш, будут добавляться новые
            "test": {
                "score": 82,
                "skills": [
                    {"name": "Java", "match": 90},
                    {"name": "Spring", "match": 90},
                    {"name": "Hibernate", "match": 90},
                    {"name": "SQL", "match": 90},
                    {"name": "Git", "match": 90}
                ],
                "experience": {
                    "description": "Опыт полностью соответствует требованиям вакансии",
                    "match": 90,
                    "details": [
                        "Опыт работы с Java и Spring",
                        "Разработка веб-приложений",
                        "Работа с базами данных"
                    ]
                },
                "education": {
                    "description": "Высшее техническое образование соответствует требованиям",
                    "match": 90
                },
                "recommendations": [
                    "Проверить знания в области архитектуры приложений",
                    "Уточнить опыт работы в команде",
                    "Оценить навыки решения проблем"
                ]
            }
        }
        
        # Используем базовый тестовый ответ
        results = fixed_responses["test_response"].copy() if "test_response" in fixed_responses else {}
        
        # Определяем область деятельности для дополнительной информации
        domain = self._determine_job_domain(resume_text, job_description_text)
        logger.info(f"Detected domain for mock data: {domain}")

        
        # Заполняем данные в зависимости от домена
        if domain.upper() == "IT":
            return self._create_it_mock_results(results)
        elif domain.upper() == "HR":
            return self._create_hr_mock_results(results)
        elif domain.upper() == "FINANCE":
            return self._create_finance_mock_results(results)
        elif domain.upper() == "MEDICAL":
            return self._create_medical_mock_results(results)
        elif domain.upper() == "SALES":
            return self._create_sales_mock_results(results)
        elif domain.upper() == "LEGAL":
            return self._create_legal_mock_results(results)
        else:
            return self._create_general_mock_results(results)
    
    def _determine_job_domain(self, resume_text: str, job_description_text: str) -> str:
        """Определяет профессиональную область по тексту резюме и вакансии"""
        combined_text = (resume_text or "") + " " + (job_description_text or "")
        lower_text = combined_text.lower()
        
        domains = {
            "it": ["программирование", "разработка", "javascript", "python", "developer", "программист"],
            "hr": ["hr", "кадры", "персонал", "рекрутинг", "делопроизводство"],
            "finance": ["финансы", "бухгалтер", "бухгалтерия", "аудит", "экономист"],
            "medical": ["врач", "медицинский", "медсестра", "больница", "клиника"],
            "sales": ["продажи", "менеджер по продажам", "sales", "клиенты", "продавец"],
            "legal": ["юрист", "правовой", "адвокат", "юридический", "законодательство"]
        }
        
        # Находим совпадения для каждой области
        domain_matches = {}
        for domain, keywords in domains.items():
            domain_matches[domain] = sum(1 for word in keywords if word in lower_text)
        
        # Определяем область с наибольшим числом совпадений
        max_matches = 0
        detected_domain = "general"
        
        for domain, matches in domain_matches.items():
            if matches > max_matches:
                max_matches = matches
                detected_domain = domain
        
        return detected_domain
    
    # Генераторы тестовых данных для различных доменов
    def _create_it_mock_results(self, results):
        skills = ["JavaScript", "React", "TypeScript", "Node.js", "Git"]
        
        # Детерминированный mock: всегда одни и те же значения
        results["skills"] = [
            {"name": skills[0], "match": 95},
            {"name": skills[1], "match": 90},
            {"name": skills[2], "match": 85},
            {"name": skills[3], "match": 80},
            {"name": skills[4], "match": 75}
        ]
        results["experience"]["description"] = "Кандидат имеет опыт разработки ПО с использованием современных технологий."
        results["experience"]["details"] = [
            "Опыт работы в команде разработчиков",
            "Участие в полном цикле разработки",
            "Использование систем контроля версий"
        ]
        results["education"]["description"] = "Образование соответствует требованиям в сфере IT."
        results["recommendations"] = [
            "Обсудить опыт работы над схожими проектами",
            "Уточнить знание современных методологий разработки",
            "Оценить навыки работы в команде"
        ]
        
        return results
    
    def _create_hr_mock_results(self, results):
        skills = ["Подбор персонала", "Кадровое делопроизводство", "1С:ЗУП", "Трудовой кодекс"]
        
        # Детерминированный mock: всегда одни и те же значения
        results["skills"] = [
            {"name": skills[0], "match": 95},
            {"name": skills[1], "match": 90},
            {"name": skills[2], "match": 85},
            {"name": skills[3], "match": 80}
        ]
        results["experience"]["description"] = "Кандидат имеет опыт работы в HR и управлении персоналом."
        results["experience"]["details"] = [
            "Ведение кадрового делопроизводства",
            "Подбор и адаптация персонала",
            "Работа с 1С:ЗУП"
        ]
        results["education"]["description"] = "Образование соответствует требованиям позиции в сфере HR."
        results["recommendations"] = [
            "Уточнить опыт работы с большим коллективом",
            "Обсудить методы оценки персонала",
            "Проверить знание изменений в трудовом законодательстве"
        ]
        
        return results
    
    def _create_finance_mock_results(self, results):
        skills = ["1С:Бухгалтерия", "Финансовый анализ", "Бюджетирование", "Excel", "Налоговый учет"]
        
        # Детерминированный mock: всегда одни и те же значения
        results["skills"] = [
            {"name": skills[0], "match": 95},
            {"name": skills[1], "match": 90},
            {"name": skills[2], "match": 85},
            {"name": skills[3], "match": 80}
        ]
        results["experience"]["description"] = "Кандидат имеет опыт работы в финансовой сфере."
        results["experience"]["details"] = [
            "Ведение бухгалтерского учета",
            "Подготовка финансовой отчетности",
            "Работа с налоговыми органами"
        ]
        results["education"]["description"] = "Образование соответствует требованиям в сфере финансов."
        results["recommendations"] = [
            "Обсудить опыт работы с различными системами налогообложения",
            "Уточнить знание последних изменений в законодательстве",
            "Оценить навыки финансового анализа"
        ]
        
        return results
    
    def _create_medical_mock_results(self, results):
        skills = ["Диагностика", "Терапия", "Медицинская документация", "Первая помощь"]
        
        # Детерминированный mock: всегда одни и те же значения
        results["skills"] = [
            {"name": skills[0], "match": 95},
            {"name": skills[1], "match": 90},
            {"name": skills[2], "match": 85},
            {"name": skills[3], "match": 80}
        ]
        results["experience"]["description"] = "Кандидат имеет опыт работы в медицинской сфере."
        results["experience"]["details"] = [
            "Работа с пациентами",
            "Ведение медицинской документации",
            "Диагностика и лечение"
        ]
        results["education"]["description"] = "Кандидат имеет профильное медицинское образование."
        results["recommendations"] = [
            "Уточнить опыт работы со сложными случаями",
            "Обсудить подход к работе с пациентами",
            "Проверить знание современных методов лечения"
        ]
        
        return results
    
    def _create_sales_mock_results(self, results):
        skills = ["Проведение переговоров", "Работа с клиентами", "CRM-системы", "Презентации"]
        
        # Детерминированный mock: всегда одни и те же значения
        results["skills"] = [
            {"name": skills[0], "match": 95},
            {"name": skills[1], "match": 90},
            {"name": skills[2], "match": 85},
            {"name": skills[3], "match": 80}
        ]
        results["experience"]["description"] = "Кандидат имеет опыт в продажах и работе с клиентами."
        results["experience"]["details"] = [
            "Выполнение плана продаж",
            "Работа с ключевыми клиентами",
            "Ведение клиентской базы"
        ]
        results["education"]["description"] = "Образование соответствует требованиям в сфере продаж."
        results["recommendations"] = [
            "Обсудить конкретные достижения в продажах",
            "Уточнить методы работы с возражениями",
            "Оценить навыки презентации продукта"
        ]
        
        return results
    
    def _create_legal_mock_results(self, results):
        skills = ["Договорная работа", "Корпоративное право", "Судебная практика", "Юридические консультации"]
        
        # Детерминированный mock: всегда одни и те же значения
        results["skills"] = [
            {"name": skills[0], "match": 95},
            {"name": skills[1], "match": 90},
            {"name": skills[2], "match": 85},
            {"name": skills[3], "match": 80}
        ]
        results["experience"]["description"] = "Кандидат имеет опыт работы в юридической сфере."
        results["experience"]["details"] = [
            "Разработка юридических документов",
            "Представление интересов в суде",
            "Правовая экспертиза"
        ]
        results["education"]["description"] = "Кандидат имеет высшее юридическое образование."
        results["recommendations"] = [
            "Обсудить опыт работы со сложными юридическими кейсами",
            "Уточнить специализацию в области права",
            "Проверить знание последних изменений в законодательстве"
        ]
        
        return results
    
    def _create_general_mock_results(self, results):
        skills = ["Коммуникация", "Работа в команде", "MS Office", "Организация", "Адаптивность"]
        
        # Детерминированный mock: всегда одни и те же значения
        results["skills"] = [
            {"name": skills[0], "match": 95},
            {"name": skills[1], "match": 90},
            {"name": skills[2], "match": 85},
            {"name": skills[3], "match": 80}
        ]
        results["experience"]["description"] = "Кандидат имеет релевантный опыт работы."
        results["experience"]["details"] = [
            "Работа на аналогичной должности",
            "Выполнение должностных обязанностей",
            "Решение рабочих задач"
        ]
        results["education"]["description"] = "Образование кандидата соответствует требованиям позиции."
        results["recommendations"] = [
            "Обсудить опыт работы в данной сфере",
            "Уточнить достижения на предыдущем месте работы",
            "Оценить мотивацию кандидата"
        ]
        
        return results
