# Техническое задание: Юнит-тесты Backend для BayLang Cloud AGI

## 1. Введение

### 1.1 Назначение документа

Данный документ описывает архитектуру, структуру и требования к **юнит-тестам** backend-компонентов проекта BayLang Cloud AGI. Тесты обеспечивают надёжность кода, упрощают рефакторинг и выявляют регрессии на ранних этапах разработки.

### 1.2 Контекст

Backend проекта построен на **FastAPI** и включает следующие ключевые модули:

- **DI Container** — управление зависимостями
- **AI Providers** — полиморфная система провайдеров (OpenRouter, OpenAI, Anthropic)
- **AI Models, Personas, Roles** — конфигурационные модели
- **AIService** — фасад для чата с fallback моделями
- **MCP Client / Manager** — интеграция с Model Context Protocol
- **Repositories (DAO)** — доступ к базе данных
- **API Routes** — HTTP эндпоинты

### 1.3 Цели тестирования

1. **Валидация бизнес-логики** — каждая единица кода работает корректно в изоляции
2. **Раннее выявление ошибок** — баги находятся до интеграции с другими модулями
3. **Документирование поведения** — тесты служат живой документацией ожидаемого поведения
4. **Безопасный рефакторинг** — возможность менять реализацию без страха сломать функциональность
5. **Регрессионное покрытие** — предотвращение повторения исправленных ошибок

---

## 2. Инструменты и фреймворки

### 2.1 Основные инструменты

| Инструмент | Назначение | Версия |
|-----------|-----------|--------|
| **pytest** | Фреймворк для запуска тестов | 7.x+ |
| **pytest-asyncio** | Поддержка async/await тестов | 0.21+ |
| **pytest-cov** | Измерение покрытия кода | 4.x+ |
| **unittest.mock** | Мокирование и подмена зависимостей | stdlib |
| **httpx** | Тестирование FastAPI эндпоинтов (TestClient) | 0.24+ |
| **aiosqlite** | Асинхронная SQLite для тестов | 0.19+ |

### 2.2 Конфигурация pytest

Создать файл `pytest.ini` или `pyproject.toml`:

```ini
# pytest.ini
[pytest]
testpaths = tests
asyncio_mode = auto
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --cov=src/core
    --cov-report=html
    --cov-report=term-missing
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (may use DB)
    slow: Slow tests
```

### 2.3 Структура каталога тестов

```
tests/
├── conftest.py                    # Глобальные фикстуры
├── unit/
│   ├── __init__.py
│   ├── container/
│   │   ├── __init__.py
│   │   └── test_container.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── test_config.py
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── providers/
│   │   │   ├── __init__.py
│   │   │   ├── test_base_provider.py
│   │   │   ├── test_openrouter_provider.py
│   │   │   ├── test_openai_provider.py
│   │   │   ├── test_anthropic_provider.py
│   │   │   └── test_provider_factory.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── test_ai_model.py
│   │   ├── personas/
│   │   │   ├── __init__.py
│   │   │   └── test_ai_persona.py
│   │   ├── roles/
│   │   │   ├── __init__.py
│   │   │   └── test_ai_role.py
│   │   ├── messages/
│   │   │   ├── __init__.py
│   │   │   └── test_message.py
│   │   ├── context/
│   │   │   ├── __init__.py
│   │   │   └── test_conversation_context.py
│   │   ├── mcp/
│   │   │   ├── __init__.py
│   │   │   ├── test_mcp_client.py
│   │   │   └── test_mcp_manager.py
│   │   ├── test_ai_service.py
│   │   └── test_message_processor.py
│   └── database/
│       ├── __init__.py
│       └── repositories/
│           ├── __init__.py
│           ├── test_base_repository.py
│           ├── test_provider_repository.py
│           ├── test_model_repository.py
│           ├── test_ai_repository.py
│           └── test_ai_role_repository.py
├── integration/
│   ├── __init__.py
│   ├── test_api_providers.py
│   ├── test_api_models.py
│   ├── test_api_personas.py
│   └── test_api_chat.py
└── fixtures/
    ├── providers.json
    ├── models.json
    ├── personas.json
    └── messages.json
```

---

## 3. Глобальные фикстуры (conftest.py)

### 3.1 Базовые фикстуры

```python
# tests/conftest.py

import pytest
import pytest_asyncio
import tempfile
import os
from unittest.mock import MagicMock, AsyncMock

# ─── Тестовая БД ──────────────────────────────────────

@pytest_asyncio.fixture
async def test_db():
    """Создание изолированной SQLite БД для каждого теста"""
    import aiosqlite
    
    # Временный файл БД
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    
    # Создание таблиц
    await db.execute("""
        CREATE TABLE IF NOT EXISTS providers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL,
            api_key TEXT NOT NULL,
            base_url TEXT,
            config TEXT DEFAULT '{}',
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await db.execute("""
        CREATE TABLE IF NOT EXISTS models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_id INTEGER NOT NULL,
            model_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            max_tokens INTEGER DEFAULT 4096,
            context_window INTEGER DEFAULT 128000,
            temperature REAL DEFAULT 0.7,
            top_p REAL DEFAULT 1.0,
            config TEXT DEFAULT '{}',
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (provider_id) REFERENCES providers(id) ON DELETE CASCADE
        )
    """)
    
    await db.execute("""
        CREATE TABLE IF NOT EXISTS ai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            slug TEXT NOT NULL UNIQUE,
            soul TEXT NOT NULL,
            avatar_url TEXT,
            temperature REAL DEFAULT 0.7,
            max_tokens INTEGER DEFAULT 4096,
            is_default INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await db.execute("""
        CREATE TABLE IF NOT EXISTS ai_models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ai_id INTEGER NOT NULL,
            model_id INTEGER NOT NULL,
            priority INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (ai_id) REFERENCES ai(id) ON DELETE CASCADE,
            FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE,
            UNIQUE(ai_id, model_id)
        )
    """)
    
    await db.execute("""
        CREATE TABLE IF NOT EXISTS ai_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ai_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            slug TEXT NOT NULL,
            prompt TEXT NOT NULL,
            icon TEXT,
            sort_order INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ai_id) REFERENCES ai(id) ON DELETE CASCADE
        )
    """)
    
    await db.commit()
    
    yield db
    
    await db.close()
    os.unlink(db_path)


@pytest.fixture
def mock_db():
    """Мок базы данных для unit-тестов"""
    db = MagicMock()
    db.execute = MagicMock()
    db.commit = AsyncMock()
    db.close = AsyncMock()
    return db


# ─── Тестовые данные ──────────────────────────────────

@pytest.fixture
def sample_provider_row():
    """Пример строки провайдера из БД"""
    return {
        "id": 1,
        "name": "openrouter",
        "type": "openrouter",
        "api_key": "sk-or-test123456789",
        "base_url": "https://openrouter.ai/api/v1",
        "config": '{"providers_list": ["openai"]}',
        "is_active": 1,
        "created_at": "2026-01-01 00:00:00",
        "updated_at": "2026-01-01 00:00:00"
    }


@pytest.fixture
def sample_model_row():
    """Пример строки модели из БД"""
    return {
        "id": 1,
        "provider_id": 1,
        "model_id": "openai/gpt-4o",
        "name": "GPT-4o",
        "description": "Best OpenAI model",
        "max_tokens": 4096,
        "context_window": 128000,
        "temperature": 0.7,
        "top_p": 1.0,
        "config": '{"supports_streaming": true, "supports_tools": true}',
        "is_active": 1,
        "created_at": "2026-01-01 00:00:00",
        "updated_at": "2026-01-01 00:00:00"
    }


@pytest.fixture
def sample_ai_row():
    """Пример строки AI-личности из БД"""
    return {
        "id": 1,
        "name": "Ассистент",
        "slug": "assistant",
        "soul": "Ты умный AI-ассистент.",
        "avatar_url": None,
        "temperature": 0.7,
        "max_tokens": 4096,
        "is_default": 1,
        "is_active": 1,
        "created_at": "2026-01-01 00:00:00",
        "updated_at": "2026-01-01 00:00:00"
    }


@pytest.fixture
def sample_role_row():
    """Пример строки роли из БД"""
    return {
        "id": 1,
        "ai_id": 1,
        "name": "Консультант",
        "slug": "consultant",
        "prompt": "Ты консультант. Задавай уточняющие вопросы.",
        "icon": "💬",
        "sort_order": 0,
        "is_active": 1,
        "created_at": "2026-01-01 00:00:00"
    }


@pytest.fixture
def sample_messages():
    """Пример списка сообщений для чата"""
    return [
        {"role": "system", "content": "Ты умный AI-ассистент."},
        {"role": "user", "content": "Привет! Как дела?"},
        {"role": "assistant", "content": "Привет! У меня всё отлично, спасибо!"},
    ]


# ─── Мок провайдера ──────────────────────────────────

@pytest.fixture
def mock_provider():
    """Мок BaseProvider для тестирования AIService"""
    from unittest.mock import MagicMock
    
    provider = MagicMock()
    provider.name = "test_provider"
    provider.is_active = True
    
    # Метод send возвращает стандартный ответ
    provider.send.return_value = {
        "content": "Test response from AI",
        "finish_reason": "stop",
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 20,
            "total_tokens": 70
        }
    }
    
    return provider
```

