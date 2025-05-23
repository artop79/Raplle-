"""
Сервис для работы с API Heygen для создания и управления видеоаватарами.
"""
import os
import json
import requests
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

class HeygenService:
    """
    Класс для взаимодействия с API Heygen.
    """
    
    BASE_URL = "https://api.heygen.com/v2"
    
    def __init__(self):
        """
        Инициализация сервиса с API ключом из переменных окружения.
        """
        self.api_key = os.getenv("HEYGEN_API_KEY")
        if not self.api_key:
            raise ValueError("API ключ Heygen не найден в переменных окружения")
        
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "x-api-key": self.api_key
        }
    
    def create_streaming_session(self, quality="720p", avatar_id=None, voice_id=None, **options):
        """
        Создает новую сессию стриминга для видеоаватара.
        
        Args:
            quality (str): Разрешение видео (например, "720p")
            avatar_id (str, optional): ID аватара
            voice_id (str, optional): ID голоса
            **options: Дополнительные параметры
            
        Returns:
            dict: Ответ от API Heygen
        """
        url = f"{self.BASE_URL}/streaming/video"
        
        # Настройки для API v2
        payload = {
            "background": {
                "type": "color",
                "value": options.get("bg_color", "#1a1a2e")
            },
            "video_setting": {
                "resolution": quality,
                "ratio": options.get("ratio", "16:9")
            }
        }
        
        # Добавляем аватар, если указан
        if avatar_id:
            payload["avatar"] = {
                "avatar_id": avatar_id
            }
            
            # Добавляем голос, если указан
            if voice_id:
                payload["avatar"]["voice_id"] = voice_id
                payload["avatar"]["voice_setting"] = {
                    "speed": float(options.get("voice_speed", 1.0)),
                    "stability": float(options.get("voice_stability", 0.5))
                }
        
        # Webhook для уведомлений (опционально)
        if "webhook_url" in options:
            payload["webhook_url"] = options["webhook_url"]
        
        print(f"Creating streaming session with payload: {json.dumps(payload)}")
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()  # Вызовет исключение для HTTP ошибок
            
            data = response.json()
            print(f"Session created: {json.dumps(data)}")
            
            # Преобразуем данные для совместимости
            session_data = {
                "data": {
                    "session_id": data.get("data", {}).get("session_id", ""),
                    "preview_url": data.get("data", {}).get("preview_url", ""),
                    "url": data.get("data", {}).get("url", ""),
                    "created_at": data.get("data", {}).get("created_at", "")
                }
            }
            
            return session_data
            
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при создании сессии стриминга: {e}")
            return {"error": str(e)}
    
    def list_streaming_avatars(self):
        """
        Получает список доступных аватаров для стриминга.
        
        Returns:
            dict: Список аватаров
        """
        url = f"{self.BASE_URL}/avatars"
        
        try:
            print(f"Fetching avatars from: {url}")
            print(f"Using headers: {self.headers}")
            
            response = requests.get(url, headers=self.headers)
            print(f"Response status code: {response.status_code}")
            
            # Отладочный вывод текста ответа
            response_text = response.text
            print(f"Response text preview: {response_text[:200]}...")
            
            response.raise_for_status()
            
            # Пробуем парсить JSON в защищенном режиме
            try:
                data = response.json()
                print(f"Successfully parsed JSON response. Keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            except ValueError as json_err:
                print(f"Error parsing JSON: {json_err}")
                return {"error": f"Invalid JSON response: {str(json_err)}"}
            
            avatars = []
            
            if isinstance(data, dict) and "data" in data:
                # В API v2 аватары находятся в data["data"]["avatars"]
                if isinstance(data["data"], dict) and "avatars" in data["data"] and isinstance(data["data"]["avatars"], list):
                    # Преобразуем формат данных API v2 в формат, ожидаемый фронтендом
                    for avatar in data["data"]["avatars"]:
                        if isinstance(avatar, dict):
                            # Формируем структуру данных, ожидаемую фронтендом
                            processed_avatar = {
                                "avatar_id": avatar.get("avatar_id", ""),
                                "name": avatar.get("avatar_name", "Heygen Avatar"),  # Изменено на avatar_name
                                "gender": avatar.get("gender", "не указан"),
                                "language": avatar.get("language", "английский"),
                                "preview_url": avatar.get("preview_image_url", ""),  # Изменено на preview_image_url
                                "type": avatar.get("model_type", "realistic"),
                                "voice_id": avatar.get("voice_id", "")
                            }
                            avatars.append(processed_avatar)
                            print(f"Processed avatar: {processed_avatar['name']}")
                        else:
                            print(f"Unexpected avatar data type: {type(avatar)}")
                    
                    print(f"Fetched {len(avatars)} avatars successfully")
                elif isinstance(data["data"], list):
                    # Старый формат для совместимости
                    print("Using alternative format where data['data'] is a list")
                    for avatar in data["data"]:
                        if isinstance(avatar, dict):
                            processed_avatar = {
                                "avatar_id": avatar.get("avatar_id", ""),
                                "name": avatar.get("name", "Heygen Avatar"),
                                "gender": avatar.get("gender", "не указан"),
                                "language": avatar.get("language", "английский"),
                                "preview_url": avatar.get("preview_url") or avatar.get("image_url", ""),
                                "type": avatar.get("model_type", "realistic"),
                                "voice_id": avatar.get("voice_id", "")
                            }
                            avatars.append(processed_avatar)
                            print(f"Processed avatar: {processed_avatar['name']}")
                    print(f"Fetched {len(avatars)} avatars from alternative format")
                else:
                    print(f"Unexpected data format. data['data'] is neither a dict with 'avatars' nor a list: {type(data['data'])}")
                    print(f"Keys in data['data']: {list(data['data'].keys()) if isinstance(data['data'], dict) else 'Not a dict'}")
                    if isinstance(data['data'], dict) and 'avatars' in data['data']:
                        print(f"Type of data['data']['avatars']: {type(data['data']['avatars'])}")
                        if isinstance(data['data']['avatars'], list):
                            print(f"Length of data['data']['avatars']: {len(data['data']['avatars'])}")
                            if len(data['data']['avatars']) > 0:
                                print(f"Type of first avatar: {type(data['data']['avatars'][0])}")
                                print(f"Keys of first avatar: {list(data['data']['avatars'][0].keys()) if isinstance(data['data']['avatars'][0], dict) else 'Not a dict'}")
                        
                    # Детальный вывод для отладки
                    print(f"Full data structure: {data}")
                    
                return {"data": avatars}
            else:
                print(f"Response does not contain 'data' key or is not a dictionary. Type: {type(data)}")
                # Возвращаем пустой список вместо ошибки
                return {"data": []}
                
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при получении списка аватаров: {e}")
            return {"error": str(e)}
    
    def check_api_status(self):
        """
        Проверяет статус подключения к API Heygen
        
        Returns:
            dict: Статус подключения
        """
        try:
            # Для проверки доступности API используем запрос на получение аватаров
            print(f"Checking Heygen API status: {self.BASE_URL}/avatars")
            response = requests.get(
                f"{self.BASE_URL}/avatars", 
                headers=self.headers
            )
            
            # Проверяем статус ответа
            if response.status_code == 200:
                # Пробуем парсить JSON в защищенном режиме
                try:
                    data = response.json()
                    if isinstance(data, dict) and data.get("data") is not None:
                        print("Heygen API доступен, получены данные")
                        return {"status": "ok", "message": "API доступен"}
                except ValueError:
                    print("Heygen API доступен, но ответ не является JSON")
                
                # Если дошли до сюда, значит API доступен, но формат ответа неожиданный
                return {"status": "ok", "message": "API доступен, но формат ответа неожиданный"}
            else:
                print(f"Heygen API недоступен, код ответа: {response.status_code}")
                return {"status": "error", "message": f"API недоступен, код ответа: {response.status_code}"}
        except Exception as e:
            print(f"Error checking API status: {str(e)}")
            return {"status": "error", "message": f"Ошибка проверки API: {str(e)}"}
    
    def get_streaming_session_info(self, session_id):
        """
        Получает информацию о сессии стриминга

        Args:
            session_id (str): ID сессии стриминга
            
        Returns:
            dict: Информация о сессии
        """
        try:
            url = f"{self.BASE_URL}/streaming/video/{session_id}"
            print(f"Getting session info for {session_id}")
            
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            print(f"Session info: {json.dumps(data)}")
            
            return data
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при получении информации о сессии: {e}")
            return {"error": str(e)}
    
    def send_text_to_avatar(self, session_id, text, voice_id=None, **options):
        """
        Отправляет текст для озвучивания аватаром.
        
        Args:
            session_id (str): ID сессии стриминга
            text (str): Текст для озвучивания
            voice_id (str, optional): ID голоса для использования
            **options: Дополнительные настройки голоса
            
        Returns:
            dict: Ответ от API Heygen
        """
        url = f"{self.BASE_URL}/streaming/talk"
        
        # Формат для API v2
        payload = {
            "session_id": session_id,
            "text": text,
            "voice_setting": {
                "stability": float(options.get("voice_stability", 0.5)),
                "speed": float(options.get("voice_speed", 1.0)),
                "style": int(options.get("voice_style", 0)),
            },
            "language": options.get("language", "ru")
        }
        
        print(f"Sending text to session {session_id}: {text[:30]}...")
        print(f"Payload: {json.dumps(payload)}")
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            print(f"Text sent successfully: {json.dumps(data)}")
            
            return data
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при отправке текста: {e}")
            return {"error": str(e)}
    
    def close_streaming_session(self, session_id):
        """
        Закрывает сессию стриминга.
        
        Args:
            session_id (str): ID сессии стриминга
            
        Returns:
            dict: Ответ от API Heygen
        """
        url = f"{self.BASE_URL}/streaming/video/{session_id}"
        
        print(f"Closing streaming session {session_id}")
        
        try:
            # В API v2 используется DELETE запрос
            response = requests.delete(url, headers=self.headers)
            response.raise_for_status()
            
            print(f"Session closed successfully with status {response.status_code}")
            
            return {"status": "success", "message": "Сессия успешно закрыта"}
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при закрытии сессии: {e}")
            return {"error": str(e)}
            
    def get_voices(self, language="ru"):
        """
        Получает список доступных голосов для использования с аватарами.
        
        Args:
            language (str): Код языка (по умолчанию "ru")
            
        Returns:
            dict: Список голосов
        """
        url = f"{self.BASE_URL}/voice"
        
        try:
            print(f"Fetching voices for language: {language}")
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            voices = []
            
            if "data" in data:
                # Фильтруем голоса по языку
                filtered_voices = data["data"]
                if language != "all":
                    filtered_voices = [v for v in data["data"] if 
                        v.get("language_code") == language or
                        (language == "ru" and v.get("language_code") == "russian") or
                        (language == "russian" and v.get("language_code") == "ru")
                    ]
                
                # Преобразуем формат данных в ожидаемый фронтендом
                for voice in filtered_voices:
                    processed_voice = {
                        "voice_id": voice.get("voice_id"),
                        "name": voice.get("name", "Voice"),
                        "gender": voice.get("gender", "neutral"),
                        "language": voice.get("language", "English"),
                        "language_code": voice.get("language_code", "en")
                    }
                    voices.append(processed_voice)
                
                print(f"Fetched {len(voices)} voices for language '{language}'")
                return {"data": voices}
            else:
                print("No voices found in the response")
                return {"data": []}
                
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при получении голосов: {e}")
            return {"error": str(e)}


# Пример использования:
if __name__ == "__main__":
    heygen = HeygenService()
    
    # Проверка API статуса
    print("\n=== Проверка API статуса ===")
    status = heygen.check_api_status()
    print("API статус:", status)
    
    # Получение списка аватаров
    print("\n=== Получение списка аватаров ===")
    avatars_response = heygen.list_streaming_avatars()
    
    # Получение голосов
    print("\n=== Получение голосов для русского языка ===")
    voices_response = heygen.get_voices(language="ru")
    
    # Если есть доступные аватары и голоса
    if "error" not in avatars_response and avatars_response.get("data") and \
       "error" not in voices_response and voices_response.get("data"):
        
        # Выбираем первый аватар и голос
        avatar_id = avatars_response["data"][0]["avatar_id"]
        voice_id = voices_response["data"][0]["voice_id"] if voices_response["data"] else None
        
        print(f"\n=== Создание сессии с аватаром {avatar_id} ===")
        # Создание новой сессии с указанным аватаром и голосом
        session_response = heygen.create_streaming_session(
            quality="720p", 
            avatar_id=avatar_id, 
            voice_id=voice_id,
            bg_color="#1a1a2e",
            voice_speed=1.0,
            voice_stability=0.5
        )
        
        if "error" not in session_response and session_response.get("data", {}).get("session_id"):
            session_id = session_response["data"]["session_id"]
            
            # Отправка текста для озвучивания
            print(f"\n=== Отправка текста в сессию {session_id} ===")
            text_response = heygen.send_text_to_avatar(
                session_id=session_id,
                text="Привет! Я ваш AI-интервьюер. Расскажите о вашем опыте работы.",
                voice_speed=1.0,
                voice_stability=0.5,
                language="ru"
            )
            
            # Ждем 5 секунд, чтобы увидеть результат
            import time
            print("\nОжидание 5 секунд...")
            time.sleep(5)
            
            # Закрытие сессии
            print(f"\n=== Закрытие сессии {session_id} ===")
            close_response = heygen.close_streaming_session(session_id)
            print("Результат закрытия сессии:", json.dumps(close_response, indent=2))
        else:
            print("\nОшибка при создании сессии:", json.dumps(session_response, indent=2))
    else:
        if "error" in avatars_response:
            print("\nОшибка при получении аватаров:", json.dumps(avatars_response, indent=2))
        if "error" in voices_response:
            print("\nОшибка при получении голосов:", json.dumps(voices_response, indent=2))
