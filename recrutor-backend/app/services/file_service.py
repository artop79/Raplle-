import os
import hashlib
import tempfile
from datetime import datetime
from typing import Optional, Dict, Tuple, Any, Union

import PyPDF2
import docx2txt
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.database.models import File, AnalysisResult

class FileService:
    def save_text_as_file(self, db: Session, text: str, filename: str, file_type: str, user_id: int, 
                         file_hash: Optional[str] = None) -> File:
        """
        Сохраняет текст как файл в базе данных
        
        Args:
            db: Сессия базы данных
            text: Текстовое содержимое для сохранения
            filename: Имя файла
            file_type: Тип файла ('resume' или 'job_description')
            user_id: ID пользователя
            file_hash: Опциональный хеш файла (если уже вычислен)
            
        Returns:
            Объект File из базы данных
        """
        # Проверяем, есть ли файл уже в базе данных
        if not file_hash:
            file_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        
        existing_file = db.query(File).filter(
            File.file_hash == file_hash,
            File.file_type == file_type,
            File.user_id == user_id
        ).first()
        
        if existing_file:
            # Файл уже существует, обновляем дату последнего доступа
            existing_file.last_accessed_at = datetime.now()
            db.commit()
            return existing_file
        
        # Создаем новый файл
        new_file = File(
            filename=filename,
            file_type=file_type,
            file_hash=file_hash,
            content=text,
            content_size=len(text.encode('utf-8')),
            user_id=user_id,
            created_at=datetime.now(),
            last_accessed_at=datetime.now(),
            access_count=1
        )
        
        db.add(new_file)
        db.commit()
        db.refresh(new_file)
        
        return new_file
        
    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Нормализует текст: удаляет лишние пробелы, приводит к нижнему регистру, убирает лишние переводы строк.
        """
        if not text:
            return ''
        # Удаляем лишние пробелы и переводы строк, приводим к нижнему регистру
        text = text.replace('\r', ' ').replace('\n', ' ')
        text = ' '.join(text.split())
        return text.strip().lower()
    @staticmethod
    async def process_file(file: UploadFile, file_type: str, user_id: int, db: Session) -> File:
        # ...
        # После извлечения текста:
        text = FileService.normalize_text(text)
        # ...
        """
        Обрабатывает файл: извлекает текст, создает хеш, сохраняет в БД
        
        Args:
            file: Загруженный файл
            file_type: Тип файла ('resume' или 'job_description')
            user_id: ID пользователя
            db: Сессия базы данных
            
        Returns:
            Объект File из базы данных
        """
        print(f"Processing {file_type} file: {file.filename}")
        
        # Читаем содержимое файла
        file_content = await file.read()
        file.file.seek(0)  # Сбрасываем указатель чтения для повторного использования
        
        # Извлекаем текст из файла
        extracted_text = await FileService.extract_text_from_file(file, file_content)
        if not extracted_text:
            raise ValueError(f"Could not extract text from {file.filename}")
            
        # Создаем хеш содержимого
        file_hash = FileService.calculate_hash(extracted_text)
        print(f"Hash for {file.filename}: {file_hash[:8]}...")
        
        # Проверяем, есть ли файл с таким хешем в БД
        with db.begin():
            # Используем with_for_update для блокировки при параллельных запросах
            existing_file = db.query(File).filter(
                File.file_hash == file_hash,
                File.file_type == file_type
            ).with_for_update().first()
            
            if existing_file:
                print(f"Found existing file in DB with same hash: {existing_file.id}")
                # Обновляем время последнего использования
                existing_file.last_used_at = datetime.now()
                db.commit()
                return existing_file
            
            # Создаем новую запись
            file_record = File(
                user_id=user_id,
                file_type=file_type,
                filename=file.filename,
                file_hash=file_hash,
                content=extracted_text,
                original_size=len(file_content),
                mime_type=file.content_type,
                created_at=datetime.now(),
                last_used_at=datetime.now()
            )
            
            db.add(file_record)
            db.commit()
            db.refresh(file_record)
            
            print(f"Created new file record in DB: {file_record.id}")
            return file_record
    
    @staticmethod
    async def extract_text_from_file(file: UploadFile, content: bytes = None) -> Optional[str]:
        """Извлекает текст из различных типов файлов (PDF, DOCX, TXT)"""
        if content is None:
            content = await file.read()
            file.file.seek(0)  # Сбрасываем указатель для повторного использования
        
        filename = file.filename.lower()
        
        try:
            if filename.endswith('.pdf'):
                return FileService._extract_text_from_pdf(content)
            elif filename.endswith('.docx'):
                return FileService._extract_text_from_docx(content)
            elif filename.endswith('.txt'):
                return content.decode('utf-8')
            else:
                raise ValueError(f"Unsupported file format: {filename}")
        except Exception as e:
            print(f"Error extracting text from file {filename}: {str(e)}")
            return None
    
    @staticmethod
    def calculate_hash(content: str) -> str:
        """Вычисляет SHA-256 хеш содержимого"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    @staticmethod
    def _extract_text_from_pdf(content: bytes) -> str:
        """Извлекает текст из PDF файла"""
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(content)
        
        # Извлекаем текст
        text = ""
        try:
            with open(temp_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
        finally:
            # Удаляем временный файл
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
        return text
    
    @staticmethod
    def _extract_text_from_docx(content: bytes) -> str:
        """Извлекает текст из DOCX файла"""
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(content)
        
        # Извлекаем текст
        try:
            text = docx2txt.process(temp_path)
        finally:
            # Удаляем временный файл
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
        return text