---

## 4. Тесты: DI Container

### 4.1 Описание модуля

`container.py` — простой DI-контейнер для управления зависимостями (singleton и transient).

### 4.2 Тесты

```python
# tests/unit/container/test_container.py

import pytest
from src.core.container import Container


class TestContainer:
    """Тесты DI-контейнера"""
    
    def test_singleton_returns_same_instance(self):
        """Singleton должен возвращать один и тот же экземпляр"""
        container = Container()
        
        container.singleton("config", lambda c: {"debug": True})
        
        instance1 = container.get("config")
        instance2 = container.get("config")
        
        assert instance1 is instance2
        assert instance1["debug"] is True
    
    def test_transient_returns_new_instance(self):
        """Transient должен создавать новый экземпляр каждый раз"""
        container = Container()
        
        call_count = 0
        
        def factory(c):
            nonlocal call_count
            call_count += 1
            return {"instance_id": call_count}
        
        container.register("service", factory)
        
        instance1 = container.get("service")
        instance2 = container.get("service")
        
        assert instance1 is not instance2
        assert instance1["instance_id"] != instance2["instance_id"]
    
    def test_get_returns_correct_value(self):
        """get() должен возвращать значение по имени"""
        container = Container()
        container.singleton("value", lambda c: 42)
        
        assert container.get("value") == 42
    
    def test_get_unregistered_raises_error(self):
        """Получение незарегистрированного имени вызывает ошибку"""
        container = Container()
        
        with pytest.raises(KeyError):
            container.get("nonexistent")
    
    def test_singleton_receives_container(self):
        """Singleton-фабрика получает контейнер как аргумент"""
        container = Container()
        container.singleton("self_ref", lambda c: c)
        
        result = container.get("self_ref")
        assert result is container
    
    def test_transient_receives_container(self):
        """Transient-фабрика получает контейнер как аргумент"""
        container = Container()
        container.register("dep", lambda c: "dependency")
        container.register("service", lambda c: c.get("dep"))
        
        result = container.get("service")
        assert result == "dependency"
    
    def test_register_overwrites_previous(self):
        """Повторная регистрация перезаписывает предыдущую"""
        container = Container()
        container.singleton("value", lambda c: 1)
        container.singleton("value", lambda c: 2)
        
        assert container.get("value") == 2
    
    def test_has_returns_true_for_registered(self):
        """has() возвращает True для зарегистрированных имен"""
        container = Container()
        container.singleton("exists", lambda c: None)
        
        assert container.has("exists") is True
        assert container.has("missing") is False
```

---

## 5. Тесты: AI Providers

### 5.1 Тесты BaseProvider

```python
# tests/unit/ai/providers/test_base_provider.py

import pytest
from unittest.mock import MagicMock, patch
from src.core.ai.providers.BaseProvider import BaseProvider, ProviderException


class ConcreteProvider(BaseProvider):
    """Конкретная реализация для тестирования абстрактного класса"""
    
    def _default_base_url(self) -> str:
        return "https://api.test.com/v1"
    
    def build_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def build_payload(self, model_id: str, messages: list, **kwargs) -> dict:
        return {"model": model_id, "messages": messages}
    
    def _parse_response(self, raw_response: dict) -> dict:
        choice = raw_response["choices"][0]
        return {
            "content": choice["message"]["content"],
            "finish_reason": choice.get("finish_reason", "stop"),
            "usage": raw_response.get("usage", {})
        }


class TestBaseProvider:
    """Тесты базового класса провайдера"""
    
    def test_init_from_row(self, sample_provider_row):
        """Инициализация из строки БД"""
        provider = ConcreteProvider(sample_provider_row)
        
        assert provider.id == 1
        assert provider.name == "openrouter"
        assert provider.type == "openrouter"
        assert provider.api_key == "sk-or-test123456789"
        assert provider.is_active is True
    
    def test_init_parses_json_config(self, sample_provider_row):
        """Конфигурация парсится из JSON строки"""
        provider = ConcreteProvider(sample_provider_row)
        
        assert isinstance(provider.config, dict)
        assert "providers_list" in provider.config
    
    def test_init_default_base_url(self, sample_provider_row):
        """Base URL по умолчанию используется при отсутствии в БД"""
        row = {**sample_provider_row, "base_url": None}
        provider = ConcreteProvider(row)
        
        assert provider.base_url == "https://api.test.com/v1"
    
    def test_send_inactive_provider_raises(self, sample_provider_row):
        """Отправка от неактивного провайдера вызывает ошибку"""
        row = {**sample_provider_row, "is_active": 0}
        provider = ConcreteProvider(row)
        
        with pytest.raises(ProviderException, match="отключён"):
            provider.send("model", [])
    
    @patch("src.core.ai.providers.BaseProvider.requests.post")
    def test_send_success(self, mock_post, sample_provider_row):
        """Успешная отправка запроса"""
        # Мок ответа
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {"content": "Hello!"},
                "finish_reason": "stop"
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        
        provider = ConcreteProvider(sample_provider_row)
        result = provider.send("gpt-4o", [{"role": "user", "content": "Hi"}])
        
        assert result["content"] == "Hello!"
        assert result["finish_reason"] == "stop"
        assert result["usage"]["total_tokens"] == 15
    
    @patch("src.core.ai.providers.BaseProvider.requests.post")
    def test_send_timeout_raises(self, mock_post, sample_provider_row):
        """Таймаут запроса вызывает ProviderException"""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout()
        
        provider = ConcreteProvider(sample_provider_row)
        
        with pytest.raises(ProviderException, match="Таймаут"):
            provider.send("gpt-4o", [{"role": "user", "content": "Hi"}])
    
    @patch("src.core.ai.providers.BaseProvider.requests.post")
    def test_send_connection_error_raises(self, mock_post, sample_provider_row):
        """Ошибка соединения вызывает ProviderException"""
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError()
        
        provider = ConcreteProvider(sample_provider_row)
        
        with pytest.raises(ProviderException, match="соединения"):
            provider.send("gpt-4o", [{"role": "user", "content": "Hi"}])
    
    @patch("src.core.ai.providers.BaseProvider.requests.post")
    def test_send_http_error_raises(self, mock_post, sample_provider_row):
        """HTTP ошибка вызывает ProviderException"""
        import requests
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )
        mock_post.return_value = mock_response
        
        provider = ConcreteProvider(sample_provider_row)
        
        with pytest.raises(ProviderException, match="HTTP ошибка"):
            provider.send("gpt-4o", [{"role": "user", "content": "Hi"}])
    
    def test_build_url(self, sample_provider_row):
        """Формирование URL для запроса"""
        provider = ConcreteProvider(sample_provider_row)
        url = provider._build_url()
        
        assert url == "https://openrouter.ai/api/v1/chat/completions"
    
    def test_repr(self, sample_provider_row):
        """Строковое представление провайдера"""
        provider = ConcreteProvider(sample_provider_row)
        repr_str = repr(provider)
        
        assert "ConcreteProvider" in repr_str
        assert "openrouter" in repr_str
```

