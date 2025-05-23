from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.status import HTTP_404_NOT_FOUND, HTTP_422_UNPROCESSABLE_ENTITY, HTTP_500_INTERNAL_SERVER_ERROR
import logging

logger = logging.getLogger(__name__)

# Пример пользовательских исключений
class FileNotFoundError(Exception):
    """Файл не найден в базе данных"""
    pass

class PermissionDeniedError(Exception):
    """Ошибка доступа (нет прав)"""
    pass

class ValidationError(Exception):
    """Ошибка валидации входных данных"""
    pass

def format_error_response(exc: Exception, status_code: int = 500):
    return {
        "status": "error",
        "error": {
            "type": exc.__class__.__name__,
            "message": str(exc)
        }
    }

def add_global_exception_handlers(app):
    @app.exception_handler(FileNotFoundError)
    async def file_not_found_handler(request: Request, exc: FileNotFoundError):
        logger.warning(f"File not found: {exc}")
        return JSONResponse(status_code=HTTP_404_NOT_FOUND, content=format_error_response(exc, HTTP_404_NOT_FOUND))

    @app.exception_handler(PermissionDeniedError)
    async def permission_denied_handler(request: Request, exc: PermissionDeniedError):
        logger.warning(f"Permission denied: {exc}")
        return JSONResponse(status_code=403, content=format_error_response(exc, 403))

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError):
        logger.warning(f"Validation error: {exc}")
        return JSONResponse(status_code=HTTP_422_UNPROCESSABLE_ENTITY, content=format_error_response(exc, HTTP_422_UNPROCESSABLE_ENTITY))

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.warning(f"HTTPException: {exc.detail}")
        return JSONResponse(status_code=exc.status_code, content=format_error_response(exc, exc.status_code))

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unexpected error: {exc}")
        return JSONResponse(status_code=HTTP_500_INTERNAL_SERVER_ERROR, content=format_error_response(exc, HTTP_500_INTERNAL_SERVER_ERROR))
