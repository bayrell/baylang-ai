"""
Базовый репозиторий для CRUD операций.
Предоставляет абстракцию над доступом к данным.
"""
from typing import Optional, List, Type, TypeVar
from core.database.record import Record

T = TypeVar('T', bound=Record)


class Repository:
    """Базовый репозиторий для CRUD операций"""

    def __init__(self, db, record_class: Type[T]):
        self.db = db
        self.record_class = record_class

    async def find_by_id(self, id: int) -> Optional[T]:
        """Поиск по ID"""
        query = f"SELECT * FROM {self.record_class._table} WHERE id = ?"
        row = await self.db.fetch_one(query, (id,))
        if row:
            return self.record_class.from_db(row)
        return None

    async def find_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """Получение всех записей"""
        query = f"SELECT * FROM {self.record_class._table} LIMIT ? OFFSET ?"
        rows = await self.db.fetch_all(query, (limit, offset))
        return [self.record_class.from_db(row) for row in rows]

    async def create(self, record: T) -> T:
        """Создание новой записи"""
        data = record.to_db()
        fields = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])

        query = f"INSERT INTO {self.record_class._table} ({fields}) VALUES ({placeholders})"
        cursor = await self.db.execute(query, list(data.values()))

        record.id = cursor.lastrowid
        return record

    async def update(self, record: T) -> T:
        """Обновление записи"""
        data = record.to_db()
        set_clause = ", ".join([f"{k} = ?" for k in data.keys()])

        query = f"UPDATE {self.record_class._table} SET {set_clause} WHERE id = ?"
        await self.db.execute(query, list(data.values()) + [record.id])

        return record

    async def delete(self, id: int) -> bool:
        """Удаление записи"""
        query = f"DELETE FROM {self.record_class._table} WHERE id = ?"
        cursor = await self.db.execute(query, (id,))
        return cursor.rowcount > 0

    async def count(self) -> int:
        """Подсчет количества записей"""
        query = f"SELECT COUNT(*) as count FROM {self.record_class._table}"
        row = await self.db.fetch_one(query)
        return row["count"] if row else 0