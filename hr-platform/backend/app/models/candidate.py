from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base
import datetime

class Candidate(Base):
    """Модель кандидата"""
    __tablename__ = "candidates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    phone = Column(String, nullable=True)
    resume_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Отношения с другими таблицами
    analyses = relationship("Analysis", back_populates="candidate")
    video_interviews = relationship("VideoInterview", back_populates="candidate")

class Analysis(Base):
    """Модель анализа резюме"""
    __tablename__ = "analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=True)
    vacancy_id = Column(Integer, ForeignKey("vacancies.id"), nullable=True)
    analysis_date = Column(DateTime, default=datetime.datetime.utcnow)
    analysis_results = Column(JSON)  # Результат анализа в JSON
    overall_score = Column(Float)  # Общий скоринг (0-100)
    
    # Отношения с другими таблицами
    candidate = relationship("Candidate", back_populates="analyses")
    vacancy = relationship("Vacancy", back_populates="analyses")

class Vacancy(Base):
    """Модель вакансии"""
    __tablename__ = "vacancies"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    requirements = Column(String)
    skills = Column(String)  # Навыки, разделенные запятыми
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Отношения с другими таблицами
    analyses = relationship("Analysis", back_populates="vacancy")
    video_interviews = relationship("VideoInterview", back_populates="vacancy")
