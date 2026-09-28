"""
Сервис для работы с JWT токенами.
Создание, проверка и декодирование токенов.
"""
from datetime import datetime, timedelta
from typing import Optional
import jwt
import os


class JWTService:
    """Сервис для работы с JWT токенами"""

    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 60 * 24  # 24 часа

    def create_access_token(self, user_id: int, email: str) -> dict:
        """Создание JWT токена"""
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)

        payload = {
            "sub": user_id,
            "email": email,
            "exp": expire,
            "iat": datetime.utcnow()
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        return {
            "token": token,
            "expires_at": expire
        }

    def verify_token(self, token: str) -> Optional[dict]:
        """Проверка JWT токена"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def decode_token(self, token: str) -> Optional[dict]:
        """Декодирование JWT токена"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except Exception:
            return None