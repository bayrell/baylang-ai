"""
Репозиторий для работы с пользователями.
Наследуется от базового Repository и добавляет специфичные методы.
"""
from typing import Optional
from core.database.repository import Repository
from core.database.records.user_record import UserRecord


class UserRepository(Repository):
    """Репозиторий для работы с пользователями"""

    def __init__(self, db):
        super().__init__(db, UserRecord)

    async def find_by_email(self, email: str) -> Optional[UserRecord]:
        """Поиск пользователя по email"""
        query = "SELECT * FROM users WHERE email = ?"
        row = await self.db.fetch_one(query, (email,))
        if row:
            return UserRecord.from_db(row)
        return None

    async def find_by_username(self, username: str) -> Optional[UserRecord]:
        """Поиск пользователя по username"""
        query = "SELECT * FROM users WHERE username = ?"
        row = await self.db.fetch_one(query, (username,))
        if row:
            return UserRecord.from_db(row)
        return None

    async def create_user(self, username: str, email: str, password: str,
                          display_name: str = None) -> UserRecord:
        """Создание нового пользователя"""
        password_hash = UserRecord.hash_password(password)

        user = UserRecord(
            username=username,
            email=email,
            password_hash=password_hash,
            display_name=display_name or username,
            is_active=True,
            is_admin=False
        )

        return await self.create(user)

    async def verify_user(self, email: str, password: str) -> Optional[UserRecord]:
        """Проверка учетных данных"""
        user = await self.find_by_email(email)
        if user and user.verify_password(password):
            return user
        return None

    async def update_password(self, user_id: int, new_password: str) -> bool:
        """Обновление пароля"""
        password_hash = UserRecord.hash_password(new_password)
        query = "UPDATE users SET password_hash = ? WHERE id = ?"
        cursor = await self.db.execute(query, (password_hash, user_id))
        return cursor.rowcount > 0