### 5.2 Тесты OpenRouterProvider

```python
# tests/unit/ai/providers/test_openrouter_provider.py

import pytest
from src.core.ai.providers.OpenRouterProvider import OpenRouterProvider


class TestOpenRouterProvider:
    """Тесты провайдера OpenRouter"""
    
    def test_default_base_url(self, sample_provider_row):
        """URL по умолчанию для OpenRouter"""
        provider = OpenRouterProvider(sample_provider_row)
        assert provider.base_url == "https://openrouter.ai/api/v1"
    
    def test_build_headers(self, sample_provider_row):
        """Формирование заголовков"""
        provider = OpenRouterProvider(sample_provider_row)
        headers = provider.build_headers()
        
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer sk-or-test123456789"
        assert headers["Content-Type"] == "application/json"
        assert "HTTP-Referer" in headers
        assert "X-Title" in headers
    
    def test_build_payload_basic(self, sample_provider_row):
        """Формирование базового payload"""
        provider = OpenRouterProvider(sample_provider_row)
        messages = [{"role": "user", "content": "Hello"}]
        
        payload = provider.build_payload("gpt-4o", messages)
        
        assert payload["model"] == "gpt-4o"
        assert payload["messages"] == messages
    
    def test_build_payload_with_temperature(self, sample_provider_row):
        """Payload с temperature"""
        provider = OpenRouterProvider(sample_provider_row)
        messages = [{"role": "user", "content": "Hello"}]
        
        payload = provider.build_payload("gpt-4o", messages, temperature=0.5)
        
        assert payload["temperature"] == 0.5
    
    def test_build_payload_with_max_tokens(self, sample_provider_row):
        """Payload с max_tokens"""
        provider = OpenRouterProvider(sample_provider_row)
        messages = [{"role": "user", "content": "Hello"}]
        
        payload = provider.build_payload("gpt-4o", messages, max_tokens=2048)
        
        assert payload["max_tokens"] == 2048
    
    def test_build_payload_with_tools(self, sample_provider_row):
        """Payload с инструментами"""
        provider = OpenRouterProvider(sample_provider_row)
        messages = [{"role": "user", "content": "Hello"}]
        tools = [{"type": "function", "function": {"name": "get_weather"}}]
        
        payload = provider.build_payload("gpt-4o", messages, tools=tools)
        
        assert "tools" in payload
        assert len(payload["tools"]) == 1
    
    def test_build_payload_provider_priority(self, sample_provider_row):
        """Payload с приоритетными провайдерами OpenRouter"""
        provider = OpenRouterProvider(sample_provider_row)
        messages = [{"role": "user", "content": "Hello"}]
        
        payload = provider.build_payload("gpt-4o", messages)
        
        assert "provider" in payload
        assert "order" in payload["provider"]
    
    def test_parse_response(self, sample_provider_row):
        """Парсинг стандартного ответа"""
        provider = OpenRouterProvider(sample_provider_row)
        raw = {
            "choices": [{
                "message": {"content": "Hello!"},
                "finish_reason": "stop"
            }],
            "usage": {"total_tokens": 100}
        }
        
        result = provider._parse_response(raw)
        
        assert result["content"] == "Hello!"
        assert result["finish_reason"] == "stop"
        assert result["usage"]["total_tokens"] == 100
    
    def test_parse_response_with_tool_calls(self, sample_provider_row):
        """Парсинг ответа с tool_calls"""
        provider = OpenRouterProvider(sample_provider_row)
        raw = {
            "choices": [{
                "message": {
                    "content": "",
                    "tool_calls": [{"id": "call_123", "type": "function"}]
                },
                "finish_reason": "tool_calls"
            }],
            "usage": {}
        }
        
        result = provider._parse_response(raw)
        
        assert "tool_calls" in result
        assert len(result["tool_calls"]) == 1
```

### 5.3 Тесты ProviderFactory

```python
# tests/unit/ai/providers/test_provider_factory.py

import pytest
from src.core.ai.providers.ProviderFactory import ProviderFactory, ProviderException
from src.core.ai.providers.OpenRouterProvider import OpenRouterProvider
from src.core.ai.providers.OpenAIProvider import OpenAIProvider
from src.core.ai.providers.AnthropicProvider import AnthropicProvider


class TestProviderFactory:
    """Тесты фабрики провайдеров"""
    
    def test_create_openrouter(self, sample_provider_row):
        """Создание провайдера OpenRouter"""
        provider = ProviderFactory.create(sample_provider_row)
        
        assert isinstance(provider, OpenRouterProvider)
        assert provider.name == "openrouter"
    
    def test_create_openai(self, sample_provider_row):
        """Создание провайдера OpenAI"""
        row = {**sample_provider_row, "type": "openai", "name": "openai"}
        provider = ProviderFactory.create(row)
        
        assert isinstance(provider, OpenAIProvider)
    
    def test_create_anthropic(self, sample_provider_row):
        """Создание провайдера Anthropic"""
        row = {**sample_provider_row, "type": "anthropic", "name": "anthropic"}
        provider = ProviderFactory.create(row)
        
        assert isinstance(provider, AnthropicProvider)
    
    def test_create_unknown_type_raises(self, sample_provider_row):
        """Неизвестный тип провайдера вызывает ошибку"""
        row = {**sample_provider_row, "type": "unknown_provider"}
        
        with pytest.raises(ProviderException, match="Неизвестный тип"):
            ProviderFactory.create(row)
    
    def test_get_supported_types(self):
        """Получение списка поддерживаемых типов"""
        types = ProviderFactory.get_supported_types()
        
        assert "openrouter" in types
        assert "openai" in types
        assert "anthropic" in types
    
    def test_register_custom_provider(self, sample_provider_row):
        """Регистрация кастомного провайдера"""
        from src.core.ai.providers.BaseProvider import BaseProvider
        
        class CustomProvider(BaseProvider):
            def _default_base_url(self): return "https://custom.api.com"
            def build_headers(self): return {}
            def build_payload(self, model_id, messages, **kwargs): return {}
            def _parse_response(self, raw): return {}
        
        ProviderFactory.register("custom", CustomProvider)
        
        row = {**sample_provider_row, "type": "custom"}
        provider = ProviderFactory.create(row)
        
        assert isinstance(provider, CustomProvider)
        
        # Очистка
        del ProviderFactory._registry["custom"]
```

