from fastapi import Depends
from app.database.session import get_db
from app.core.auth import get_current_user

# Реэкспортируем зависимости для удобства использования
get_current_user = get_current_user
get_db = get_db
