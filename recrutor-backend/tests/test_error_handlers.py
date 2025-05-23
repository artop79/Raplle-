import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.error_handlers import FileNotFoundError, PermissionDeniedError, ValidationError

client = TestClient(app)

@app.get("/test/file-not-found")
def test_file_not_found():
    raise FileNotFoundError("Файл не найден!")

@app.get("/test/permission-denied")
def test_permission_denied():
    raise PermissionDeniedError("Нет доступа!")

@app.get("/test/validation-error")
def test_validation_error():
    raise ValidationError("Ошибка валидации!")

@app.get("/test/unexpected-error")
def test_unexpected_error():
    raise RuntimeError("Неожиданная ошибка!")

def test_file_not_found_handler():
    response = client.get("/test/file-not-found")
    assert response.status_code == 404
    assert response.json()["status"] == "error"
    assert response.json()["error"]["type"] == "FileNotFoundError"


def test_permission_denied_handler():
    response = client.get("/test/permission-denied")
    assert response.status_code == 403
    assert response.json()["status"] == "error"
    assert response.json()["error"]["type"] == "PermissionDeniedError"


def test_validation_error_handler():
    response = client.get("/test/validation-error")
    assert response.status_code == 422
    assert response.json()["status"] == "error"
    assert response.json()["error"]["type"] == "ValidationError"


def test_generic_error_handler():
    response = client.get("/test/unexpected-error")
    assert response.status_code == 500
    assert response.json()["status"] == "error"
    assert response.json()["error"]["type"] == "RuntimeError"
