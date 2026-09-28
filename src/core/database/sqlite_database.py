"""
Реализация SQLite базы данных с поддержкой async.
Использует aiosqlite для асинхронного доступа к SQLite.
"""
import aiosqlite
from typing import Optional, List, Any
from core.database import Database


class SQLiteDatabase(Database):
    """Реализация для SQLite"""

    def __init__(self, db_path: str = "data.db"):
        self.db_path = db_path
        self.connection: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Подключение к SQLite"""
        self.connection = await aiosqlite.connect(self.db_path)
        self.connection.row_factory = aiosqlite.Row
        # Включаем поддержку внешних ключей
        await self.connection.execute("PRAGMA foreign_keys = ON")

    async def disconnect(self):
        """Отключение от SQLite"""
        if self.connection:
            await self.connection.close()

    async def execute(self, query: str, params: tuple = ()) -> Any:
        """Выполнение запроса"""
        cursor = await self.connection.execute(query, params)
        await self.connection.commit()
        return cursor

    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[dict]:
        """Получение одной строки"""
        cursor = await self.connection.execute(query, params)
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None

    async def fetch_all(self, query: str, params: tuple = ()) -> List[dict]:
        """Получение всех строк"""
        cursor = await self.connection.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def execute_migration(self, sql: str):
        """Выполнение миграции"""
        await self.connection.executescript(sql)
        await self.connection.commit()