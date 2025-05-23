from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.db.database import Base
import datetime

class VideoInterview(Base):
    """Модель видеоинтервью"""
    __tablename__ = "video_interviews"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=True)
    vacancy_id = Column(Integer, ForeignKey("vacancies.id"), nullable=True)
    file_path = Column(String)  # Путь к файлу видео
    original_filename = Column(String)  # Исходное имя файла
    duration = Column(Float, nullable=True)  # Длительность видео в секундах
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Отношения с другими таблицами
    candidate = relationship("Candidate", back_populates="video_interviews")
    vacancy = relationship("Vacancy", back_populates="video_interviews")
    
    # Можно добавить отношение с анализом видео, если это будет реализовано
    # analysis = relationship("VideoAnalysis", back_populates="video")
