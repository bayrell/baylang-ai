"""
Запись пользователя в БД.
Содержит методы для хеширования и проверки паролей.
"""
from datetime import datetime
from typing import Optional
from core.database.record import Record
import bcrypt


class UserRecord(Record):
    """Запись пользователя в БД"""

    _table = "users"
    _fields = [
        "id", "username", "email", "password_hash",
        "display_name", "is_active", "is_admin",
        "created_at", "updated_at"
    ]

    @staticmethod
    def hash_password(password: str) -> str:
        """Хеширование пароля"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def verify_password(self, password: str) -> bool:
        """Проверка пароля"""
        return bcrypt.checkpw(
            password.encode('utf-8'),
            self.password_hash.encode('utf-8')
        )

    def to_public_dict(self) -> dict:
        """Публичные данные пользователя (без пароля)"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "display_name": self.display_name,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "created_at": self.created_at
        }