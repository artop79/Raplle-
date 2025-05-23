"""
Sqlite-совместимые версии HR-моделей
"""
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Boolean, Index, UniqueConstraint
from sqlalchemy.types import JSON  # Используем стандартный JSON вместо JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database.models import Base, User

class Vacancy(Base):
    __tablename__ = "vacancies"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True, nullable=False)
    description = Column(Text, nullable=False)
    requirements = Column(JSON, nullable=False)  # JSON вместо JSONB
    interview_type = Column(String(50), nullable=False)
    evaluation_criteria = Column(JSON, nullable=False)  # JSON вместо JSONB
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

class Interview(Base):
    __tablename__ = "interviews"
    
    id = Column(Integer, primary_key=True, index=True)
    vacancy_id = Column(Integer, ForeignKey("vacancies.id"), nullable=True)
    candidate_name = Column(String(255), nullable=True)
    candidate_email = Column(String(255), nullable=True)
    status = Column(String(50), nullable=True, default="ожидается")
    access_link = Column(String(255), unique=True, index=True, nullable=True)
    meeting_id = Column(String(255), nullable=True)
    meeting_password = Column(String(100), nullable=True)
    zoom_meeting_id = Column(String(32), nullable=True)  # Для совместимости со старой структурой
    join_url = Column(String(512), nullable=True)  # Для совместимости со старой структурой
    start_url = Column(String(512), nullable=True)  # Для совместимости со старой структурой
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    scheduled_time = Column(DateTime(timezone=True), nullable=True)  # Для совместимости со старой структурой
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    transcript = Column(Text, nullable=True)  # Для совместимости со старой структурой
    candidate_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Для совместимости со старой структурой
    job_id = Column(Integer, nullable=True)  # Для совместимости со старой структурой

class InterviewQuestion(Base):
    __tablename__ = "interview_questions"
    
    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    order = Column(Integer, nullable=False)
    category = Column(String(100), nullable=True)
    is_required = Column(Boolean, default=True)

class InterviewAnswer(Base):
    __tablename__ = "interview_answers"
    
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("interview_questions.id"), nullable=False)
    answer_text = Column(Text, nullable=True)
    audio_file = Column(String(255), nullable=True)
    transcription = Column(Text, nullable=True)
    analysis = Column(JSON, nullable=True)  # JSON вместо JSONB
    score = Column(Float, nullable=True)

class InterviewReport(Base):
    __tablename__ = "interview_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False)
    video_url = Column(String(255), nullable=True)
    total_score = Column(Float, nullable=True)
    analysis_summary = Column(Text, nullable=True)
    strengths = Column(JSON, nullable=True)  # JSON вместо JSONB
    weaknesses = Column(JSON, nullable=True)  # JSON вместо JSONB
    recommendation = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class InterviewResult(Base):
    __tablename__ = "interview_results"
    
    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False)
    result_json = Column(JSON, nullable=False)  # JSON вместо JSONB или PostgreSQL JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(100), nullable=False)
    is_read = Column(Boolean, default=False)
    related_interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=True)
    related_vacancy_id = Column(Integer, ForeignKey("vacancies.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
