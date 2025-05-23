import datetime
from sqlalchemy.orm import Session
from app.database.models import AnalysisResult
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class CacheService:
    """
    Вспомогательный сервис для работы с анализами (AnalysisResult).
    Оставлены только методы для очистки старых записей.
    """
    @staticmethod
    def clear_old_cache(db: Session, days_threshold: int = None) -> int:
        """
        Очищает устаревшие записи анализа (AnalysisResult)
        :param db: сессия БД
        :param days_threshold: сколько дней хранить записи
        :return: количество удалённых записей
        """
        if days_threshold is None:
            days_threshold = settings.CACHE_EXPIRATION_DAYS
        threshold_date = datetime.datetime.now() - datetime.timedelta(days=days_threshold)
        old_analyses = db.query(AnalysisResult).filter(
            AnalysisResult.created_at < threshold_date
        ).all()
        deleted = 0
        for analysis in old_analyses:
            db.delete(analysis)
            deleted += 1
        db.commit()
        logger.info(f"Удалено устаревших записей AnalysisResult: {deleted}")
        return deleted
