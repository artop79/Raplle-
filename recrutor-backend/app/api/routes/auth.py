from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.models import User
from app.core.auth import authenticate_user, create_access_token, get_password_hash, get_current_user, verify_password
from app.config import settings

router = APIRouter()

@router.post("/login")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    """Вход в систему и получение токена доступа"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Проверяем, что пользователь активен
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Учетная запись пользователя неактивна",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Обновляем время последнего входа
    from datetime import datetime
    user.last_login = datetime.now()
    db.commit()
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "is_superuser": user.is_superuser
    }

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    username: str, 
    email: str, 
    password: str, 
    db: Session = Depends(get_db)
):
    """Регистрация нового пользователя"""
    # Проверяем уникальность имени пользователя и email
    existing_user = db.query(User).filter(
        (User.username == username) | (User.email == email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким именем или email уже существует"
        )
    
    # Создаем нового пользователя
    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash(password)
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "message": "Пользователь успешно зарегистрирован"
    }

@router.get("/me")
async def read_users_me(current_user = Depends(get_current_user)):
    """Получение информации о текущем пользователе"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "is_superuser": current_user.is_superuser,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None
    }

@router.post("/test-login")
async def test_login():
    """Тестовый вход для демонстрации и разработки"""
    # Создаем тестовый токен (не для использования в продакшн!)
    access_token_expires = timedelta(days=1)  # Долгий срок для удобства тестирования
    access_token = create_access_token(
        data={"sub": "testuser"}, expires_delta=access_token_expires
    )
    
    # Возвращаем тестовые данные пользователя
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": 9999,
            "username": "test_user",
            "email": "test@example.com",
            "is_superuser": True,
            "name": "Тестовый Пользователь HR"
        }
    }

@router.get("/dashboard")
async def get_user_dashboard(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Получение статистики для личного кабинета пользователя"""
    from app.database.models import File, AnalysisResult
    from sqlalchemy import func
    
    # Получаем количество загруженных файлов
    resume_count = db.query(func.count(File.id)).filter(
        File.user_id == current_user.id,
        File.file_type == "resume"
    ).scalar()
    
    job_description_count = db.query(func.count(File.id)).filter(
        File.user_id == current_user.id,
        File.file_type == "job_description"
    ).scalar()
    
    # Получаем количество анализов
    analysis_count = db.query(func.count(AnalysisResult.id)).join(
        File, AnalysisResult.resume_id == File.id
    ).filter(
        File.user_id == current_user.id
    ).scalar()
    
    # Получаем последние загруженные файлы
    recent_files = db.query(File).filter(
        File.user_id == current_user.id
    ).order_by(File.created_at.desc()).limit(5).all()
    
    recent_files_data = [{
        "id": file.id,
        "filename": file.filename,
        "file_type": file.file_type,
        "created_at": file.created_at.isoformat() if file.created_at else None
    } for file in recent_files]
    
    return {
        "user_info": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
            "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
            "is_superuser": current_user.is_superuser
        },
        "statistics": {
            "resume_count": resume_count,
            "job_description_count": job_description_count,
            "analysis_count": analysis_count
        },
        "recent_files": recent_files_data
    }

@router.put("/update-profile")
async def update_user_profile(
    username: str = None,
    email: str = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Обновление профиля пользователя"""
    # Проверка на уникальность нового имени пользователя и email
    if username and username != current_user.username:
        existing_username = db.query(User).filter(User.username == username).first()
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким именем уже существует"
            )
        current_user.username = username
    
    if email and email != current_user.email:
        existing_email = db.query(User).filter(User.email == email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким email уже существует"
            )
        current_user.email = email
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "status": "success",
        "message": "Профиль пользователя успешно обновлен",
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
            "is_superuser": current_user.is_superuser
        }
    }

@router.put("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Изменение пароля пользователя"""
    # Проверка текущего пароля
    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный текущий пароль"
        )
    
    # Проверка сложности нового пароля
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Новый пароль должен содержать минимум 8 символов"
        )
    
    # Обновление пароля
    current_user.hashed_password = get_password_hash(new_password)
    db.commit()
    
    return {
        "status": "success",
        "message": "Пароль успешно изменен"
    }
