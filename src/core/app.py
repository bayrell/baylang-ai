"""
Главное приложение FastAPI.
Создает и настраивает приложение, подключает роуты и зависимости.
"""
import jinja2
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from core.container import Container
from core.config import Config, CloudflareConfig
from core.database.sqlite_database import SQLiteDatabase
from core.database.d1_database import D1Database
from core.database.repositories.user_repository import UserRepository
from core.database.migrations.migration_service import MigrationService


def register_container():
    """Регистрация контейнера с зависимостями"""
    container = Container()
    container.singleton("app", lambda container: FastAPI())
    container.singleton("template", lambda container: jinja2.Environment())
    container.singleton("config", lambda container: Config())
    return container


container = register_container()
app = container.get("app")


def get_container():
    """Получение контейнера"""
    return container


def get_app():
    """Получение приложения"""
    return app


def get_config():
    """Получение конфигурации"""
    return container.get("config")


def register_routes():
    """Регистрация роутов"""
    from core.routes import router
    app.include_router(router)
    
    # Подключаем auth роуты
    from core.auth.router import router as auth_router
    router.include_router(auth_router)


def register_frontend():
    """Регистрация статических файлов фронтенда"""
    app.mount("/", StaticFiles(directory="dist", html=True), name="static")


def create_app():
    """Создание приложения для локальной разработки"""
    # Регистрируем SQLite БД для разработки
    db = SQLiteDatabase("data.db")
    container.singleton("database", lambda container: db)

    # Регистрируем репозитории
    container.singleton("user_repository", lambda container: UserRepository(db))

    # Регистрируем сервис миграций
    migration_service = MigrationService(db)
    container.singleton("migration_service", lambda container: migration_service)

    # Применяем миграции
    import asyncio
    asyncio.get_event_loop().run_until_complete(db.connect())
    asyncio.get_event_loop().run_until_complete(migration_service.migrate())
    asyncio.get_event_loop().run_until_complete(db.disconnect())

    # Регистрируем роуты
    register_routes()

    return app


def create_cloudflare(env):
    """Создание приложения для Cloudflare Workers"""
    # Регистрируем D1 БД для production
    db = D1Database(env.D1_DB)
    container.singleton("database", lambda container: db)

    # Регистрируем репозитории
    container.singleton("user_repository", lambda container: UserRepository(db))

    # Обновляем конфигурацию
    container.singleton("config", lambda container: CloudflareConfig(env))

    # Регистрируем роуты
    register_routes()

    return app