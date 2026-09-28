"""
Конфигурация приложения.
Поддерживает два режима: локальный и Cloudflare.
"""
import os


class Config:
    """Базовая конфигурация для локальной разработки"""

    def __init__(self):
        self.DEBUG = os.getenv("DEBUG", "true")
        self.JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
        self.DB_PATH = os.getenv("DB_PATH", "data.db")
        self.HOST = os.getenv("HOST", "0.0.0.0")
        self.PORT = int(os.getenv("PORT", "8000"))

    def get(self, key):
        """Получение значения конфигурации"""
        return getattr(self, key, None)


class CloudflareConfig:
    """Конфигурация для Cloudflare Workers"""

    def __init__(self, env):
        self.env = env
        self.DEBUG = env.get("DEBUG", "false")
        self.JWT_SECRET = env.get("JWT_SECRET", "your-secret-key-change-in-production")

    def get(self, key):
        """Получение значения конфигурации"""
        return getattr(self, key, None)