import openai
from app.config import settings
import json
import re

async def generate_questions(job_description, skills=None, num_questions=10):
    """
    Генерация вопросов для интервью на основе описания вакансии
    
    Args:
        job_description: Описание вакансии
        skills: Требуемые навыки (опционально)
        num_questions: Количество вопросов для генерации
    
    Returns:
        list: Список вопросов
    """
    
    skills_text = ""
    if skills:
        if isinstance(skills, list):
            skills_text = ", ".join(skills)
        else:
            skills_text = skills
            
    prompt = f"""
    Сгенерируйте {num_questions} вопросов для технического интервью на позицию со следующим описанием:
    
    Описание вакансии:
    {job_description}
    
    {f"Требуемые навыки: {skills_text}" if skills_text else ""}
    
    Вопросы должны охватывать как технические навыки (hard skills), так и личностные качества (soft skills).
    Вопросы должны быть понятными, конкретными и позволять оценить компетентность кандидата.
    
    Верните список вопросов в формате JSON-массива.
    """
    
    try:
        # Проверяем наличие API ключа OpenAI
        if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "ваш_api_ключ":
            # Fallback на предустановленные вопросы
            return _get_default_questions(num_questions)
        
        # Вызываем OpenAI API
        response = await openai.chat.completions.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Вы опытный технический рекрутер, специализирующийся на проведении интервью."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        # Обработка ответа и извлечение вопросов
        content = response.choices[0].message.content
        
        # Находим JSON в ответе
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            questions = json.loads(json_match.group(0))
        else:
            # Если не удалось найти JSON, разбиваем по строкам
            lines = content.split('\n')
            questions = [line.strip().strip('0123456789.').strip() for line in lines if line.strip()]
            # Фильтруем пустые строки и заголовки
            questions = [q for q in questions if '?' in q]
        
        return questions
    except Exception as e:
        print(f"Ошибка при генерации вопросов: {e}")
        # Возвращаем базовые вопросы в случае ошибки
        return _get_default_questions(num_questions)

def _get_default_questions(num_questions=5):
    """Возвращает набор стандартных вопросов для интервью"""
    default_questions = [
        "Расскажите о вашем опыте работы в данной области.",
        "Какие технологии и инструменты вы использовали в последнем проекте?",
        "Расскажите о сложной задаче, которую вы решили, и как вы подошли к её решению.",
        "Как вы работаете в команде? Приведите пример успешного командного проекта.",
        "Как вы справляетесь со стрессовыми ситуациями на работе?",
        "Какие ваши сильные и слабые стороны?",
        "Почему вы считаете себя подходящим кандидатом на эту позицию?",
        "Какие у вас планы профессионального развития на ближайшие 1-2 года?",
        "Почему вы решили сменить текущее место работы или почему ищете новую работу?",
        "Какие у вас есть вопросы о компании или позиции?"
    ]
    
    # Ограничиваем количество вопросов
    return default_questions[:min(num_questions, len(default_questions))]
