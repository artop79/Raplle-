"""
Модуль для подробного подсчета скоринга кандидатов на основе анализа резюме и вакансии
"""

class CandidateScoring:
    """Класс для детального подсчета скоринга кандидатов"""
    
    def __init__(self):
        self.skill_weight = 0.5  # Вес навыков в общем скоринге
        self.experience_weight = 0.3  # Вес опыта
        self.education_weight = 0.2  # Вес образования
    
    def calculate_score(self, candidate_analysis, job_requirements):
        """
        Расчет скоринга кандидата на основе анализа и требований вакансии
        
        Args:
            candidate_analysis (dict): Результат анализа резюме кандидата
            job_requirements (dict): Требования вакансии
            
        Returns:
            dict: Детальный скоринг с разбивкой по категориям
        """
        scores = {
            'skills_match': self._calculate_skills_match(candidate_analysis, job_requirements),
            'experience': self._calculate_experience_score(candidate_analysis, job_requirements),
            'education': self._calculate_education_score(candidate_analysis, job_requirements),
            'overall': 0  # Будет рассчитано ниже
        }
        
        # Рассчитываем общий скоринг с весами
        scores['overall'] = (
            scores['skills_match'] * self.skill_weight + 
            scores['experience'] * self.experience_weight + 
            scores['education'] * self.education_weight
        )
        
        # Добавляем категорию и цветовое кодирование
        scores['category'] = self._get_category(scores['overall'])
        scores['color_code'] = self._get_color_code(scores['overall'])
        
        return scores
    
    def _calculate_skills_match(self, candidate_analysis, job_requirements):
        """Расчет соответствия навыков"""
        if not candidate_analysis.get('skills') or not job_requirements.get('required_skills'):
            return 50  # Базовая оценка при отсутствии данных
        
        # Получаем списки навыков (преобразуем в нижний регистр для совпадения)
        candidate_skills = [s.lower() for s in candidate_analysis['skills']]
        required_skills = [s.lower() for s in job_requirements['required_skills']]
        
        # Если требуемых навыков нет, возвращаем базовую оценку
        if not required_skills:
            return 50
        
        # Считаем совпадения
        matches = 0
        for skill in required_skills:
            # Проверяем точное совпадение или вхождение как подстроки
            if any(skill == cs or skill in cs for cs in candidate_skills):
                matches += 1
        
        # Рассчитываем процент совпадения
        match_percentage = (matches / len(required_skills)) * 100
        return match_percentage
    
    def _calculate_experience_score(self, candidate_analysis, job_requirements):
        """Расчет соответствия опыта работы"""
        # В простой реализации проверяем общий стаж
        required_years = job_requirements.get('required_years_experience', 0)
        
        if required_years == 0:
            return 50  # Базовая оценка при отсутствии требований к опыту
        
        # Пытаемся извлечь опыт кандидата (может быть в разных форматах)
        candidate_years = 0
        if isinstance(candidate_analysis.get('experience'), dict):
            # Если опыт представлен как объект с годами
            candidate_years = candidate_analysis['experience'].get('total_years', 0)
        elif isinstance(candidate_analysis.get('experience'), (int, float)):
            # Если опыт представлен как число
            candidate_years = candidate_analysis['experience']
        
        # Расчет скоринга по опыту
        if candidate_years >= required_years * 1.5:
            return 100  # Превышает требования на 50% и более
        elif candidate_years >= required_years:
            return 80  # Соответствует требованиям
        elif candidate_years >= required_years * 0.8:
            return 60  # Немного не дотягивает
        elif candidate_years >= required_years * 0.5:
            return 40  # Сильно не дотягивает
        else:
            return 20  # Значительно ниже требований
    
    def _calculate_education_score(self, candidate_analysis, job_requirements):
        """Расчет соответствия образования"""
        # Упрощенная реализация для MVP
        # В полной версии здесь будет сложная логика сравнения уровней образования
        
        # Базовая оценка
        score = 50
        
        # Если нет информации или требований - базовая оценка
        if not candidate_analysis.get('education') or not job_requirements.get('required_education'):
            return score
        
        # Уровни образования (в порядке возрастания)
        education_levels = {
            'среднее': 1,
            'среднее специальное': 2,
            'неоконченное высшее': 3,
            'бакалавр': 4,
            'высшее': 5,
            'магистр': 6,
            'кандидат наук': 7,
            'доктор наук': 8
        }
        
        # Определяем уровень образования кандидата и требуемый уровень
        candidate_education = candidate_analysis['education'].lower()
        required_education = job_requirements['required_education'].lower()
        
        candidate_level = 0
        required_level = 0
        
        # Находим уровень образования кандидата
        for level, value in education_levels.items():
            if level in candidate_education:
                candidate_level = value
                break
        
        # Находим требуемый уровень образования
        for level, value in education_levels.items():
            if level in required_education:
                required_level = value
                break
        
        # Если не удалось определить уровни - базовая оценка
        if candidate_level == 0 or required_level == 0:
            return score
        
        # Рассчитываем скоринг
        if candidate_level >= required_level + 2:
            return 100  # Значительно превышает требования
        elif candidate_level >= required_level:
            return 90  # Соответствует или превышает требования
        elif candidate_level == required_level - 1:
            return 70  # Немного не дотягивает
        else:
            return 40  # Не соответствует требованиям
    
    def _get_category(self, overall_score):
        """Определение категории кандидата по общему скорингу"""
        if overall_score >= 90:
            return "Отличный кандидат"
        elif overall_score >= 75:
            return "Хороший кандидат"
        elif overall_score >= 60:
            return "Подходящий кандидат"
        elif overall_score >= 40:
            return "Требует рассмотрения"
        else:
            return "Не соответствует требованиям"
    
    def _get_color_code(self, overall_score):
        """Определение цветового кода для визуализации скоринга"""
        if overall_score >= 90:
            return "#34d399"  # Зеленый
        elif overall_score >= 75:
            return "#4361ee"  # Синий
        elif overall_score >= 60:
            return "#fbbf24"  # Желтый
        elif overall_score >= 40:
            return "#f59e0b"  # Оранжевый
        else:
            return "#f87171"  # Красный
