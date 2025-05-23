from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Boolean, Index, UniqueConstraint
from sqlalchemy.types import JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    username = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    files = relationship("File", back_populates="user")
    
    def __repr__(self):
        return f"<User {self.username}>"

class File(Base):
    __tablename__ = "files"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_type = Column(String(20), nullable=False)  # "resume" или "job_description"
    filename = Column(String(255), nullable=False)
    file_hash = Column(String(64), index=True, nullable=False)  # SHA256 хеш содержимого
    content = Column(Text, nullable=False)  # извлеченный текст документа
    original_size = Column(Integer)  # размер оригинального файла в байтах
    mime_type = Column(String(100))  # MIME-тип (application/pdf, application/docx и т.д.)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="files")
    resume_analyses = relationship("AnalysisResult", foreign_keys="AnalysisResult.resume_id", back_populates="resume")
    job_description_analyses = relationship("AnalysisResult", foreign_keys="AnalysisResult.job_description_id", back_populates="job_description")
    
    # Создаем уникальный индекс по хешу файла и типу файла
    # Это предотвратит дублирование одинаковых файлов в базе
    __table_args__ = (UniqueConstraint('file_hash', 'file_type', name='uix_file_hash_type'),)
    
    def __repr__(self):
        return f"<File {self.filename} ({self.file_type})>"

class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    
    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("files.id"), nullable=False)
    job_description_id = Column(Integer, ForeignKey("files.id"), nullable=False)
    score = Column(Float, nullable=False)  # общая оценка соответствия
    results = Column(JSON, nullable=False)  # полные результаты анализа в JSON
    api_provider = Column(String(50), nullable=False)  # 'openai', 'mock', и т.д.
    api_model = Column(String(50), nullable=True)  # 'gpt-3.5-turbo', 'gpt-4', и т.д.
    processing_time = Column(Float)  # время обработки в секундах
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_accessed_at = Column(DateTime(timezone=True), server_default=func.now())
    access_count = Column(Integer, default=1)  # счетчик использований результата
    
    resume = relationship("File", foreign_keys=[resume_id], back_populates="resume_analyses")
    job_description = relationship("File", foreign_keys=[job_description_id], back_populates="job_description_analyses")
    feedbacks = relationship("AnalysisFeedback", back_populates="analysis_result")
    
    # Создаем уникальный индекс по resume_id и job_description_id
    # Это гарантирует, что для каждой пары файлов будет только один результат анализа
    __table_args__ = (UniqueConstraint('resume_id', 'job_description_id', name='uix_analysis_files'),)
    
    def __repr__(self):
        return f"<AnalysisResult score={self.score} resume_id={self.resume_id} job_id={self.job_description_id}>"

class AnalysisFeedback(Base):
    __tablename__ = "analysis_feedback"
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analysis_results.id"), nullable=False, index=True)
    hr_rating = Column(Integer, nullable=False)  # Оценка HR (1-5)
    hr_comment = Column(Text, nullable=True)     # Комментарий HR
    is_successful = Column(Boolean, nullable=True)  # Принят ли кандидат (True/False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    analysis_result = relationship("AnalysisResult", back_populates="feedbacks")

    def __repr__(self):
        return f"<AnalysisFeedback analysis_id={self.analysis_id} rating={self.hr_rating} success={self.is_successful}>"

# Индексы для улучшения производительности запросов
Index('idx_file_hash', File.file_hash)
Index('idx_file_user_type', File.user_id, File.file_type)
Index('idx_analysis_results_score', AnalysisResult.score)
Index('idx_analysis_results_date', AnalysisResult.created_at)
