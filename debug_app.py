import sys
import traceback

try:
    # Добавляем путь к пакету в sys.path
    sys.path.append('/Users/macbook/recrutor.com/recrutor-backend')
    # Пытаемся импортировать и запустить основное приложение
    from app.main import app
    
    print("Приложение успешно импортировано!")
    print(f"Доступные маршруты:")
    for route in app.routes:
        print(f" - {route.path}")
    
except Exception as e:
    print("Ошибка при импорте приложения:")
    print(f"Тип ошибки: {type(e).__name__}")
    print(f"Сообщение об ошибке: {str(e)}")
    print("\nПолный стек вызовов:")
    traceback.print_exc()
