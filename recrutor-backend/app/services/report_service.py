import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from fpdf import FPDF
import pandas as pd
from sqlalchemy.orm import Session
from app.services.analysis_service import AnalysisService


class ReportService:
    """Сервис для генерации отчетов на основе результатов анализа резюме"""
    
    def __init__(self, analysis_service: AnalysisService):
        self.analysis_service = analysis_service
        self.reports_dir = os.path.join(os.getcwd(), "reports")
        os.makedirs(self.reports_dir, exist_ok=True)
    
    def generate_pdf_report(self, db: Session, analysis_id: int) -> str:
        """Генерирует PDF-отчет на основе анализа резюме"""
        analysis_data = self.analysis_service.get_analysis_by_id(db, analysis_id)
        if not analysis_data:
            raise ValueError(f"Анализ с ID {analysis_id} не найден")
        
        # Создаем PDF документ
        pdf = FPDF()
        pdf.add_page()
        
        # Используем базовый шрифт для простоты
        # На продакшене можно будет добавить кириллические шрифты
        pdf.set_font('Arial', '', 12)
        
        # Заголовок отчета
        pdf.set_font('Arial', '', 16)
        pdf.cell(0, 10, "Отчет по анализу резюме", 0, 1, 'C')
        
        # Дата
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 10, f"Дата создания: {datetime.now().strftime('%d.%m.%Y %H:%M')}", 0, 1, 'R')
        
        # Общая информация
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, f"Резюме: {analysis_data['resume']['filename']}", 0, 1)
        pdf.cell(0, 10, f"Вакансия: {analysis_data['job_description']['filename']}", 0, 1)
        
        # Общий процент соответствия
        overall_match = analysis_data['results']['overall_match']
        pdf.set_font('Arial', '', 14)
        pdf.cell(0, 10, f"Общий процент соответствия: {overall_match['score']}%", 0, 1)
        
        # Резюме анализа
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, "Резюме анализа:", 0, 1)
        self._add_multi_line_text(pdf, overall_match['summary'])
        
        # Сильные стороны
        pdf.set_font('DejaVu', '', 12)
        pdf.cell(0, 10, "Сильные стороны:", 0, 1)
        for strength in overall_match['strengths']:
            pdf.cell(10, 10, "•", 0, 0)
            pdf.cell(0, 10, strength, 0, 1)
        
        # Слабые стороны
        pdf.cell(0, 10, "Слабые стороны:", 0, 1)
        for weakness in overall_match['weaknesses']:
            pdf.cell(10, 10, "•", 0, 0)
            pdf.cell(0, 10, weakness, 0, 1)
        
        # Анализ навыков
        pdf.add_page()
        pdf.set_font('Arial', '', 14)
        pdf.cell(0, 10, "Анализ навыков", 0, 1)
        
        skills = analysis_data['results']['skills_analysis']
        for i, skill in enumerate(skills):
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 10, f"{skill['skill']} - {skill['match']}% соответствие", 0, 1)
            pdf.set_font('Arial', '', 10)
            pdf.cell(10, 10, "", 0, 0)
            pdf.cell(0, 10, f"Категория: {skill['category']}", 0, 1)
            pdf.cell(10, 10, "", 0, 0)
            pdf.cell(0, 10, f"Релевантность: {skill['relevance']}", 0, 1)
            pdf.cell(10, 10, "", 0, 0)
            pdf.cell(0, 10, f"Контекст: {skill['context']}", 0, 1)
            if i < len(skills) - 1:
                pdf.cell(0, 5, "", 0, 1)
        
        # Опыт работы
        pdf.add_page()
        pdf.set_font('Arial', '', 14)
        pdf.cell(0, 10, "Опыт работы", 0, 1)
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, f"Соответствие опыта: {analysis_data['results']['experience']['match']}%", 0, 1)
        self._add_multi_line_text(pdf, analysis_data['results']['experience']['summary'])
        
        experience_details = analysis_data['results']['experience']['details']
        for i, exp in enumerate(experience_details):
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 10, f"{exp['position']} - {exp['company']}", 0, 1)
            pdf.set_font('Arial', '', 10)
            pdf.cell(10, 10, "", 0, 0)
            pdf.cell(0, 10, f"Период: {exp['period']}", 0, 1)
            pdf.cell(10, 10, "", 0, 0)
            pdf.cell(0, 10, f"Релевантность: {exp['relevance']}%", 0, 1)
            pdf.cell(10, 10, "", 0, 0)
            pdf.cell(0, 10, "Ключевые моменты:", 0, 1)
            for highlight in exp['highlights']:
                pdf.cell(20, 10, "•", 0, 0)
                pdf.cell(0, 10, highlight, 0, 1)
            if i < len(experience_details) - 1:
                pdf.cell(0, 5, "", 0, 1)
        
        # Образование
        pdf.add_page()
        pdf.set_font('Arial', '', 14)
        pdf.cell(0, 10, "Образование", 0, 1)
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, f"Соответствие образования: {analysis_data['results']['education']['match']}%", 0, 1)
        self._add_multi_line_text(pdf, analysis_data['results']['education']['summary'])
        
        education_details = analysis_data['results']['education']['details']
        for i, edu in enumerate(education_details):
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 10, f"{edu['degree']}", 0, 1)
            pdf.set_font('Arial', '', 10)
            pdf.cell(10, 10, "", 0, 0)
            pdf.cell(0, 10, f"Учебное заведение: {edu['institution']}", 0, 1)
            pdf.cell(10, 10, "", 0, 0)
            pdf.cell(0, 10, f"Год: {edu['year']}", 0, 1)
            pdf.cell(10, 10, "", 0, 0)
            pdf.cell(0, 10, f"Релевантность: {edu['relevance']}%", 0, 1)
            if i < len(education_details) - 1:
                pdf.cell(0, 5, "", 0, 1)
        
        # Рекомендуемые вопросы для интервью
        pdf.add_page()
        pdf.set_font('Arial', '', 14)
        pdf.cell(0, 10, "Рекомендуемые вопросы для интервью", 0, 1)
        
        interview_questions = analysis_data['results']['interview_questions']
        for i, question in enumerate(interview_questions):
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 10, f"Вопрос {i+1}: {question['question']}", 0, 1)
            pdf.set_font('Arial', '', 10)
            pdf.cell(10, 10, "", 0, 0)
            pdf.cell(0, 10, f"Цель: {question['purpose']}", 0, 1)
            pdf.cell(10, 10, "", 0, 0)
            pdf.cell(0, 10, f"Связано с: {question['related_to']}", 0, 1)
            if i < len(interview_questions) - 1:
                pdf.cell(0, 5, "", 0, 1)
        
        # Сохраняем отчет
        filename = f"report_analysis_{analysis_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(self.reports_dir, filename)
        pdf.output(filepath)
        
        return filepath
    
    def generate_excel_report(self, db: Session, analysis_id: int) -> str:
        """Генерирует Excel-отчет на основе анализа резюме"""
        analysis_data = self.analysis_service.get_analysis_by_id(db, analysis_id)
        if not analysis_data:
            raise ValueError(f"Анализ с ID {analysis_id} не найден")
        
        # Создаем Excel-файл
        filename = f"report_analysis_{analysis_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = os.path.join(self.reports_dir, filename)
        
        # Используем pandas для создания Excel с несколькими листами
        with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
            # Общая информация
            general_info = {
                'Информация': ['Резюме', 'Вакансия', 'Дата анализа', 'Общий % соответствия', 'Резюме анализа'],
                'Значение': [
                    analysis_data['resume']['filename'],
                    analysis_data['job_description']['filename'],
                    datetime.now().strftime('%d.%m.%Y %H:%M'),
                    analysis_data['results']['overall_match']['score'],
                    analysis_data['results']['overall_match']['summary']
                ]
            }
            pd.DataFrame(general_info).to_excel(writer, sheet_name='Общая информация', index=False)
            
            # Сильные и слабые стороны
            strengths = [{'Пункт': s} for s in analysis_data['results']['overall_match']['strengths']]
            weaknesses = [{'Пункт': w} for w in analysis_data['results']['overall_match']['weaknesses']]
            
            pd.DataFrame(strengths).to_excel(writer, sheet_name='Сильные стороны', index=False)
            pd.DataFrame(weaknesses).to_excel(writer, sheet_name='Слабые стороны', index=False)
            
            # Навыки
            skills_df = pd.DataFrame(analysis_data['results']['skills_analysis'])
            skills_df.to_excel(writer, sheet_name='Навыки', index=False)
            
            # Опыт работы
            experience_summary = {
                'Показатель': ['Общий % соответствия опыта', 'Резюме'],
                'Значение': [
                    analysis_data['results']['experience']['match'],
                    analysis_data['results']['experience']['summary']
                ]
            }
            pd.DataFrame(experience_summary).to_excel(writer, sheet_name='Опыт (общее)', index=False)
            
            # Детальный опыт
            experience_details_list = []
            for exp in analysis_data['results']['experience']['details']:
                exp_dict = {
                    'Должность': exp['position'],
                    'Компания': exp['company'],
                    'Период': exp['period'],
                    'Релевантность (%)': exp['relevance']
                }
                
                # Добавляем ключевые моменты через запятую
                exp_dict['Ключевые моменты'] = ', '.join(exp['highlights'])
                experience_details_list.append(exp_dict)
            
            if experience_details_list:
                pd.DataFrame(experience_details_list).to_excel(writer, sheet_name='Опыт (детали)', index=False)
            
            # Образование
            education_summary = {
                'Показатель': ['Общий % соответствия образования', 'Резюме'],
                'Значение': [
                    analysis_data['results']['education']['match'],
                    analysis_data['results']['education']['summary']
                ]
            }
            pd.DataFrame(education_summary).to_excel(writer, sheet_name='Образование (общее)', index=False)
            
            # Детальное образование
            if analysis_data['results']['education']['details']:
                education_df = pd.DataFrame(analysis_data['results']['education']['details'])
                education_df.to_excel(writer, sheet_name='Образование (детали)', index=False)
            
            # Вопросы для интервью
            questions_df = pd.DataFrame(analysis_data['results']['interview_questions'])
            questions_df.to_excel(writer, sheet_name='Вопросы для интервью', index=False)
            
            # Настраиваем форматирование (ширину столбцов)
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for i, col in enumerate(worksheet.worksheets[0].table.cols):
                    worksheet.set_column(i, i, 30)
        
        return filepath
    
    def _add_multi_line_text(self, pdf: FPDF, text: str, max_width: int = 180):
        """Добавляет многострочный текст в PDF"""
        lines = pdf.multi_cell(0, 10, text, 0, 1)
        pdf.ln(3)
