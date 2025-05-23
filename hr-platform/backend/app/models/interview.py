from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Boolean, Text
from sqlalchemy.orm import relationship
from app.db.database import Base
import datetime

class Interview(Base):
    """Модель интервью с AI"""
    __tablename__ = "interviews"
    
    id = Column(Integer, primary_key=True, index=True)
    vacancy_id = Column(Integer, ForeignKey("vacancies.id"))
    title = Column(String)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    questions = Column(JSON)  # Список вопросов в JSON
    zoom_meeting_id = Column(String, nullable=True)
    zoom_meeting_url = Column(String, nullable=True)
    status = Column(String)  # scheduled, completed, cancelled
    
    # Отношения
    vacancy = relationship("Vacancy", back_populates="interviews")
    candidates = relationship("InterviewCandidate", back_populates="interview")

class InterviewCandidate(Base):
    """Связь кандидата с интервью"""
    __tablename__ = "interview_candidates"
    
    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"))
    candidate_id = Column(Integer, ForeignKey("candidates.id"))
    scheduled_at = Column(DateTime)
    completed = Column(Boolean, default=False)
    answers = Column(JSON, nullable=True)  # Ответы кандидата в JSON
    analysis = Column(JSON, nullable=True)  # Анализ ответов
    report_path = Column(String, nullable=True)  # Путь к PDF-отчету
    
    # Отношения
    interview = relationship("Interview", back_populates="candidates")
    candidate = relationship("Candidate", back_populates="interviews")
