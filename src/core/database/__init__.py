"""
Абстрактный класс для работы с БД.
Определяет интерфейс, который должны реализовать конкретные БД (SQLite, D1).
"""
from typing import Optional, List, Any
from abc import ABC, abstractmethod


class Database(ABC):
    """Абстрактный класс для работы с БД"""

    @abstractmethod
    async def connect(self):
        """Подключение к БД"""
        pass

    @abstractmethod
    async def disconnect(self):
        """Отключение от БД"""
        pass

    @abstractmethod
    async def execute(self, query: str, params: tuple = ()) -> Any:
        """Выполнение запроса"""
        pass

    @abstractmethod
    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[dict]:
        """Получение одной строки"""
        pass

    @abstractmethod
    async def fetch_all(self, query: str, params: tuple = ()) -> List[dict]:
        """Получение всех строк"""
        pass

    @abstractmethod
    async def execute_migration(self, sql: str):
        """Выполнение миграции"""
        pass