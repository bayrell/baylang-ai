"""
Базовый класс для всех записей БД.
Определяет методы для сериализации/десериализации данных.
"""
from datetime import datetime
from typing import Optional, Any
import json


class Record:
    """Базовый класс для всех записей БД"""

    # Имя таблицы (переопределяется в дочерних классах)
    _table: str = ""

    # Поля таблицы (переопределяется в дочерних классах)
    _fields: list = []

    def __init__(self, **kwargs):
        self._data = {}
        for field in self._fields:
            setattr(self, field, kwargs.get(field))
            self._data[field] = kwargs.get(field)

    def to_dict(self) -> dict:
        """Преобразование в словарь"""
        return {k: v for k, v in self._data.items() if v is not None}

    def to_json(self) -> str:
        """Преобразование в JSON строку"""
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_db(cls, row: dict) -> 'Record':
        """Создание экземпляра из строки БД"""
        return cls(**row)

    def to_db(self) -> dict:
        """Преобразование для сохранения в БД"""
        return self.to_dict()

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.to_dict()}>"