---

## 6. Тесты: AI Model, Persona, Role

### 6.1 Тесты AIModel

```python
# tests/unit/ai/models/test_ai_model.py

import pytest
from src.core.ai.models.AIModel import AIModel


class TestAIModel:
    """Тесты конфигурации модели LLM"""
    
    def test_init_from_row(self, sample_model_row):
        """Инициализация из строки БД"""
        model = AIModel(sample_model_row)
        
        assert model.id == 1
        assert model.provider_id == 1
        assert model.model_id == "openai/gpt-4o"
        assert model.name == "GPT-4o"
        assert model.max_tokens == 4096
        assert model.context_window == 128000
    
    def test_default_values(self):
        """Значения по умолчанию"""
        row = {
            "id": 1,
            "provider_id": 1,
            "model_id": "test-model",
            "name": "Test"
        }
        model = AIModel(row)
        
        assert model.description == ""
        assert model.max_tokens == 4096
        assert model.context_window == 128000
        assert model.temperature == 0.7
        assert model.top_p == 1.0
        assert model.is_active is True
    
    def test_to_dict(self, sample_model_row):
        """Сериализация в словарь"""
        model = AIModel(sample_model_row)
        d = model.to_dict()
        
        assert isinstance(d, dict)
        assert d["model_id"] == "openai/gpt-4o"
        assert d["config"]["supports_streaming"] is True
    
    def test_supports_streaming(self, sample_model_row):
        """Проверка поддержки streaming"""
        model = AIModel(sample_model_row)
        assert model.supports_streaming() is True
    
    def test_supports_tools(self, sample_model_row):
        """Проверка поддержки tool calling"""
        model = AIModel(sample_model_row)
        assert model.supports_tools() is True
    
    def test_supports_vision_false(self, sample_model_row):
        """Модель без поддержки vision"""
        model = AIModel(sample_model_row)
        assert model.supports_vision() is False
    
    def test_config_parsed_correctly(self, sample_model_row):
        """Конфигурация парсится из JSON"""
        model = AIModel(sample_model_row)
        
        assert isinstance(model.config, dict)
        assert "supports_streaming" in model.config
```

### 6.2 Тесты AIPersona

```python
# tests/unit/ai/personas/test_ai_persona.py

import pytest
from src.core.ai.personas.AIPersona import AIPersona
from src.core.ai.models.AIModel import AIModel


class TestAIPersona:
    """Тесты AI-личности"""
    
    def test_init_from_row(self, sample_ai_row):
        """Инициализация из строки БД"""
        persona = AIPersona(sample_ai_row)
        
        assert persona.id == 1
        assert persona.name == "Ассистент"
        assert persona.slug == "assistant"
        assert persona.soul == "Ты умный AI-ассистент."
        assert persona.is_default is True
    
    def test_get_system_messages(self, sample_ai_row):
        """Формирование системных сообщений"""
        persona = AIPersona(sample_ai_row)
        messages = persona.get_system_messages()
        
        assert len(messages) == 1
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == persona.soul
    
    def test_get_system_messages_with_role(self, sample_ai_row, sample_role_row):
        """Системные сообщения с ролью"""
        persona = AIPersona(sample_ai_row)
        
        # Добавляем роль
        from src.core.ai.roles.AIRole import AIRole
        role = AIRole(sample_role_row)
        persona.roles = [role]
        
        messages = persona.get_system_messages(role_slug="consultant")
        
        assert len(messages) == 1
        assert "Консультант" in messages[0]["content"]
        assert role.prompt in messages[0]["content"]
    
    def test_get_system_messages_unknown_role(self, sample_ai_row):
        """Неизвестная роль не добавляется в промпт"""
        persona = AIPersona(sample_ai_row)
        messages = persona.get_system_messages(role_slug="unknown")
        
        assert messages[0]["content"] == persona.soul
    
    def test_get_active_model(self, sample_ai_row, sample_model_row):
        """Получение основной активной модели"""
        persona = AIPersona(sample_ai_row)
        
        model1 = AIModel({**sample_model_row, "id": 1})
        model2 = AIModel({**sample_model_row, "id": 2, "model_id": "claude-3"})
        
        # Модель с priority=0 — основная
        model1.priority = 0
        model1.is_active = True
        model2.priority = 1
        model2.is_active = True
        
        persona.models = [model2, model1]  # Порядок перемешан
        
        active = persona.get_active_model()
        assert active.id == 1  # priority=0
    
    def test_get_active_model_none(self, sample_ai_row):
        """Нет активных моделей"""
        persona = AIPersona(sample_ai_row)
        persona.models = []
        
        assert persona.get_active_model() is None
    
    def test_get_fallback_models(self, sample_ai_row, sample_model_row):
        """Получение моделей fallback"""
        persona = AIPersona(sample_ai_row)
        
        model1 = AIModel({**sample_model_row, "id": 1})
        model1.priority = 0
        model1.is_active = True
        
        model2 = AIModel({**sample_model_row, "id": 2, "model_id": "claude-3"})
        model2.priority = 1
        model2.is_active = True
        
        model3 = AIModel({**sample_model_row, "id": 3, "model_id": "llama-3"})
        model3.priority = 2
        model3.is_active = True
        
        persona.models = [model1, model2, model3]
        
        fallbacks = persona.get_fallback_models()
        
        assert len(fallbacks) == 2
        assert all(m.priority > 0 for m in fallbacks)
    
    def test_to_dict(self, sample_ai_row):
        """Сериализация в словарь"""
        persona = AIPersona(sample_ai_row)
        d = persona.to_dict()
        
        assert isinstance(d, dict)
        assert d["slug"] == "assistant"
        assert "models" in d
        assert "roles" in d
```

### 6.3 Тесты AIRole

```python
# tests/unit/ai/roles/test_ai_role.py

import pytest
from src.core.ai.roles.AIRole import AIRole


class TestAIRole:
    """Тесты роли AI"""
    
    def test_init_from_row(self, sample_role_row):
        """Инициализация из строки БД"""
        role = AIRole(sample_role_row)
        
        assert role.id == 1
        assert role.ai_id == 1
        assert role.name == "Консультант"
        assert role.slug == "consultant"
        assert role.prompt == "Ты консультант. Задавай уточняющие вопросы."
        assert role.icon == "💬"
        assert role.sort_order == 0
    
    def test_to_dict(self, sample_role_row):
        """Сериализация в словарь"""
        role = AIRole(sample_role_row)
        d = role.to_dict()
        
        assert isinstance(d, dict)
        assert d["name"] == "Консультант"
        assert d["slug"] == "consultant"
        assert d["prompt"] == role.prompt
```

---

## 7. Тесты: ConversationContext

