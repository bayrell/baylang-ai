"""
Реализация Cloudflare D1 базы данных.
D1 - это серверная SQLite-подобная база данных от Cloudflare.
"""
from typing import Optional, List, Any
from core.database import Database


class D1Database(Database):
    """Реализация для Cloudflare D1"""

    def __init__(self, d1_binding):
        """
        d1_binding - привязка D1 из Cloudflare Workers
        self.env.D1_DB
        """
        self.d1 = d1_binding

    async def connect(self):
        """D1 не требует явного подключения"""
        pass

    async def disconnect(self):
        """D1 не требует явного отключения"""
        pass

    async def execute(self, query: str, params: tuple = ()) -> Any:
        """Выполнение запроса через D1 API"""
        # D1 использует другой API
        result = await self.d1.prepare(query).bind(*params).run()
        return result

    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[dict]:
        """Получение одной строки"""
        result = await self.d1.prepare(query).bind(*params).first()
        return result

    async def fetch_all(self, query: str, params: tuple = ()) -> List[dict]:
        """Получение всех строк"""
        result = await self.d1.prepare(query).bind(*params).all()
        return result["results"] if result else []

    async def execute_migration(self, sql: str):
        """Выполнение миграции (разбиваем на отдельные запросы)"""
        # D1 не поддерживает executescript, разбиваем SQL
        queries = sql.split(";")
        for query in queries:
            query = query.strip()
            if query:
                await self.d1.prepare(query).run()