from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Boolean, Index, UniqueConstraint
from sqlalchemy.types import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database.models import Base, User

class Vacancy(Base):
    __tablename__ = "vacancies"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True, nullable=False)
    description = Column(Text, nullable=False)
    requirements = Column(JSONB, nullable=False)  # Хранение списка требований в формате JSON
    interview_type = Column(String(50), nullable=False)  # "smart" или "manual"
    evaluation_criteria = Column(JSONB, nullable=False)  # Критерии оценки в JSON формате
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Отношения
    interviews = relationship("Interview", back_populates="vacancy", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Vacancy {self.title}>"

class Interview(Base):
    __tablename__ = "interviews"
    
    id = Column(Integer, primary_key=True, index=True)
    vacancy_id = Column(Integer, ForeignKey("vacancies.id"), nullable=False)
    candidate_name = Column(String(255), nullable=True)
    candidate_email = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="ожидается")  # "ожидается", "в процессе", "завершено"
    access_link = Column(String(255), unique=True, index=True, nullable=False)
    meeting_id = Column(String(255), nullable=True)  # ID Zoom-встречи
    meeting_password = Column(String(100), nullable=True)  # Пароль Zoom-встречи
    scheduled_at = Column(DateTime(timezone=True), nullable=True)  # Планируемое время интервью
    completed_at = Column(DateTime(timezone=True), nullable=True)  # Время завершения интервью
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Отношения
    vacancy = relationship("Vacancy", back_populates="interviews")
    report = relationship("InterviewReport", uselist=False, back_populates="interview", 
                         cascade="all, delete-orphan")
    questions = relationship("InterviewQuestion", back_populates="interview", 
                            cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Interview {self.id} for Vacancy {self.vacancy_id} - Status: {self.status}>"

class InterviewQuestion(Base):
    __tablename__ = "interview_questions"
    
    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    order = Column(Integer, nullable=False)  # Порядок вопроса в интервью
    category = Column(String(100), nullable=True)  # Категория вопроса (технический, поведенческий и т.д.)
    is_required = Column(Boolean, default=True)
    
    # Отношения
    interview = relationship("Interview", back_populates="questions")
    answer = relationship("InterviewAnswer", uselist=False, back_populates="question",
                         cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Question {self.id}: {self.question_text[:30]}...>"

class InterviewAnswer(Base):
    __tablename__ = "interview_answers"
    
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("interview_questions.id"), nullable=False)
    answer_text = Column(Text, nullable=True)
    audio_file = Column(String(255), nullable=True)  # Путь к аудиофайлу с ответом
    transcription = Column(Text, nullable=True)  # Текстовая расшифровка ответа
    analysis = Column(JSONB, nullable=True)  # Анализ ответа системой
    score = Column(Float, nullable=True)  # Оценка ответа (1-5)
    
    # Отношения
    question = relationship("InterviewQuestion", back_populates="answer")
    
    def __repr__(self):
        return f"<Answer {self.id} for Question {self.question_id}>"

class InterviewReport(Base):
    __tablename__ = "interview_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False)
    video_url = Column(String(255), nullable=True)  # Ссылка на запись видео
    total_score = Column(Float, nullable=True)  # Общий балл за интервью
    analysis_summary = Column(Text, nullable=True)  # Краткое резюме анализа
    strengths = Column(JSONB, nullable=True)  # Сильные стороны кандидата
    weaknesses = Column(JSONB, nullable=True)  # Слабые стороны кандидата
    recommendation = Column(String(100), nullable=True)  # "Подходит", "Требует дополнительного интервью", "Не подходит"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Отношения
    interview = relationship("Interview", back_populates="report")
    
    def __repr__(self):
        return f"<Report {self.id} for Interview {self.interview_id}>"

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(100), nullable=False)  # "interview_completed", "vacancy_created", etc.
    is_read = Column(Boolean, default=False)
    related_interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=True)
    related_vacancy_id = Column(Integer, ForeignKey("vacancies.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<Notification {self.id} for User {self.user_id}: {self.title}>"

# Добавляем обратные связи в модель User
User.vacancies = relationship("Vacancy", backref="user", cascade="all, delete-orphan")
User.notifications = relationship("Notification", backref="user", cascade="all, delete-orphan")