```python
# tests/unit/ai/context/test_conversation_context.py

import pytest
from src.core.ai.context.ConversationContext import ConversationContext
from src.core.ai.messages.Message import Message


class TestConversationContext:
    """Тесты контекста диалога"""
    
    def test_init_empty(self):
        """Пустой контекст при создании"""
        ctx = ConversationContext()
        messages = ctx.get_messages()
        
        assert isinstance(messages, list)
        assert len(messages) == 0
    
    def test_set_system(self):
        """Установка системного промпта"""
        ctx = ConversationContext()
        system_msg = [{"role": "system", "content": "You are helpful."}]
        
        ctx.set_system(system_msg)
        messages = ctx.get_messages()
        
        assert len(messages) == 1
        assert messages[0]["role"] == "system"
    
    def test_add_user_message(self):
        """Добавление сообщения пользователя"""
        ctx = ConversationContext()
        ctx.set_system([{"role": "system", "content": "You are helpful."}])
        
        ctx.add_message(Message.role_user("Hello!"))
        messages = ctx.get_messages()
        
        assert len(messages) == 2
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hello!"
    
    def test_add_ai_message(self):
        """Добавление ответа AI"""
        ctx = ConversationContext()
        ctx.set_system([{"role": "system", "content": "You are helpful."}])
        
        ctx.add_message(Message.role_user("Hello!"))
        ctx.add_message(Message.role_ai("Hi there!"))
        
        messages = ctx.get_messages()
        
        assert len(messages) == 3
        assert messages[2]["role"] == "assistant"
    
    def test_full_conversation_flow(self):
        """Полный поток диалога"""
        ctx = ConversationContext()
        
        # Система
        ctx.set_system([{"role": "system", "content": "AI assistant."}])
        
        # Пользователь
        ctx.add_message(Message.role_user("Привет!"))
        
        # AI
        ctx.add_message(Message.role_ai("Здравствуйте!"))
        
        # Пользователь
        ctx.add_message(Message.role_user("Как погода?"))
        
        messages = ctx.get_messages()
        
        assert len(messages) == 4
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[2]["role"] == "assistant"
        assert messages[3]["role"] == "user"
    
    def test_clear_context(self):
        """Очистка контекста"""
        ctx = ConversationContext()
        ctx.set_system([{"role": "system", "content": "AI assistant."}])
        ctx.add_message(Message.role_user("Hello!"))
        
        ctx.clear()
        messages = ctx.get_messages()
        
        assert len(messages) == 0
```

---

## 8. Тесты: MCP Client

```python
# tests/unit/ai/mcp/test_mcp_client.py

import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock
from src.core.ai.mcp.MCPClient import MCPClient


class TestMCPClient:
    """Тесты клиента Model Context Protocol"""
    
    def test_init(self):
        """Инициализация клиента"""
        client = MCPClient("/usr/bin/mcp-server", ["--verbose"])
        
        assert client.path == "/usr/bin/mcp-server"
        assert client.args == ["--verbose"]
        assert client.process is None
        assert client.request_id == 0
    
    def test_init_default_args(self):
        """Аргументы по умолчанию"""
        client = MCPClient("/usr/bin/mcp-server")
        
        assert client.args == []
    
    def test_is_connected_false_initially(self):
        """Изначально не подключён"""
        client = MCPClient("/usr/bin/mcp-server")
        
        assert client.is_connected() is False
    
    @patch("src.core.ai.mcp.MCPClient.subprocess.Popen")
    def test_start_server(self, mock_popen):
        """Запуск сервера"""
        mock_process = MagicMock()
        mock_popen.return_value = mock_process
        
        client = MCPClient("/usr/bin/mcp-server")
        client.start_server()
        
        mock_popen.assert_called_once()
        assert client.process == mock_process
    
    @patch("src.core.ai.mcp.MCPClient.subprocess.Popen")
    def test_is_connected_true_after_start(self, mock_popen):
        """Подключён после запуска сервера"""
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Процесс жив
        mock_popen.return_value = mock_process
        
        client = MCPClient("/usr/bin/mcp-server")
        client.start_server()
        
        assert client.is_connected() is True
    
    @patch("src.core.ai.mcp.MCPClient.subprocess.Popen")
    def test_stop_server(self, mock_popen):
        """Остановка сервера"""
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        client = MCPClient("/usr/bin/mcp-server")
        client.start_server()
        client.stop_server()
        
        mock_process.terminate.assert_called_once()
        assert client.process is None
    
    @patch("src.core.ai.mcp.MCPClient.select.select")
    @patch("src.core.ai.mcp.MCPClient.subprocess.Popen")
    def test_send_message(self, mock_popen, mock_select):
        """Отправка JSON-RPC сообщения"""
        # Мок процесса
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.stdin = MagicMock()
        mock_process.stdout = MagicMock()
        mock_popen.return_value = mock_process
        
        # Мок select — stdout готов
        mock_select.return_value = ([mock_process.stdout], [], [])
        
        # Мок ответа
        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"tools": []}
        }
        mock_process.stdout.readline.return_value = json.dumps(response) + "\n"
        
        client = MCPClient("/usr/bin/mcp-server")
        client.start_server()
        result = client.send_message("tools/list")
        
        assert result["result"] == {"tools": []}
        assert client.request_id == 1
    
    @patch("src.core.ai.mcp.MCPClient.select.select")
    @patch("src.core.ai.mcp.MCPClient.subprocess.Popen")
    def test_send_message_timeout(self, mock_popen, mock_select):
        """Таймаут при отправке сообщения"""
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.stdin = MagicMock()
        mock_popen.return_value = mock_process
        
        # Мок select — таймаут (пустой список готовых)
        mock_select.return_value = ([], [], [])
        
        client = MCPClient("/usr/bin/mcp-server")
        client.start_server()
        
        with pytest.raises(Exception, match="Таймаут"):
            client.send_message("tools/list", timeout=1)
    
    @patch("src.core.ai.mcp.MCPClient.MCPClient.send_message")
    @patch("src.core.ai.mcp.MCPClient.MCPClient.connect")
    def test_initialize(self, mock_connect, mock_send):
        """Инициализация MCP соединения"""
        mock_send.return_value = {"result": {"protocolVersion": "2025-06-18"}}
        
        client = MCPClient("/usr/bin/mcp-server")
        result = client.initialize()
        
        mock_send.assert_called_once_with("initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {
                "name": "BayLang AI",
                "version": "1.0.0",
            }
        })
    
    @patch("src.core.ai.mcp.MCPClient.MCPClient.send_message")
    @patch("src.core.ai.mcp.MCPClient.MCPClient.connect")
    def test_list_tools(self, mock_connect, mock_send):
        """Получение списка инструментов"""
        tools = [{"name": "read_file", "description": "Read a file"}]
        mock_send.return_value = {"result": {"tools": tools}}
        
        client = MCPClient("/usr/bin/mcp-server")
        result = client.list_tools()
        
        assert len(result) == 1
        assert result[0]["name"] == "read_file"
    
    @patch("src.core.ai.mcp.MCPClient.MCPClient.send_message")
    @patch("src.core.ai.mcp.MCPClient.MCPClient.connect")
    def test_execute(self, mock_connect, mock_send):
        """Вызов инструмента"""
        mock_send.return_value = {"result": {"content": "File contents"}}
        
        client = MCPClient("/usr/bin/mcp-server")
        result = client.execute("read_file", {"path": "/tmp/test.txt"})
        
        mock_send.assert_called_once_with("tools/call", {
            "name": "read_file",
            "arguments": {"path": "/tmp/test.txt"}
        })
    
    def test_context_manager(self):
        """Контекстный менеджер"""
        with patch.object(MCPClient, "connect") as mock_connect:
            with patch.object(MCPClient, "stop_server") as mock_stop:
                with MCPClient("/usr/bin/mcp-server") as client:
                    assert isinstance(client, MCPClient)
                
                mock_stop.assert_called_once()
```

