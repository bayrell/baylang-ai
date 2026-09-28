"""
API роуты для авторизации.
Содержит эндпоинты для регистрации, входа, профиля и смены пароля.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

from core.auth.jwt_service import JWTService

# Request модели
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    display_name: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = None
    email: Optional[EmailStr] = None

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)

# Response модели
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    display_name: Optional[str]
    is_active: bool
    is_admin: bool
    created_at: datetime

class AuthResponse(BaseModel):
    user: UserResponse
    token: str
    expires_at: datetime

class ErrorResponse(BaseModel):
    detail: str

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()

# Сервисы (получаются через DI контейнер)
jwt_service = JWTService()


def get_user_repository():
    """Получение репозитория пользователей через контейнер"""
    from core.app import get_container
    container = get_container()
    return container.get("user_repository")


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Получение текущего пользователя из JWT"""
    token = credentials.credentials
    payload = jwt_service.verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    return payload


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    """Регистрация нового пользователя"""
    user_repo = get_user_repository()

    # Проверяем существование пользователя
    existing_user = await user_repo.find_by_email(request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    existing_user = await user_repo.find_by_username(request.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Создаем пользователя
    user = await user_repo.create_user(
        username=request.username,
        email=request.email,
        password=request.password,
        display_name=request.display_name
    )

    # Создаем JWT токен
    token_data = jwt_service.create_access_token(user.id, user.email)

    return AuthResponse(
        user=UserResponse(**user.to_public_dict()),
        token=token_data["token"],
        expires_at=token_data["expires_at"]
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """Вход в систему"""
    user_repo = get_user_repository()

    # Проверяем учетные данные
    user = await user_repo.verify_user(request.email, request.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )

    # Создаем JWT токен
    token_data = jwt_service.create_access_token(user.id, user.email)

    return AuthResponse(
        user=UserResponse(**user.to_public_dict()),
        token=token_data["token"],
        expires_at=token_data["expires_at"]
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Получение текущего пользователя"""
    user_repo = get_user_repository()
    user = await user_repo.find_by_id(current_user["sub"])

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse(**user.to_public_dict())


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user)
):
    """Обновление профиля"""
    user_repo = get_user_repository()
    user = await user_repo.find_by_id(current_user["sub"])

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Обновляем поля
    if request.display_name is not None:
        user.display_name = request.display_name
    if request.email is not None:
        # Проверяем уникальность email
        existing = await user_repo.find_by_email(request.email)
        if existing and existing.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        user.email = request.email

    user.updated_at = datetime.utcnow()
    await user_repo.update(user)

    return UserResponse(**user.to_public_dict())


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """Смена пароля"""
    user_repo = get_user_repository()
    user = await user_repo.find_by_id(current_user["sub"])

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Проверяем текущий пароль
    if not user.verify_password(request.current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Обновляем пароль
    await user_repo.update_password(user.id, request.new_password)

    return {"message": "Password updated successfully"}