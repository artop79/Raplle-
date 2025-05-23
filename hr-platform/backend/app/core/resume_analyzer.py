import os
import json
import fitz  # PyMuPDF для работы с PDF
import openai
from app.config import settings
import docx
import tempfile
import aiofiles

class ResumeAnalyzer:
    """Класс для анализа резюме с использованием OpenAI API"""
    
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
    
    async def extract_text_from_pdf(self, file_path):
        """Извлечение текста из PDF файла"""
        try:
            # Если файл - PDF
            if file_path.lower().endswith('.pdf'):
                doc = fitz.open(file_path)
                text = ""
                for page in doc:
                    text += page.get_text()
                return text
            
            # Если файл - DOCX
            elif file_path.lower().endswith('.docx'):
                doc = docx.Document(file_path)
                text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
                return text
            
            # Если файл - DOC или другой формат
            else:
                # Можно добавить другие обработчики или конвертеры
                raise ValueError(f"Неподдерживаемый формат файла: {file_path}")
                
        except Exception as e:
            raise Exception(f"Ошибка при извлечении текста: {str(e)}")
    
    async def analyze(self, resume_text, job_description=None):
        """
        Анализ резюме с использованием OpenAI API
        
        Args:
            resume_text (str): Текст резюме
            job_description (str, optional): Текст описания вакансии для сравнения
            
        Returns:
            dict: Результаты анализа в структурированном виде
        """
        try:
            # Сокращаем длинные документы, чтобы уложиться в лимиты токенов API
            resume_text = self._truncate_text(resume_text, max_chars=12000)
            if job_description:
                job_description = self._truncate_text(job_description, max_chars=4000)
            
            # Строим промпт в зависимости от наличия описания вакансии
            prompt = self._build_prompt(resume_text, job_description)
            
            # Вызываем API OpenAI
            response = await openai.chat.completions.acreate(
                model=settings.GPT_MODEL,
                messages=[
                    {"role": "system", "content": "Вы HR-аналитик, который профессионально анализирует резюме кандидатов."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=settings.MAX_TOKENS,
                temperature=0.2  # Низкая температура для более точных ответов
            )
            
            # Извлекаем и парсим ответ
            result_text = response.choices[0].message.content
            
            # Пытаемся преобразовать результат в JSON
            try:
                # Ищем JSON в ответе (если ответ может содержать дополнительный текст)
                start_json = result_text.find('{')
                end_json = result_text.rfind('}') + 1
                if start_json != -1 and end_json != 0:
                    json_str = result_text[start_json:end_json]
                    result = json.loads(json_str)
                else:
                    # Если JSON не найден, используем весь ответ как текст
                    result = {"analysis": result_text}
            except json.JSONDecodeError:
                # Если не удалось распарсить JSON, возвращаем текстовый результат
                result = {"analysis": result_text}
            
            # Добавляем скоринг, если его нет в результате
            if "overall_score" not in result and job_description:
                result["overall_score"] = self._calculate_score(result)
            
            return result
            
        except Exception as e:
            raise Exception(f"Ошибка при анализе резюме: {str(e)}")
    
    def _build_prompt(self, resume_text, job_description=None):
        """Создание запроса к OpenAI в зависимости от наличия описания вакансии"""
        if job_description:
            return f"""
            Проанализируйте это резюме:
            
            {resume_text}
            
            И сравните его с требованиями вакансии:
            
            {job_description}
            
            Результат представьте в структурированном виде JSON со следующими ключами:
            1. "skills" - массив ключевых навыков кандидата
            2. "experience" - объект с опытом работы (компании, должности, годы)
            3. "education" - информация об образовании
            4. "match_percentage" - процент соответствия требованиям вакансии (число от 0 до 100)
            5. "strengths" - массив сильных сторон кандидата
            6. "areas_for_improvement" - массив областей для развития
            7. "recommendations" - объект с рекомендациями для HR (ключи: "hire" - булево значение, "reason" - строка с объяснением)
            8. "overall_score" - общий скоринг кандидата (число от 0 до 100)
            
            Отформатируйте результат в валидный JSON. Используйте только русский язык в ответе.
            """
        else:
            return f"""
            Проанализируйте это резюме:
            
            {resume_text}
            
            Результат представьте в структурированном виде JSON со следующими ключами:
            1. "skills" - массив ключевых навыков кандидата
            2. "experience" - объект с опытом работы (компании, должности, годы)
            3. "education" - информация об образовании
            4. "strengths" - массив сильных сторон кандидата
            5. "summary" - краткое резюме кандидата (2-3 предложения)
            
            Отформатируйте результат в валидный JSON. Используйте только русский язык в ответе.
            """
    
    def _truncate_text(self, text, max_chars=10000):
        """Сокращение длинных текстов для соблюдения ограничений токенов API"""
        if len(text) <= max_chars:
            return text
        
        # Берем начало и конец документа, пропуская середину
        start_chars = int(max_chars * 0.7)  # 70% от начала
        end_chars = max_chars - start_chars  # 30% от конца
        
        truncated = text[:start_chars] + "\n...[текст сокращен]...\n" + text[-end_chars:]
        return truncated
    
    def _calculate_score(self, analysis_result):
        """
        Расчет общего скоринга кандидата на основе результатов анализа
        Это упрощенная версия для MVP, в реальном приложении логика будет сложнее
        """
        score = 0
        
        # Если есть процент соответствия, используем его
        if "match_percentage" in analysis_result:
            try:
                return float(analysis_result["match_percentage"])
            except (ValueError, TypeError):
                pass
        
        # Оценка на основе рекомендации найма
        if "recommendations" in analysis_result and "hire" in analysis_result["recommendations"]:
            if analysis_result["recommendations"]["hire"]:
                score += 70  # Базовый скор для рекомендуемых кандидатов
            else:
                score += 30  # Базовый скор для нерекомендуемых кандидатов
        
        # Добавляем бонусы за сильные стороны
        if "strengths" in analysis_result:
            score += min(len(analysis_result["strengths"]) * 5, 15)  # До 15 баллов за сильные стороны
        
        # Вычитаем за области для улучшения
        if "areas_for_improvement" in analysis_result:
            score -= min(len(analysis_result["areas_for_improvement"]) * 3, 10)  # До 10 баллов вычета
        
        # Ограничиваем диапазон от 0 до 100
        return max(0, min(score, 100))