---

## 9. Тесты: MCP Manager

```python
# tests/unit/ai/mcp/test_mcp_manager.py

import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock
from src.core.ai.mcp.MCPManager import MCPManager
from src.core.ai.mcp.MCPClient import MCPClient


class TestMCPManager:
    """Тесты менеджера MCP серверов"""
    
    def test_init_empty(self):
        """Пустой менеджер при создании"""
        manager = MCPManager()
        
        assert manager.clients == {}
        assert manager.tools_cache == {}
    
    def test_load_config(self):
        """Загрузка конфигурации из списка"""
        config = [
            {"name": "filesystem", "path": "/usr/bin/mcp-fs", "args": ["--root"]},
            {"name": "api", "path": "/usr/bin/mcp-api", "enabled": False}
        ]
        
        manager = MCPManager()
        manager.load_config(config)
        
        assert "filesystem" in manager.clients
        assert isinstance(manager.clients["filesystem"], MCPClient)
        assert "api" not in manager.clients  # disabled
    
    def test_load_config_disabled_server(self):
        """Отключённые серверы не загружаются"""
        config = [
            {"name": "disabled", "path": "/usr/bin/mcp", "enabled": False}
        ]
        
        manager = MCPManager()
        manager.load_config(config)
        
        assert len(manager.clients) == 0
    
    @patch("src.core.ai.mcp.MCPManager.MCPManager.load_config")
    @patch("os.getenv")
    def test_load_from_env(self, mock_getenv, mock_load):
        """Загрузка конфигурации из переменных окружения"""
        config_data = json.dumps([
            {"name": "filesystem", "path": "/usr/bin/mcp-fs"}
        ])
        mock_getenv.return_value = config_data
        
        manager = MCPManager()
        manager.load_from_env()
        
        mock_load.assert_called_once()
    
    @patch("os.getenv")
    def test_load_from_env_empty(self, mock_getenv):
        """Пустая переменная окружения"""
        mock_getenv.return_value = None
        
        manager = MCPManager()
        manager.load_from_env()  # Не должно вызвать ошибку
    
    @patch("os.getenv")
    def test_load_from_env_invalid_json(self, mock_getenv):
        """Невалидный JSON в переменной окружения"""
        mock_getenv.return_value = "not a json"
        
        manager = MCPManager()
        manager.load_from_env()  # Не должно вызвать ошибку
    
    @patch.object(MCPClient, "connect")
    def test_connect_all(self, mock_connect):
        """Подключение всех серверов"""
        manager = MCPManager()
        manager.load_config([
            {"name": "fs", "path": "/usr/bin/mcp-fs"},
            {"name": "api", "path": "/usr/bin/mcp-api"}
        ])
        
        manager.connect_all()
        
        assert mock_connect.call_count == 2
    
    @patch.object(MCPClient, "connect")
    def test_connect_all_error_continues(self, mock_connect):
        """Ошибка подключения одного сервера не блокирует другие"""
        def side_effect():
            raise Exception("Connection failed")
        
        mock_connect.side_effect = side_effect
        
        manager = MCPManager()
        manager.load_config([
            {"name": "fs", "path": "/usr/bin/mcp-fs"},
            {"name": "api", "path": "/usr/bin/mcp-api"}
        ])
        
        # Не должно выбросить исключение
        manager.connect_all()
    
    @patch.object(MCPClient, "stop_server")
    def test_disconnect_all(self, mock_stop):
        """Отключение всех серверов"""
        manager = MCPManager()
        manager.load_config([
            {"name": "fs", "path": "/usr/bin/mcp-fs"},
            {"name": "api", "path": "/usr/bin/mcp-api"}
        ])
        
        manager.disconnect_all()
        
        assert mock_stop.call_count == 2
    
    def test_get_all_tools(self):
        """Получение инструментов со всех серверов"""
        manager = MCPManager()
        
        # Мок клиента
        mock_client = MagicMock()
        mock_client.is_connected.return_value = True
        mock_client.list_tools.return_value = [
            {"name": "read_file", "description": "Read file"},
            {"name": "write_file", "description": "Write file"}
        ]
        
        manager.clients = {"filesystem": mock_client}
        
        tools = manager.get_all_tools()
        
        assert "filesystem:read_file" in tools
        assert "filesystem:write_file" in tools
        assert tools["filesystem:read_file"]["server"] == "filesystem"
    
    def test_execute_tool(self):
        """Вызов инструмента"""
        manager = MCPManager()
        
        mock_client = MagicMock()
        mock_client.is_connected.return_value = True
        mock_client.execute.return_value = {"result": "success"}
        
        manager.clients = {"filesystem": mock_client}
        
        result = manager.execute_tool("filesystem:read_file", {"path": "/tmp/test.txt"})
        
        assert result == {"result": "success"}
        mock_client.execute.assert_called_once_with("read_file", {"path": "/tmp/test.txt"})
    
    def test_execute_tool_invalid_format(self):
        """Неверный формат имени инструмента"""
        manager = MCPManager()
        
        with pytest.raises(ValueError, match="Неверный формат"):
            manager.execute_tool("invalid_format", {})
    
    def test_execute_tool_unknown_server(self):
        """Неизвестный сервер"""
        manager = MCPManager()
        
        with pytest.raises(ValueError, match="не найден"):
            manager.execute_tool("unknown:tool", {})
    
    @patch.object(MCPClient, "connect")
    def test_execute_tool_reconnects(self, mock_connect):
        """Переподключение при вызове инструмента на отключённом сервере"""
        manager = MCPManager()
        
        mock_client = MagicMock()
        mock_client.is_connected.return_value = False  # Не подключён
        mock_client.execute.return_value = {"result": "success"}
        
        manager.clients = {"fs": mock_client}
        
        manager.execute_tool("fs:read_file", {"path": "/tmp"})
        
        mock_client.connect.assert_called_once()
```

---

## 10. Тесты: AIService (Фасад)

### 10.1 Описание

`AIService` — главный фасад, связывающий провайдеры, репозитории, контекст и логику чата с fallback моделями.

### 10.2 Тесты

