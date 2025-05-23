import openai
import asyncio
import os
import time
import json
from app.config import settings

async def analyze_interview_answers(questions, answers):
    """Анализ ответов кандидата на вопросы интервью"""
    analysis_results = {}
    
    # Проверяем наличие API ключа OpenAI
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "ваш_api_ключ":
        return _get_dummy_analysis(questions, answers)
    
    try:
        # Формируем запрос для анализа каждого ответа
        for i, (question, answer) in enumerate(zip(questions, answers)):
            prompt = f"""
            Проанализируйте ответ кандидата на следующий вопрос:
            
            Вопрос: {question}
            
            Ответ кандидата: {answer}
            
            Оцените ответ по следующим критериям:
            1. Релевантность ответа (насколько ответ соответствует вопросу)
            2. Глубина понимания темы
            3. Ясность изложения
            4. Структурированность ответа
            5. Общее впечатление
            
            Для каждого критерия укажите оценку от 1 до 10 и краткое обоснование.
            Также дайте общую оценку ответа от 1 до 10.
            
            Результат верните в формате JSON.
            """
            
            response = await openai.chat.completions.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Вы эксперт по оценке кандидатов на собеседовании."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            analysis = response.choices[0].message.content
            analysis_results[f"question_{i+1}"] = {
                "question": question,
                "answer": answer,
                "analysis": analysis
            }
        
        # Общий анализ всего интервью
        all_answers = "\n\n".join([f"Вопрос: {q}\nОтвет: {a}" for q, a in zip(questions, answers)])
        
        summary_prompt = f"""
        Проведите общий анализ интервью кандидата на основе всех вопросов и ответов:
        
        {all_answers}
        
        Оцените:
        1. Технические навыки (знания, опыт, подход к решению задач)
        2. Soft skills (коммуникация, отношение к работе, культурное соответствие)
        3. Общее впечатление и рекомендации
        
        Дайте общую оценку кандидата от 1 до 100 и рекомендации о найме (рекомендовать/не рекомендовать/рассмотреть).
        
        Результат верните в формате JSON.
        """
        
        summary_response = await openai.chat.completions.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Вы эксперт по оценке кандидатов на собеседовании."},
                {"role": "user", "content": summary_prompt}
            ],
            temperature=0.3
        )
        
        analysis_results["summary"] = summary_response.choices[0].message.content
        
        return analysis_results
    except Exception as e:
        print(f"Ошибка при анализе интервью: {e}")
        return _get_dummy_analysis(questions, answers)

def _get_dummy_analysis(questions, answers):
    """Возвращает фиктивный анализ для демонстрационных целей"""
    
    analysis_results = {}
    
    # Анализируем каждый ответ
    for i, (question, answer) in enumerate(zip(questions, answers)):
        # Генерируем базовый анализ
        analysis = {
            "релевантность_ответа": {
                "оценка": 7,
                "обоснование": "Ответ в целом соответствует заданному вопросу, но есть некоторые отклонения от темы."
            },
            "глубина_понимания": {
                "оценка": 8,
                "обоснование": "Кандидат демонстрирует хорошее понимание предмета, но некоторые аспекты могли быть раскрыты глубже."
            },
            "ясность_изложения": {
                "оценка": 6,
                "обоснование": "Ответ в целом понятен, но местами нелогичен или недостаточно структурирован."
            },
            "структурированность": {
                "оценка": 7,
                "обоснование": "Ответ имеет логическую структуру, но переходы между идеями не всегда плавные."
            },
            "общее_впечатление": {
                "оценка": 7,
                "обоснование": "Хороший ответ, демонстрирующий компетентность кандидата в данном вопросе."
            },
            "общая_оценка": 7
        }
        
        analysis_results[f"question_{i+1}"] = {
            "question": question,
            "answer": answer,
            "analysis": json.dumps(analysis, ensure_ascii=False)
        }
    
    # Общий итог интервью
    summary = {
        "технические_навыки": {
            "оценка": 75,
            "комментарий": "Кандидат демонстрирует хороший уровень технических знаний, соответствующий требуемому для данной позиции."
        },
        "soft_skills": {
            "оценка": 70,
            "комментарий": "Коммуникативные навыки на хорошем уровне, кандидат ясно выражает свои мысли, проявляет энтузиазм."
        },
        "общее_впечатление": "Кандидат производит положительное впечатление, демонстрирует необходимые знания и опыт.",
        "общая_оценка": 72,
        "рекомендация": "Рассмотреть кандидатуру на следующих этапах собеседования."
    }
    
    analysis_results["summary"] = json.dumps(summary, ensure_ascii=False)
    
    return analysis_results

async def generate_pdf_report(candidate_name, vacancy_title, analysis_results):
    """
    Генерация PDF-отчета по результатам интервью
    В MVP версии возвращает путь к фиктивному файлу
    """
    # Создать директорию для отчетов, если не существует
    report_dir = os.path.join(settings.UPLOAD_DIR, "reports")
    os.makedirs(report_dir, exist_ok=True)
    
    # В полной версии здесь будет создание PDF отчета
    # с использованием библиотеки reportlab или fpdf
    
    # Для MVP просто возвращаем путь к несуществующему файлу
    filename = f"interview_report_{candidate_name.replace(' ', '_')}_{int(time.time())}.pdf"
    report_path = os.path.join(report_dir, filename)
    
    # Создаем пустой файл для демонстрации
    with open(report_path, "w") as f:
        f.write(f"Отчет по интервью {candidate_name} на позицию {vacancy_title}\n")
        f.write("Это тестовый отчет для MVP версии системы.\n")
        
        # Запись анализа в текстовом формате
        f.write("\n=== ОБЩИЙ ИТОГ ===\n")
        if isinstance(analysis_results["summary"], str):
            try:
                summary = json.loads(analysis_results["summary"])
                for key, value in summary.items():
                    if isinstance(value, dict):
                        f.write(f"{key}: {value.get('оценка')} - {value.get('комментарий', '')}\n")
                    else:
                        f.write(f"{key}: {value}\n")
            except:
                f.write(analysis_results["summary"])
        
        # Запись детального анализа ответов
        f.write("\n=== ДЕТАЛЬНЫЙ АНАЛИЗ ===\n")
        for key, data in analysis_results.items():
            if key == "summary":
                continue
                
            f.write(f"\nВопрос: {data['question']}\n")
            f.write(f"Ответ: {data['answer']}\n")
            f.write(f"Анализ: {data['analysis']}\n")
    
    return report_path
