import logging
import hashlib
import time
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from sqlalchemy.orm import Session

from app.database.models import File, AnalysisResult
from app.services.openai_service import OpenAIService
from app.services.file_service import FileService

# Настройка логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileNotFoundError(Exception):
    """Пользовательское исключение для отсутствующего файла в базе данных."""
    pass

class AnalysisService:
    def __init__(self, openai_service: OpenAIService, db: Session):
        self.openai_service = openai_service
        self.db = db

    def _get_file_or_raise(self, file_id: int) -> File:
        """
        Получает файл по ID или выбрасывает FileNotFoundError.
        """
        file = self.db.query(File).filter(File.id == file_id).first()
        if not file:
            logger.error(f"Файл с id={file_id} не найден в базе данных")
            raise FileNotFoundError(f"Файл с id={file_id} не найден в базе данных")
        return file
        
    async def analyze_resume_text(self, resume_text: str, job_description_text: str, 
                            resume_filename: str = "resume.pdf", job_description_filename: str = "job.pdf",
                            user_id: int = None) -> Dict[str, Any]:
        """
        Анализирует резюме и сравнивает его с описанием вакансии на основе текстового содержимого.
        
        Args:
            resume_text: Текст резюме
            job_description_text: Текст описания вакансии
            resume_filename: Имя файла резюме (для сохранения в базе данных)
            job_description_filename: Имя файла описания вакансии (для сохранения в базе данных)
            user_id: ID пользователя (для сохранения в базе данных)
            
        Returns:
            Dict[str, Any]: Результаты анализа
        """
        start_time = time.time()
        logger.info("Starting resume analysis from text content")
        
        try:
            # Создаем хеши текстов
            resume_hash = hashlib.sha256(resume_text.encode('utf-8')).hexdigest()
            job_hash = hashlib.sha256(job_description_text.encode('utf-8')).hexdigest()
            
            # Проверяем, есть ли уже результат анализа в БД
            existing_analysis = self.db.query(AnalysisResult).filter(
                AnalysisResult.results['resume_hash'].astext == resume_hash,
                AnalysisResult.results['job_hash'].astext == job_hash
            ).first()
            
            if existing_analysis:
                logger.info(f"Found existing analysis result in database: id={existing_analysis.id}")
                
                # Обновляем статистику использования
                existing_analysis.access_count += 1
                existing_analysis.last_accessed_at = datetime.now()
                self.db.commit()
                
                return existing_analysis.results
            
            # Выполняем анализ через OpenAI API
            logger.info("No existing analysis found, performing new analysis")
            analysis_result = await self.openai_service.analyze_resume(
                resume_text, 
                job_description_text
            )
            
            # Добавляем хеши в результат
            analysis_result["resume_hash"] = resume_hash
            analysis_result["job_hash"] = job_hash
            
            # Вычисляем общий скор если он отсутствует
            if "overall_match" in analysis_result and "score" in analysis_result["overall_match"]:
                score = float(analysis_result["overall_match"]["score"])
            else:
                # Если нет нового формата, пробуем использовать старый
                score = float(analysis_result.get("score", 0.0))
            
            # Вычисляем время обработки
            processing_time = time.time() - start_time
            
            # Сохраняем результат в базу данных
            file_service = FileService()
            
            # Сохраняем файлы в базу данных, если необходимо
            resume_file_id = None
            job_file_id = None
            
            if user_id:
                # Сохраняем резюме в базу данных
                resume_file = file_service.save_text_as_file(
                    self.db, resume_text, resume_filename, "resume", user_id, resume_hash
                )
                resume_file_id = resume_file.id
                
                # Сохраняем описание вакансии в базу данных
                job_file = file_service.save_text_as_file(
                    self.db, job_description_text, job_description_filename, "job_description", user_id, job_hash
                )
                job_file_id = job_file.id
            
            # Сохраняем результат анализа
            import copy
            stable_result = copy.deepcopy(analysis_result)
            
            new_analysis = AnalysisResult(
                resume_id=resume_file_id,
                job_description_id=job_file_id,
                score=score,
                results=stable_result,
                api_provider=self.openai_service.provider_name,
                api_model=self.openai_service.model,
                processing_time=processing_time,
                created_at=datetime.now(),
                last_accessed_at=datetime.now(),
                access_count=1
            )
            
            self.db.add(new_analysis)
            self.db.commit()
            self.db.refresh(new_analysis)
            
            logger.info(f"Created new analysis result: id={new_analysis.id}, processing_time={processing_time:.2f}s")
            return analysis_result
        
        except Exception as e:
            logger.error(f"Error during resume analysis: {str(e)}")
            raise
    
    async def analyze_resume(self, resume_file_id: int, job_description_file_id: int) -> Dict[str, Any]:
        """
        Анализирует резюме и сравнивает его с описанием вакансии.
        Использует детерминистический подход: для одинаковых файлов всегда возвращает одинаковый результат.
        
        Args:
            resume_file_id: ID файла резюме в базе данных
            job_description_file_id: ID файла описания вакансии в базе данных
            
        Returns:
            Dict[str, Any]: Результаты анализа
        """
        start_time = time.time()
        logger.info(f"Starting resume analysis for resume_id={resume_file_id} and job_id={job_description_file_id}")
        
        # Получаем файлы из базы данных
        resume_file = self._get_file_or_raise(resume_file_id)
        job_file = self._get_file_or_raise(job_description_file_id)

        # Проверяем, есть ли уже результат анализа в БД
        with self.db.begin():
            existing_analysis = self.db.query(AnalysisResult).filter(
                AnalysisResult.resume_id == resume_file_id,
                AnalysisResult.job_description_id == job_description_file_id
            ).first()
            
            if existing_analysis:
                logger.info(f"Found existing analysis result in database: id={existing_analysis.id}")
                
                # Обновляем статистику использования
                existing_analysis.access_count += 1
                existing_analysis.last_accessed_at = datetime.now()
                self.db.commit()
                
                return existing_analysis.results
            
            # Выполняем анализ через OpenAI API или мок-данные
            logger.info("No existing analysis found, performing new analysis")
            analysis_result = await self.openai_service.analyze_resume(
                resume_file.content, 
                job_file.content
            )
            
            # Вычисляем время обработки
            processing_time = time.time() - start_time
            
            # Сохраняем результат в базу данных
            import copy
            stable_result = copy.deepcopy(analysis_result)
            keys_to_remove = [k for k in stable_result if k.startswith('_')]
            for k in keys_to_remove:
                del stable_result[k]
            new_analysis = AnalysisResult(
                resume_id=resume_file_id,
                job_description_id=job_description_file_id,
                score=analysis_result.get('overall_score', 0.0),
                results=stable_result,
                api_provider=self.openai_service.provider_name,
                api_model=self.openai_service.model,
                processing_time=processing_time,
                created_at=datetime.now(),
                last_accessed_at=datetime.now(),
                access_count=1
            )
            
            self.db.add(new_analysis)
            self.db.commit()
            self.db.refresh(new_analysis)
            
            logger.info(f"Created new analysis result: id={new_analysis.id}, processing_time={processing_time:.2f}s")
            return analysis_result
        
        # Добавляем метаданные в результаты
        total_time = time.time() - start_time
        results["_meta"] = {
            "cached": False,
            "cache_id": analysis.id,
            "api_time": api_time,
            "total_time": total_time
        }
        
        return results
    
    async def extract_skills(self, text_file_id: int) -> Dict[str, Any]:
        """
        Извлекает навыки из текста (резюме или описания вакансии)
        
        Args:
            text_file_id: ID файла в базе данных
            
        Returns:
            Dict[str, Any]: Извлеченные навыки
        """
        logger.info(f"Extracting skills from file id={text_file_id}")
        
        # Получаем файл из базы данных
        file = self._get_file_or_raise(text_file_id)
        # Проверяем, есть ли уже результат в кэше
        cache_key = f"skills-{file.file_hash}"
        existing_analysis = self.db.query(AnalysisResult).filter(
            AnalysisResult.results['type'].astext == 'skills_extraction',
            AnalysisResult.results['cache_key'].astext == cache_key
        ).first()
        
        if existing_analysis:
            logger.info(f"Found cached skills analysis: id={existing_analysis.id}")
            return existing_analysis.results
        
        # Извлекаем навыки через OpenAI
        logger.info("No cached skills found, calling OpenAI API")
        skills = await self.openai_service.extract_skills(file.content)
        
        # Сохраняем как специальный тип анализа
        new_analysis = AnalysisResult(
            resume_id=text_file_id if file.file_type == 'resume' else None,
            job_description_id=text_file_id if file.file_type == 'job_description' else None,
            score=1.0,  # Не используется для этого типа анализа
            results={
                'type': 'skills_extraction',
                'skills': skills,
                'cache_key': cache_key
            },
            api_provider=self.openai_service.provider_name,
            api_model=self.openai_service.model,
            created_at=datetime.now()
        )
        
        self.db.add(new_analysis)
        self.db.commit()
        
        return skills
    
    async def identify_sections(self, resume_file_id: int) -> Dict[str, Any]:
        """
        Идентифицирует разделы в резюме
        
        Args:
            resume_file_id: ID файла резюме в базе данных
            
        Returns:
            Dict[str, Any]: Информация о разделах резюме
        """
        logger.info(f"Identifying sections in resume id={resume_file_id}")
        
        # Получаем файл из базы данных
        file = self._get_file_or_raise(resume_file_id)
        # Проверяем, есть ли уже результат в кэше
        cache_key = f"sections-{file.file_hash}"
        existing_analysis = self.db.query(AnalysisResult).filter(
            AnalysisResult.results['type'].astext == 'sections_identification',
            AnalysisResult.results['cache_key'].astext == cache_key
        ).first()
        
        if existing_analysis:
            logger.info(f"Found cached sections analysis: id={existing_analysis.id}")
            return existing_analysis.results
        
        # Идентифицируем разделы через OpenAI
        logger.info("No cached sections found, calling OpenAI API")
        sections = await self.openai_service.identify_sections(file.content)
        
        # Сохраняем как специальный тип анализа
        new_analysis = AnalysisResult(
            resume_id=resume_file_id,
            job_description_id=None,
            score=1.0,  # Не используется для этого типа анализа
            results={
                'type': 'sections_identification',
                'sections': sections,
                'cache_key': cache_key
            },
            api_provider=self.openai_service.provider_name,
            api_model=self.openai_service.model,
            created_at=datetime.now()
        )
        
        self.db.add(new_analysis)
        self.db.commit()
        
        return sections
    
    def get_analysis_history(self, db: Session, user_id: int, limit: int = 10) -> Dict[str, Any]:
        """
        Получает историю анализов пользователя
        """
        # Ищем все анализы, где резюме принадлежит пользователю
        analyses = (
            db.query(AnalysisResult)
            .join(File, AnalysisResult.resume_id == File.id)
            .filter(File.user_id == user_id)
            .order_by(AnalysisResult.created_at.desc())
            .limit(limit)
            .all()
        )
        history = []
        for analysis in analyses:
            history.append({
                "id": analysis.id,
                "resume": {
                    "filename": analysis.resume.filename,
                    "created_at": analysis.resume.created_at.isoformat()
                },
                "job_description": {
                    "filename": analysis.job_description.filename if analysis.job_description else None,
                    "created_at": analysis.job_description.created_at.isoformat() if analysis.job_description else None
                },
                "score": analysis.score,
                "created_at": analysis.created_at.isoformat()
            })
        return {
            "count": len(history),
            "analyses": history
        }
    
    def get_analysis_by_id(self, db: Session, analysis_id: int) -> Optional[Dict[str, Any]]:
        """Получает детальную информацию по анализу по его ID"""
        analysis = db.query(AnalysisResult).filter(AnalysisResult.id == analysis_id).first()
        if not analysis:
            return None
            
        # Нормализация результата, если нужно
        result = {
            "id": analysis.id,
            "resume": {
                "filename": analysis.resume.filename,
                "created_at": analysis.resume.created_at.isoformat(),
                "user_id": analysis.resume.user_id
            },
            "job_description": {
                "filename": analysis.job_description.filename if analysis.job_description else None,
                "created_at": analysis.job_description.created_at.isoformat() if analysis.job_description else None
            },
            "score": analysis.score,
            "results": analysis.results,
            "created_at": analysis.created_at.isoformat()
        }
        
        return result
    
    def clear_old_cache(self, db: Session) -> int:
        """
        Очищает старые записи кэша
        """
        return self.cache_service.clear_old_cache(db)