```python
# tests/unit/ai/test_ai_service.py

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.core.ai.AIService import AIService
from src.core.ai.providers.ProviderException import ProviderException


class TestAIService:
    """Тесты основного сервиса AI"""
    
    def setup_method(self):
        """Подготовка моков перед каждым тестом"""
        self.provider_repo = MagicMock()
        self.model_repo = MagicMock()
        self.ai_repo = MagicMock()
        self.role_repo = MagicMock()
        
        self.service = AIService(
            provider_repo=self.provider_repo,
            model_repo=self.model_repo,
            ai_repo=self.ai_repo,
            role_repo=self.role_repo
        )
    
    def test_get_provider_caches(self):
        """Провайдер кэшируется после первого получения"""
        provider_row = {
            "id": 1, "name": "test", "type": "openrouter",
            "api_key": "sk-test", "is_active": 1
        }
        self.provider_repo.find_by_id.return_value = provider_row
        
        p1 = self.service.get_provider(1)
        p2 = self.service.get_provider(1)
        
        assert p1 is p2
        assert self.provider_repo.find_by_id.call_count == 1
    
    def test_get_provider_not_found(self):
        """Ошибка при несуществующем провайдере"""
        self.provider_repo.find_by_id.return_value = None
        
        with pytest.raises(ValueError, match="не найден"):
            self.service.get_provider(999)
    
    def test_invalidate_provider_cache(self):
        """Очистка кэша провайдера"""
        provider_row = {
            "id": 1, "name": "test", "type": "openrouter",
            "api_key": "sk-test", "is_active": 1
        }
        self.provider_repo.find_by_id.return_value = provider_row
        
        self.service.get_provider(1)
        self.service.invalidate_provider_cache(1)
        
        # Следующий вызов создаст новый экземпляр
        self.service.get_provider(1)
        assert self.provider_repo.find_by_id.call_count == 2
    
    def test_chat_ai_not_found(self):
        """Чат с несуществующей AI-личностью"""
        self.ai_repo.find_by_slug_with_models_and_roles.return_value = None
        
        with pytest.raises(ValueError, match="не найдена"):
            self.service.chat("nonexistent", "Hello")
    
    def test_chat_no_active_models(self):
        """Чат без доступных моделей"""
        mock_ai = MagicMock()
        mock_ai.get_active_model.return_value = None
        self.ai_repo.find_by_slug_with_models_and_roles.return_value = mock_ai
        
        with pytest.raises(ValueError, match="Нет доступных моделей"):
            self.service.chat("assistant", "Hello")
    
    def test_chat_success(self):
        """Успешный чат"""
        # Мок AI
        mock_ai = MagicMock()
        mock_ai.temperature = 0.7
        mock_ai.max_tokens = 4096
        mock_ai.get_system_messages.return_value = [
            {"role": "system", "content": "You are helpful."}
        ]
        
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.provider_id = 1
        mock_model.model_id = "gpt-4o"
        mock_model.is_active = True
        
        mock_ai.get_active_model.return_value = mock_model
        mock_ai.get_fallback_models.return_value = []
        
        self.ai_repo.find_by_slug_with_models_and_roles.return_value = mock_ai)
        
        # Мок провайдера
        mock_provider = MagicMock()
        mock_provider.name = "openrouter"
        mock_provider.send.return_value = {
            "content": "Hello from AI!",
            "finish_reason": "stop",
            "usage": {"total_tokens": 50}
        }
        self.service._providers_cache = {1: mock_provider}
        
        result = self.service.chat("assistant", "Hi there!")
        
        assert result["content"] == "Hello from AI!"
        assert result["model_used"] == "gpt-4o"
        assert result["provider_used"] == "openrouter"
    
    def test_chat_with_fallback(self):
        """Чат с fallback на альтернативную модель"""
        # Мок AI
        mock_ai = MagicMock()
        mock_ai.temperature = 0.7
        mock_ai.max_tokens = 4096
        mock_ai.get_system_messages.return_value = [
            {"role": "system", "content": "You are helpful."}
        ]
        
        # Основная модель
        mock_primary = MagicMock()
        mock_primary.id = 1
        mock_primary.provider_id = 1
        mock_primary.model_id = "gpt-4o"
        mock_primary.is_active = True
        
        # Fallback модель
        mock_fallback = MagicMock()
        mock_fallback.id = 2
        mock_fallback.provider_id = 2
        mock_fallback.model_id = "claude-3"
        mock_fallback.priority = 1
        mock_fallback.is_active = True
        
        mock_ai.get_active_model.return_value = mock_primary
        mock_ai.get_fallback_models.return_value = [mock_fallback]
        
        self.ai_repo.find_by_slug_with_models_and_roles.return_value = mock_ai
        
        # Мок провайдеров
        mock_provider1 = MagicMock()
        mock_provider1.send.side_effect = ProviderException("Model unavailable")
        
        mock_provider2 = MagicMock()
        mock_provider2.name = "anthropic"
        mock_provider2.send.return_value = {
            "content": "Response from Claude",
            "finish_reason": "stop",
            "usage": {}
        }
        
        self.service._providers_cache = {1: mock_provider1, 2: mock_provider2}
        
        result = self.service.chat("assistant", "Hi!")
        
        assert result["content"] == "Response from Claude"
        assert result["model_used"] == "claude-3"
    
    def test_chat_all_models_fail(self):
        """Все модели недоступны"""
        mock_ai = MagicMock()
        mock_ai.temperature = 0.7
        mock_ai.max_tokens = 4096
        mock_ai.get_system_messages.return_value = [
            {"role": "system", "content": "System"}
        ]
        
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.provider_id = 1
        mock_model.model_id = "gpt-4o"
        mock_model.is_active = True
        
        mock_ai.get_active_model.return_value = mock_model
        mock_ai.get_fallback_models.return_value = []
        
        self.ai_repo.find_by_slug_with_models_and_roles.return_value = mock_ai
        
        mock_provider = MagicMock()
        mock_provider.send.side_effect = ProviderException("Error")
        self.service._providers_cache = {1: mock_provider}
        
        with pytest.raises(ProviderException, match="Все модели"):
            self.service.chat("assistant", "Hi!")
    
    def test_clear_context(self):
        """Очистка контекста сессии"""
        # Создаём контекст
        self.service._contexts["session1"] = MagicMock()
        
        self.service.clear_context("session1")
        
        assert "session1" not in self.service._contexts
    
    def test_get_context_creates_new(self):
        """Создание нового контекста"""
        ctx = self.service._get_context("new_session")
        
        assert ctx is not None
        assert "new_session" in self.service._contexts
    
    def test_get_context_reuses_existing(self):
        """Переиспользование существующего контекста"""
        ctx1 = self.service._get_context("session1")
        ctx2 = self.service._get_context("session1")
        
        assert ctx1 is ctx2
```

---

## 11. Тесты: Repositories (DAO)

### 11.1 Тесты ProviderRepository

