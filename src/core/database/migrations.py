"""
Базовый класс для миграций.
Каждая миграция должна наследоваться от этого класса и реализовывать методы up/down.
"""
import os
import importlib
from abc import ABC, abstractmethod
from typing import List, Type


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


class MigrationService:
    """Сервис для управления миграциями"""

    def __init__(self, db):
        self.db = db
        self.migrations: List[Type[Migration]] = []
        self._load_migrations()

    def _load_migrations(self):
        """Автоматическая загрузка миграций из директории"""
        migrations_dir = os.path.dirname(__file__)

        for filename in os.listdir(migrations_dir):
            if filename.startswith("0") and filename.endswith(".py"):
                module_name = filename[:-3]  # Убираем .py
                module = importlib.import_module(
                    f"core.database.migrations.{module_name}"
                )

                # Находим все классы миграций в модуле
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                        issubclass(attr, Migration) and
                        attr != Migration):
                        self.migrations.append(attr)

        # Сортируем по имени
        self.migrations.sort(key=lambda m: m(self.db).get_name())

    async def migrate(self):
        """Применение всех миграций"""
        # Создаем таблицу для отслеживания миграций
        await self.db.execute_migration("""
            CREATE TABLE IF NOT EXISTS migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255) UNIQUE NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Получаем список примененных миграций
        applied = await self.db.fetch_all(
            "SELECT name FROM migrations"
        )
        applied_names = [row["name"] for row in applied]

        # Применяем новые миграции
        for migration_class in self.migrations:
            migration = migration_class(self.db)
            name = migration.get_name()

            if name not in applied_names:
                print(f"Applying migration: {name}")
                await migration.up()

                # Записываем в таблицу миграций
                await self.db.execute(
                    "INSERT INTO migrations (name) VALUES (?)",
                    (name,)
                )

        print("All migrations applied successfully!")