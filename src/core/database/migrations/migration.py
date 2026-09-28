"""
Базовый класс для миграций.
Каждая миграция должна наследоваться от этого класса и реализовывать методы up/down.
"""
from abc import ABC, abstractmethod


class Migration(ABC):
    """Базовый класс для миграций"""

    def __init__(self, db):
        self.db = db

    @abstractmethod
    def get_name(self) -> str:
        """Имя миграции"""
        pass

    @abstractmethod
    async def up(self):
        """Применение миграции"""
        pass

    @abstractmethod
    async def down(self):
        """Откат миграции"""
        pass