```python
# tests/unit/database/repositories/test_provider_repository.py

import pytest
import pytest_asyncio
from src.core.database.repositories.ProviderRepository import ProviderRepository


class TestProviderRepository:
    """Тесты репозитория провайдеров"""
    
    @pytest_asyncio.fixture
    async def repo(self, test_db):
        """Создание репозитория с тестовой БД"""
        # Оборачиваем aiosqlite в совместимый интерфейс
        class DBWrapper:
            def __init__(self, db):
                self.db = db
            
            async def execute(self, query, params=None):
                cursor = await self.db.execute(query, params or [])
                return cursor
            
            async def fetchone(self, cursor):
                return await cursor.fetchone()
            
            async def fetchall(self, cursor):
                return await cursor.fetchall()
        
        wrapper = DBWrapper(test_db)
        return ProviderRepository(wrapper)
    
    @pytest.mark.asyncio
    async def test_create_provider(self, repo):
        """Создание провайдера"""
        data = {
            "name": "test_provider",
            "type": "openrouter",
            "api_key": "sk-test-123",
            "base_url": "https://api.test.com",
            "config": "{}",
            "is_active": 1
        }
        
        provider_id = await repo.create(data)
        
        assert provider_id > 0
    
    @pytest.mark.asyncio
    async def test_find_by_id(self, repo):
        """Поиск провайдера по ID"""
        # Создаём
        data = {
            "name": "find_test",
            "type": "openrouter",
            "api_key": "sk-test",
            "is_active": 1
        }
        provider_id = await repo.create(data)
        
        # Ищем
        result = await repo.find_by_id(provider_id)
        
        assert result is not None
        assert result["name"] == "find_test"
    
    @pytest.mark.asyncio
    async def test_find_by_id_not_found(self, repo):
        """Провайдер не найден"""
        result = await repo.find_by_id(99999)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_find_by_name(self, repo):
        """Поиск провайдера по имени"""
        data = {
            "name": "named_provider",
            "type": "openai",
            "api_key": "sk-test",
            "is_active": 1
        }
        await repo.create(data)
        
        result = await repo.find_by_name("named_provider")
        
        assert result is not None
        assert result["type"] == "openai"
    
    @pytest.mark.asyncio
    async def test_find_all(self, repo):
        """Получение всех провайдеров"""
        # Создаём несколько
        for i in range(3):
            await repo.create({
                "name": f"provider_{i}",
                "type": "openrouter",
                "api_key": f"sk-{i}",
                "is_active": 1
            })
        
        results = await repo.find_all()
        
        assert len(results) >= 3
    
    @pytest.mark.asyncio
    async def test_update_provider(self, repo):
        """Обновление провайдера"""
        # Создаём
        data = {
            "name": "update_test",
            "type": "openrouter",
            "api_key": "sk-old",
            "is_active": 1
        }
        provider_id = await repo.create(data)
        
        # Обновляем
        await repo.update(provider_id, {"api_key": "sk-new"})
        
        # Проверяем
        result = await repo.find_by_id(provider_id)
        assert result["api_key"] == "sk-new"
    
    @pytest.mark.asyncio
    async def test_delete_provider(self, repo):
        """Удаление провайдера"""
        data = {
            "name": "delete_test",
            "type": "openrouter",
            "api_key": "sk-test",
            "is_active": 1
        }
        provider_id = await repo.create(data)
        
        await repo.delete(provider_id)
        
        result = await repo.find_by_id(provider_id)
        assert result is None
```

---

## 12. Тесты: Message

```python
# tests/unit/ai/messages/test_message.py

import pytest
from src.core.ai.messages.Message import Message


class TestMessage:
    """Тесты класса Message"""
    
    def test_role_user(self):
        """Создание сообщения пользователя"""
        msg = Message.role_user("Hello!")
        
        assert msg["role"] == "user"
        assert msg["content"] == "Hello!"
    
    def test_role_ai(self):
        """Создание ответа AI"""
        msg = Message.role_ai("Hi there!")
        
        assert msg["role"] == "assistant"
        assert msg["content"] == "Hi there!"
    
    def test_role_system(self):
        """Создание системного сообщения"""
        msg = Message.role_system("You are helpful.")
        
        assert msg["role"] == "system"
        assert msg["content"] == "You are helpful."
```

---

## 13. Конфигурация покрытия кода

### 13.1 Целевые метрики

| Модуль | Минимальное покрытие | Приоритет |
|--------|---------------------|-----------|
| Container | 100% | 🔴 Критичный |
| Config | 95% | 🔴 Критичный |
| BaseProvider | 90% | 🔴 Критичный |
| ProviderFactory | 100% | 🔴 Критичный |
| OpenRouterProvider | 85% | 🔴 Критичный |
| OpenAIProvider | 85% | 🟡 Средний |
| AnthropicProvider | 85% | 🟡 Средний |
| AIModel | 100% | 🔴 Критичный |
| AIPersona | 95% | 🔴 Критичный |
| AIRole | 100% | 🔴 Критичный |
| ConversationContext | 100% | 🔴 Критичный |
| Message | 100% | 🔴 Критичный |
| AIService | 90% | 🔴 Критичный |
| MCPClient | 85% | 🟡 Средний |
| MCPManager | 90% | 🟡 Средний |
| Repositories | 80% | 🟡 Средний |

### 13.2 Генерация отчёта

```bash
# Запуск тестов с покрытием
pytest --cov=src/core --cov-report=html

# Открытие отчёта
open htmlcov/index.html
```

---

## 14. Приоритеты тестирования

### 14.1 Фаза 1: Критичные компоненты (1-2 дня)

1. **Container** — DI-контейнер (все зависимости от него)
2. **BaseProvider + ProviderFactory** — фундамент AI-системы
3. **AIModel, AIPersona, AIRole** — конфигурационные модели
4. **Message, ConversationContext** — основа чата

### 14.2 Фаза 2: Бизнес-логика (2-3 дня)

5. **OpenRouterProvider** — основной провайдер
6. **AIService** — фасад с fallback
7. **Repositories** — доступ к БД
8. **MCPClient** — интеграция с инструментами

### 14.3 Фаза 3: Дополнительные компоненты (1-2 дня)

9. **OpenAIProvider, AnthropicProvider** — доп. провайдеры
10. **MCPManager** — менеджер нескольких серверов
11. **MessageProcessor** — обработка ответов

---

## 15. Оценка трудозатрат

| Задача | Оценка |
|--------|--------|
| Настройка pytest + conftest.py | 2–3 часа |
| Тесты Container + Config | 2–3 часа |
| Тесты Providers (все) | 4–5 часов |
| Тесты Models (AIModel, Persona, Role) | 3–4 часа |
| Тесты ConversationContext + Message | 2–3 часа |
| Тесты AIService | 3–4 часа |
| Тесты MCP (Client + Manager) | 3–4 часа |
| Тесты Repositories | 3–4 часа |
| Настройка coverage + CI | 1–2 часа |
| **ИТОГО** | **23–32 часа** |

---

## 16. Запуск тестов

### 16.1 Команды

```bash
# Все тесты
pytest

# Только unit-тесты
pytest tests/unit/

# Только integration-тесты
pytest tests/integration/

# С покрытием
pytest --cov=src/core

# С отчётом HTML
pytest --cov=src/core --cov-report=html

# Конкретный файл
pytest tests/unit/ai/providers/test_provider_factory.py -v

# Конкретный тест
pytest tests/unit/ai/test_ai_service.py::TestAIService::test_chat_success -v

# Запуск с маркерами
pytest -m "not slow"
```

### 16.2 CI/CD интеграция

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov httpx aiosqlite
      
      - name: Run tests
        run: pytest --cov=src/core --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
```

---

## 17. Итог

Данная техническая спецификация описывает полную архитектуру **юнит-тестов** backend-компонентов BayLang Cloud AGI.

**Ключевые решения:**

1. **Фреймворк pytest** — де-факто стандарт для Python, поддержка async/await через pytest-asyncio
2. **Изоляция тестов** — каждый тест работает с изолированной SQLite БД или моками
3. **Покрытие критичных компонентов** — Container, Providers, Models, AIService требуют ≥90% покрытия
4. **CI/CD интеграция** — автоматический запуск тестов при каждом коммите

**Результат:** Надёжная тестовая инфраструктура, гарантирующая стабильность кодовой базы и безопасный рефакторинг.

---

*Последнее обновление: 25 сентября 2026 года*  
*Статус: Готов к реализации*  
*Ответственный: Лея*
