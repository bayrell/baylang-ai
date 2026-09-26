# Техническое задание: AI Backend + Frontend

## 1. Введение и контекст

### 1.1 Назначение документа

Данный документ описывает архитектуру и реализацию **AI подсистемы** проекта BayLang Cloud AGI — backend-модели для управления провайдерами LLM, моделями, AI-личностями и ролями, а также frontend-интерфейс для администрирования этих сущностей.

### 1.2 Текущее состояние

На данный момент проект содержит:
- **Консольный ассистент** (`console.py`) — простой CLI с прямым вызовом OpenRouter API
- **MCP Client** (`core/ai/MCPClient.py`) — клиент Model Context Protocol (с багами)
- **DI Container** (`core/container.py`) — система управления зависимостями
- **Базовый FastAPI-сервер** (`core/app.py`) — с маршрутизацией и шаблонами
- **Vue 3 фронтенд** — минимальный Layout без страниц

### 1.3 Цели разработки

1. **Структурировать AI-подсистему** в `core/ai/` с чётким разделением ответственности
2. **Создать базу данных** для хранения конфигураций провайдеров, моделей, AI и ролей
3. **Реализовать классы-провайдеры** с полиморфной отправкой запросов
4. **Построить CRUD API** для администрирования всех AI-сущностей
5. **Создать Vue-интерфейс** для визуального управления конфигурацией AI

---

## 2. Архитектура backend

### 2.1 Структура каталогов

```
src/core/
├── ai/
│   ├── __init__.py
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── BaseProvider.py        # Базовый абстрактный класс провайдера
│   │   ├── OpenRouterProvider.py   # Реализация для OpenRouter
│   │   ├── OpenAIProvider.py       # Реализация для OpenAI
│   │   ├── AnthropicProvider.py    # Реализация для Anthropic
│   │   └── ProviderFactory.py      # Фабрика создания провайдеров
│   ├── models/
│   │   ├── __init__.py
│   │   └── AIModel.py             # Конфигурация модели LLM
│   ├── personas/
│   │   ├── __init__.py
│   │   └── AIPersona.py           # Личность ИИ (soul / system prompt)
│   ├── roles/
│   │   ├── __init__.py
│   │   └── AIRole.py              # Роль ИИ (например: переводчик, аналитик)
│   ├── messages/
│   │   ├── __init__.py
│   │   └── Message.py             # Классы сообщений (User/AI/System)
│   ├── context/
│   │   ├── __init__.py
│   │   └── ConversationContext.py  # Контекст диалога (история + сессия)
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── MCPClient.py           # Клиент MCP (исправленный)
│   │   └── MCPManager.py          # Менеджер нескольких MCP серверов
│   ├── AIService.py               # Основной сервис AI (фасад)
│   └── MessageProcessor.py        # Обработка ответов (tool_call, streaming)
│
├── database/
│   ├── __init__.py
│   ├── Database.py                # Абстракция БД (SQLite / D1)
│   ├── migrations/
│   │   ├── __init__.py
│   │   ├── Migration.py           # Базовый класс миграции
│   │   ├── Migration_001_Providers.py
│   │   ├── Migration_002_Models.py
│   │   ├── Migration_003_AI.py
│   │   └── Migration_004_AIRoles.py
│   └── repositories/
│       ├── __init__.py
│       ├── ProviderRepository.py
│       ├── ModelRepository.py
│       ├── AIRepository.py
│       └── AIRoleRepository.py
│
├── api/
│   ├── __init__.py
│   ├── ai_routes.py               # API: управление провайдерами
│   ├── models_routes.py           # API: управление моделями
│   ├── personas_routes.py         # API: управление личностями
│   ├── roles_routes.py            # API: управление ролями
│   └── chat_routes.py             # API: чат с ИИ
│
├── app.py                         # FastAPI + DI Container (обновлённый)
├── container.py                   # DI контейнер
├── config.py                      # Конфигурация
└── routes.py                      # Корневые роуты
```

### 2.2 Диаграмма зависимостей

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (Vue 3)                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │ Providers │ │  Models  │ │ Personas │ │ Roles  │ │
│  │  Page     │ │  Page    │ │  Page    │ │  Page  │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └───┬────┘ │
│       └─────────────┴────────────┴───────────┘      │
└──────────────────────────┬──────────────────────────┘
                           │ HTTP API
┌──────────────────────────┴──────────────────────────┐
│                  Backend (FastAPI)                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │ AI API   │ │Models API│ │Personas  │ │Roles   │ │
│  │ Routes   │ │ Routes   │ │Routes    │ │Routes  │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └───┬────┘ │
│       └─────────────┴────────────┴───────────┘      │
│                           │                          │
│  ┌────────────────────────┴────────────────────────┐│
│  │              Repositories (DAO)                  ││
│  └────────────────────────┬────────────────────────┘│
│                           │                          │
│  ┌────────────────────────┴────────────────────────┐│
│  │          Database (SQLite / D1)                  ││
│  └─────────────────────────────────────────────────┘│
│                                                      │
│  ┌─────────────────────────────────────────────────┐│
│  │              AI Service (Фасад)                  ││
│  │  ┌───────────┐ ┌──────────┐ ┌────────────────┐  ││
│  │  │ Provider  │ │ AIModel  │ │ Conversation   │  ││
│  │  │ Factory   │ │ Config   │ │ Context        │  ││
│  │  └───────────┘ └──────────┘ └────────────────┘  ││
│  └─────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

---

## 3. Схема базы данных

### 3.1 Таблица `providers`

Хранит конфигурацию AI-провайдеров (OpenRouter, OpenAI, Anthropic и т.д.).

```sql
CREATE TABLE providers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,          -- Уникальное имя: "openrouter", "openai"
    type        TEXT NOT NULL,                 -- Тип провайдера: "openrouter", "openai", "anthropic"
    api_key     TEXT NOT NULL,                 -- API ключ (шифрование — этап 2)
    base_url    TEXT,                          -- Базовый URL API (может переопределяться)
    config      TEXT DEFAULT '{}',             -- JSON: дополнительные параметры провайдера
    is_active   INTEGER DEFAULT 1,            -- Включён/выключен
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**Поле `config` (JSON) для разных провайдеров:**

```jsonc
// OpenRouter
{
    "providers_list": ["openai", "anthropic"],  // Приоритетные провайдеры
    "route_dynamic": true,                       // Динамический роутинг
    "transforms": ["middle-out"],                // Трансформации контекста
    "app_title": "BayLang AGI"                  // Заголовок приложения
}

// OpenAI
{
    "organization": "org-xxxxx",                // Организация
    "project": "proj-xxxxx"                     // Проект
}

// Anthropic
{
    "anthropic_version": "2024-01-01",          // Версия API
    "max_tokens_limit": 200000                  // Лимит токенов
}
```

### 3.2 Таблица `models`

Хранит конфигурацию моделей LLM. Каждая модель привязана к провайдеру.

```sql
CREATE TABLE models (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id     INTEGER NOT NULL,            -- FK → providers.id
    model_id        TEXT NOT NULL,               -- ID модели у провайдера: "gpt-4o", "claude-3-opus"
    name            TEXT NOT NULL,               -- Человекочитаемое имя: "GPT-4o"
    description     TEXT,                        -- Описание модели
    max_tokens      INTEGER DEFAULT 4096,        -- Максимум токенов ответа
    context_window  INTEGER DEFAULT 128000,      -- Размер контекстного окна
    temperature     REAL DEFAULT 0.7,            -- Температура по умолчанию
    top_p           REAL DEFAULT 1.0,            -- Top-p sampling
    config          TEXT DEFAULT '{}',           -- JSON: дополнительные параметры модели
    is_active       INTEGER DEFAULT 1,           -- Включена/выключена
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (provider_id) REFERENCES providers(id) ON DELETE CASCADE
);
```

**Поле `config` (JSON) для моделей:**

```jsonc
{
    "supports_streaming": true,     // Поддержка streaming
    "supports_tools": true,         // Поддержка tool calling
    "supports_vision": false,       // Поддержка изображений
    "supports_json_mode": true,     // JSON mode
    "cost_per_1k_input": 0.0025,    // Стоимость за 1K input токенов
    "cost_per_1k_output": 0.01      // Стоимость за 1K output токенов
}
```

### 3.3 Таблица `ai`

Хранит конфигурацию AI-личностей. Каждая личность может использовать несколько моделей (для fallback).

```sql
CREATE TABLE ai (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,         -- Имя личности: "Ассистент", "Переводчик"
    slug            TEXT NOT NULL UNIQUE,         -- URL- Slug: "assistant", "translator"
    soul            TEXT NOT NULL,                -- Системный промпт (system prompt)
    avatar_url      TEXT,                         -- Аватар личности
    temperature     REAL DEFAULT 0.7,             -- Глобальная температура
    max_tokens      INTEGER DEFAULT 4096,         -- Глобальный лимит токенов
    is_default      INTEGER DEFAULT 0,            -- Личность по умолчанию
    is_active       INTEGER DEFAULT 1,            -- Включена/выключена
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### 3.4 Таблица `ai_models` (связь N:M)

Связь «AI → Модели» с приоритетом для fallback.

```sql
CREATE TABLE ai_models (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ai_id       INTEGER NOT NULL,             -- FK → ai.id
    model_id    INTEGER NOT NULL,             -- FK → models.id
    priority    INTEGER NOT NULL DEFAULT 0,   -- Приоритет: 0 = основная, 1 = fallback #1, 2 = fallback #2
    is_active   INTEGER DEFAULT 1,
    FOREIGN KEY (ai_id) REFERENCES ai(id) ON DELETE CASCADE,
    FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE,
    UNIQUE(ai_id, model_id)
);
```

### 3.5 Таблица `ai_roles`

Хранит роли AI. У одной личности может быть несколько ролей.

```sql
CREATE TABLE ai_roles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ai_id       INTEGER NOT NULL,             -- FK → ai.id
    name        TEXT NOT NULL,                -- Название роли: "Консультант", "Кодер"
    slug        TEXT NOT NULL,                -- URL-slug: "consultant", "coder"
    prompt      TEXT NOT NULL,                -- Промпт-инструкция для этой роли
    icon        TEXT,                         -- Иконка роли (emoji или icon name)
    sort_order  INTEGER DEFAULT 0,            -- Порядок отображения
    is_active   INTEGER DEFAULT 1,
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ai_id) REFERENCES ai(id) ON DELETE CASCADE
);
```

### 3.6 ER-диаграмма

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│   providers  │       │    models    │       │      ai      │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ id (PK)      │◄──┐   │ id (PK)      │   ┌──►│ id (PK)      │
│ name         │   │   │ provider_id  │───┘   │ name         │
│ type         │   │   │ model_id     │       │ slug         │
│ api_key      │   └───│ (FK→providers)│      │ soul         │
│ base_url     │       │ name         │       │ temperature  │
│ config       │       │ max_tokens   │       │ max_tokens   │
│ is_active    │       │ temperature  │       │ is_default   │
└──────────────┘       │ context_window│      │ is_active    │
                       │ config       │       └──────┬───────┘
                       │ is_active    │              │
                       └──────────────┘              │
                              ▲                      │
                              │    ┌──────────────┐  │
                              │    │  ai_models   │  │
                              │    ├──────────────┤  │
                              └────│ ai_id (FK)   │──┘
                                   │ model_id(FK) │──►
                                   │ priority     │
                                   └──────────────┘

┌──────────────┐
│   ai_roles   │
├──────────────┤
│ id (PK)      │
│ ai_id (FK)   │──► ai.id
│ name         │
│ slug         │
│ prompt       │
│ icon         │
│ sort_order   │
│ is_active    │
└──────────────┘
```

---

## 4. Классы backend: AI Providers

### 4.1 Базовый класс провайдера

```python
# src/core/ai/providers/BaseProvider.py

import json
import requests
from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """
    Базовый абстрактный класс для всех AI-провайдеров.
    
    Каждый провайдер реализует:
    - send() — отправка запроса к LLM
    - get_models() — получение списка доступных моделей
    - build_headers() — формирование заголовков запроса
    - build_payload() — формирование тела запроса
    """
    
    def __init__(self, provider_row: dict):
        """
        Инициализация провайдера из строки БД.
        
        Args:
            provider_row: Словарь с данными из таблицы providers:
                {
                    "id": 1,
                    "name": "openrouter",
                    "type": "openrouter",
                    "api_key": "sk-or-...",
                    "base_url": "https://openrouter.ai/api/v1",
                    "config": '{"providers_list": ["openai"]}',
                    "is_active": 1
                }
        """
        self.id = provider_row["id"]
        self.name = provider_row["name"]
        self.type = provider_row["type"]
        self.api_key = provider_row["api_key"]
        self.base_url = provider_row.get("base_url", self._default_base_url())
        self.config = json.loads(provider_row.get("config", "{}"))
        self.is_active = bool(provider_row.get("is_active", True))
    
    @abstractmethod
    def _default_base_url(self) -> str:
        """Возвращает URL по умолчанию для провайдера"""
        pass
    
    @abstractmethod
    def build_headers(self) -> dict:
        """Формирование HTTP-заголовков запроса"""
        pass
    
    @abstractmethod
    def build_payload(self, model_id: str, messages: list, **kwargs) -> dict:
        """
        Формирование тела запроса к LLM.
        
        Args:
            model_id: Идентификатор модели у провайдера
            messages: Список сообщений [{"role": "user", "content": "..."}]
            **kwargs: Дополнительные параметры (temperature, max_tokens и т.д.)
        """
        pass
    
    def send(self, model_id: str, messages: list, **kwargs) -> dict:
        """
        Отправка запроса к LLM и получение ответа.
        
        Args:
            model_id: ID модели
            messages: История сообщений
            **kwargs: Доп. параметры (temperature, max_tokens, tools и т.д.)
        
        Returns:
            dict с полями:
                {
                    "content": "Текст ответа",
                    "finish_reason": "stop",
                    "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
                    "tool_calls": [...]  # Опционально
                }
        
        Raises:
            ProviderException: При ошибке API
        """
        if not self.is_active:
            raise ProviderException(f"Провайдер '{self.name}' отключён")
        
        headers = self.build_headers()
        payload = self.build_payload(model_id, messages, **kwargs)
        
        url = self._build_url()
        
        try:
            response = requests.post(
                url,
                headers=headers,
                data=json.dumps(payload),
                timeout=kwargs.get("timeout", 60)
            )
            response.raise_for_status()
            result = response.json()
            
            return self._parse_response(result)
            
        except requests.exceptions.Timeout:
            raise ProviderException(f"Таймаут запроса к провайдеру '{self.name}'")
        except requests.exceptions.ConnectionError:
            raise ProviderException(f"Ошибка соединения с провайдером '{self.name}'")
        except requests.exceptions.HTTPError as e:
            raise ProviderException(
                f"HTTP ошибка провайдера '{self.name}': {e.response.status_code} — {e.response.text}"
            )
    
    def _build_url(self) -> str:
        """Формирование полного URL для запроса"""
        base = self.base_url.rstrip("/")
        return f"{base}/chat/completions"
    
    @abstractmethod
    def _parse_response(self, raw_response: dict) -> dict:
        """Парсинг ответа API в стандартный формат"""
        pass
    
    def send_stream(self, model_id: str, messages: list, **kwargs):
        """
        Streaming-отправка запроса к LLM.
        Возвращает генератор чанков текста.
        """
        if not self.is_active:
            raise ProviderException(f"Провайдер '{self.name}' отключён")
        
        headers = self.build_headers()
        payload = self.build_payload(model_id, messages, stream=True, **kwargs)
        url = self._build_url()
        
        try:
            response = requests.post(
                url,
                headers=headers,
                data=json.dumps(payload),
                stream=True,
                timeout=kwargs.get("timeout", 120)
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            break
                        chunk = json.loads(data)
                        yield self._parse_stream_chunk(chunk)
                        
        except Exception as e:
            raise ProviderException(f"Streaming ошибка провайдера '{self.name}': {str(e)}")
    
    def _parse_stream_chunk(self, chunk: dict) -> str:
        """Парсинг одного чанка streaming-ответа"""
        try:
            delta = chunk["choices"][0]["delta"]
            return delta.get("content", "")
        except (KeyError, IndexError):
            return ""
    
    def __repr__(self):
        return f"<{self.__class__.__name__} name='{self.name}' active={self.is_active}>"


class ProviderException(Exception):
    """Исключение, связанное с провайдером AI"""
    pass
```

### 4.2 Реализация: OpenRouter

```python
# src/core/ai/providers/OpenRouterProvider.py

from .BaseProvider import BaseProvider


class OpenRouterProvider(BaseProvider):
    """
    Провайдер OpenRouter — агрегатор моделей GPT, Claude, Llama и др.
    
    Особенности:
    - Динамический роутинг между провайдерами
    - Приоритетный список провайдеров
    - Поддержка трансформаций контекста
    """
    
    def _default_base_url(self) -> str:
        return "https://openrouter.ai/api/v1"
    
    def build_headers(self) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.config.get("app_url", "https://baylang.agi"),
            "X-Title": self.config.get("app_title", "BayLang Cloud AGI"),
        }
        return headers
    
    def build_payload(self, model_id: str, messages: list, **kwargs) -> dict:
        payload = {
            "model": model_id,
            "messages": messages,
        }
        
        # Опциональные параметры OpenRouter
        if kwargs.get("temperature") is not None:
            payload["temperature"] = kwargs["temperature"]
        if kwargs.get("max_tokens") is not None:
            payload["max_tokens"] = kwargs["max_tokens"]
        if kwargs.get("top_p") is not None:
            payload["top_p"] = kwargs["top_p"]
        if kwargs.get("stream"):
            payload["stream"] = True
        
        # OpenRouter-specific: приоритетные провайдеры
        providers_list = self.config.get("providers_list")
        if providers_list:
            payload["provider"] = {
                "order": providers_list,
                "allow_fallback": self.config.get("allow_fallback", True),
            }
        
        # OpenRouter-specific: динамический роутинг
        if self.config.get("route_dynamic"):
            payload.setdefault("provider", {})["order"] = []
        
        # OpenRouter-specific: трансформации контекста
        transforms = self.config.get("transforms")
        if transforms:
            payload["transforms"] = transforms
        
        # Tool calling
        tools = kwargs.get("tools")
        if tools:
            payload["tools"] = tools
            if kwargs.get("tool_choice"):
                payload["tool_choice"] = kwargs["tool_choice"]
        
        return payload
    
    def _parse_response(self, raw_response: dict) -> dict:
        choice = raw_response["choices"][0]
        
        result = {
            "content": choice["message"].get("content", ""),
            "finish_reason": choice.get("finish_reason", "stop"),
            "usage": raw_response.get("usage", {}),
        }
        
        # Tool calls
        if "tool_calls" in choice["message"]:
            result["tool_calls"] = choice["message"]["tool_calls"]
        
        return result
```

### 4.3 Реализация: OpenAI

```python
# src/core/ai/providers/OpenAIProvider.py

from .BaseProvider import BaseProvider


class OpenAIProvider(BaseProvider):
    """
    Провайдер OpenAI — прямое подключение к API OpenAI.
    
    Особенности:
    - Поддержка organization / project
    - JSON mode
    - Function calling
    """
    
    def _default_base_url(self) -> str:
        return "https://api.openai.com/v1"
    
    def build_headers(self) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        organization = self.config.get("organization")
        if organization:
            headers["OpenAI-Organization"] = organization
        
        project = self.config.get("project")
        if project:
            headers["OpenAI-Project"] = project
        
        return headers
    
    def build_payload(self, model_id: str, messages: list, **kwargs) -> dict:
        payload = {
            "model": model_id,
            "messages": messages,
        }
        
        if kwargs.get("temperature") is not None:
            payload["temperature"] = kwargs["temperature"]
        if kwargs.get("max_tokens") is not None:
            payload["max_tokens"] = kwargs["max_tokens"]
        if kwargs.get("top_p") is not None:
            payload["top_p"] = kwargs["top_p"]
        if kwargs.get("stream"):
            payload["stream"] = True
        
        # JSON mode
        if kwargs.get("response_format"):
            payload["response_format"] = kwargs["response_format"]
        elif self.config.get("supports_json_mode"):
            pass  # Не форсируем, только по запросу
        
        # Tool calling
        tools = kwargs.get("tools")
        if tools:
            payload["tools"] = tools
        
        return payload
    
    def _parse_response(self, raw_response: dict) -> dict:
        choice = raw_response["choices"][0]
        
        result = {
            "content": choice["message"].get("content", ""),
            "finish_reason": choice.get("finish_reason", "stop"),
            "usage": raw_response.get("usage", {}),
        }
        
        if "tool_calls" in choice["message"]:
            result["tool_calls"] = choice["message"]["tool_calls"]
        
        return result
```

### 4.4 Реализация: Anthropic

```python
# src/core/ai/providers/AnthropicProvider.py

import json
from .BaseProvider import BaseProvider, ProviderException


class AnthropicProvider(BaseProvider):
    """
    Провайдер Anthropic — API Claude.
    
    Особенности:
    - Системный промпт передаётся отдельным полем (не в messages)
    - Формат сообщений отличается от OpenAI
    - Максимальный контекст: до 200K токенов
    """
    
    def _default_base_url(self) -> str:
        return "https://api.anthropic.com/v1"
    
    def build_headers(self) -> dict:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": self.config.get("anthropic_version", "2024-01-01"),
            "Content-Type": "application/json",
        }
    
    def build_payload(self, model_id: str, messages: list, **kwargs) -> dict:
        # Anthropic: system промпт — отдельное поле
        system_prompt = kwargs.get("system_prompt", "")
        anthropic_messages = []
        
        for msg in messages:
            role = msg["role"]
            if role == "system":
                # Системные сообщения конвертируем
                system_prompt = msg["content"]
            else:
                anthropic_messages.append({
                    "role": role,
                    "content": msg["content"],
                })
        
        payload = {
            "model": model_id,
            "messages": anthropic_messages,
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        if kwargs.get("temperature") is not None:
            payload["temperature"] = kwargs["temperature"]
        if kwargs.get("top_p") is not None:
            payload["top_p"] = kwargs["top_p"]
        if kwargs.get("stream"):
            payload["stream"] = True
        
        return payload
    
    def _build_url(self) -> str:
        base = self.base_url.rstrip("/")
        return f"{base}/messages"
    
    def _parse_response(self, raw_response: dict) -> dict:
        # Anthropic: другой формат ответа
        content_parts = raw_response.get("content", [])
        text = ""
        for part in content_parts:
            if part.get("type") == "text":
                text += part.get("text", "")
        
        return {
            "content": text,
            "finish_reason": raw_response.get("stop_reason", "end_turn"),
            "usage": raw_response.get("usage", {}),
        }
    
    def _parse_stream_chunk(self, chunk: dict) -> str:
        event_type = chunk.get("type", "")
        
        if event_type == "content_block_delta":
            delta = chunk.get("delta", {})
            return delta.get("text", "")
        
        return ""
```

### 4.5 Фабрика провайдеров

```python
# src/core/ai/providers/ProviderFactory.py

from .BaseProvider import BaseProvider, ProviderException
from .OpenRouterProvider import OpenRouterProvider
from .OpenAIProvider import OpenAIProvider
from .AnthropicProvider import AnthropicProvider


class ProviderFactory:
    """
    Фабрика для создания экземпляров провайдеров по типу.
    
    Пример использования:
        provider = ProviderFactory.create(provider_row)
        result = provider.send("gpt-4o", messages)
    """
    
    # Реестр типов провайдеров
    _registry: dict[str, type[BaseProvider]] = {
        "openrouter": OpenRouterProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
    }
    
    @classmethod
    def create(cls, provider_row: dict) -> BaseProvider:
        """
        Создание экземпляра провайдера из строки БД.
        
        Args:
            provider_row: Словарь с данными провайдера из БД
        
        Returns:
            Экземпляр BaseProvider
        
        Raises:
            ProviderException: Если тип провайдера не зарегистрирован
        """
        provider_type = provider_row.get("type", "")
        
        provider_class = cls._registry.get(provider_type)
        if not provider_class:
            available = ", ".join(cls._registry.keys())
            raise ProviderException(
                f"Неизвестный тип провайдера: '{provider_type}'. "
                f"Доступные типы: {available}"
            )
        
        return provider_class(provider_row)
    
    @classmethod
    def register(cls, provider_type: str, provider_class: type[BaseProvider]):
        """Регистрация нового типа провайдера"""
        cls._registry[provider_type] = provider_class
    
    @classmethod
    def get_supported_types(cls) -> list[str]:
        """Список зарегистрированных типов провайдеров"""
        return list(cls._registry.keys())
```

---

## 5. Классы backend: AI Model, Persona, Role

### 5.1 AIModel — конфигурация модели

```python
# src/core/ai/models/AIModel.py

import json


class AIModel:
    """
    Конфигурация модели LLM.
    
    Хранит параметры генерации (temperature, max_tokens),
    информацию о контекстном окне и дополнительные опции.
    """
    
    def __init__(self, model_row: dict):
        """
        Args:
            model_row: Строка из таблицы models:
                {
                    "id": 1,
                    "provider_id": 1,
                    "model_id": "gpt-4o",
                    "name": "GPT-4o",
                    "description": "Самая умная модель OpenAI",
                    "max_tokens": 4096,
                    "context_window": 128000,
                    "temperature": 0.7,
                    "top_p": 1.0,
                    "config": '{"supports_streaming": true}',
                    "is_active": 1
                }
        """
        self.id = model_row["id"]
        self.provider_id = model_row["provider_id"]
        self.model_id = model_row["model_id"]          # "gpt-4o"
        self.name = model_row["name"]                  # "GPT-4o"
        self.description = model_row.get("description", "")
        self.max_tokens = model_row.get("max_tokens", 4096)
        self.context_window = model_row.get("context_window", 128000)
        self.temperature = model_row.get("temperature", 0.7)
        self.top_p = model_row.get("top_p", 1.0)
        self.config = json.loads(model_row.get("config", "{}"))
        self.is_active = bool(model_row.get("is_active", True))
    
    def to_dict(self) -> dict:
        """Сериализация в словарь"""
        return {
            "id": self.id,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "name": self.name,
            "description": self.description,
            "max_tokens": self.max_tokens,
            "context_window": self.context_window,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "config": self.config,
            "is_active": self.is_active,
        }
    
    def supports_streaming(self) -> bool:
        return self.config.get("supports_streaming", True)
    
    def supports_tools(self) -> bool:
        return self.config.get("supports_tools", False)
    
    def supports_vision(self) -> bool:
        return self.config.get("supports_vision", False)
```

### 5.2 AIPersona — личность ИИ

```python
# src/core/ai/personas/AIPersona.py

import json


class AIPersona:
    """
    Личность AI — хранит системный промпт (soul) и глобальные настройки.
    
    Каждая личность может иметь несколько моделей (с fallback)
    и несколько ролей (например: «переводчик», «аналитик», «кодер»).
    """
    
    def __init__(self, ai_row: dict):
        self.id = ai_row["id"]
        self.name = ai_row["name"]
        self.slug = ai_row["slug"]
        self.soul = ai_row["soul"]                    # Системный промпт
        self.avatar_url = ai_row.get("avatar_url")
        self.temperature = ai_row.get("temperature", 0.7)
        self.max_tokens = ai_row.get("max_tokens", 4096)
        self.is_default = bool(ai_row.get("is_default", False))
        self.is_active = bool(ai_row.get("is_active", True))
        
        # Связанные данные (загружаются отдельно)
        self.models = []    # Список AIModel с приоритетами
        self.roles = []     # Список AIRole
    
    def get_system_messages(self, role_slug: str = None) -> list[dict]:
        """
        Формирование системных сообщений для запроса к LLM.
        
        Args:
            role_slug: Если указана роль — добавляет её промпт к soul
        
        Returns:
            Список сообщений [{"role": "system", "content": "..."}]
        """
        content = self.soul
        
        # Добавляем роль, если указана
        if role_slug:
            for role in self.roles:
                if role.slug == role_slug:
                    content += f"\n\n---\nРоль: {role.name}\nИнструкция: {role.prompt}"
                    break
        
        return [{"role": "system", "content": content}]
    
    def get_active_model(self) -> "AIModel | None":
        """Получение основной активной модели (priority = 0)"""
        for model in sorted(self.models, key=lambda m: m.priority):
            if model.is_active:
                return model
        return None
    
    def get_fallback_models(self) -> list:
        """Получение моделей для fallback (priority > 0)"""
        return [
            m for m in sorted(self.models, key=lambda m: m.priority)
            if m.priority > 0 and m.is_active
        ]
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "soul": self.soul,
            "avatar_url": self.avatar_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "is_default": self.is_default,
            "is_active": self.is_active,
            "models": [m.to_dict() for m in self.models],
            "roles": [r.to_dict() for r in self.roles],
        }
```

### 5.3 AIRole — роль AI

```python
# src/core/ai/roles/AIRole.py


class AIRole:
    """
    Роль AI — специализация личности.
    
    Примеры:
    - «Консультант» — помогает с вопросами
    - «Переводчик» — переводит тексты
    - «Кодер» — помогает с программированием
    - «Аналитик» — анализирует данные
    """
    
    def __init__(self, role_row: dict):
        self.id = role_row["id"]
        self.ai_id = role_row["ai_id"]
        self.name = role_row["name"]
        self.slug = role_row["slug"]
        self.prompt = role_row["prompt"]             # Инструкция для роли
        self.icon = role_row.get("icon")             # Emoji или icon name
        self.sort_order = role_row.get("sort_order", 0)
        self.is_active = bool(role_row.get("is_active", True))
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ai_id": self.ai_id,
            "name": self.name,
            "slug": self.slug,
            "prompt": self.prompt,
            "icon": self.icon,
            "sort_order": self.sort_order,
            "is_active": self.is_active,
        }
```

---

## 6. AIService — фасад

```python
# src/core/ai/AIService.py

from core.database.repositories.ProviderRepository import ProviderRepository
from core.database.repositories.ModelRepository import ModelRepository
from core.database.repositories.AIRepository import AIRepository
from core.database.repositories.AIRoleRepository import AIRoleRepository

from core.ai.providers.ProviderFactory import ProviderException
from core.ai.providers.ProviderFactory import ProviderFactory
from core.ai.messages.Message import Message
from core.ai.context.ConversationContext import ConversationContext


class AIService:
    """
    Основной сервис AI — фасад для всех операций.
    
    Связывает:
    - Репозитории (доступ к БД)
    - Провайдеры (отправка запросов)
    - Личности и модели (конфигурация)
    - Контекст (история диалога)
    
    Пример использования:
        ai_service = container.get("ai_service")
        response = ai_service.chat(
            ai_slug="assistant",
            user_message="Привет!",
            session_id="abc123"
        )
    """
    
    def __init__(self, provider_repo: ProviderRepository, model_repo: ModelRepository,
                 ai_repo: AIRepository, role_repo: AIRoleRepository):
        self.provider_repo = provider_repo
        self.model_repo = model_repo
        self.ai_repo = ai_repo
        self.role_repo = role_repo
        
        # Кэш провайдеров: provider_id -> BaseProvider
        self._providers_cache: dict[int, object] = {}
        
        # Кэш контекстов: session_id -> ConversationContext
        self._contexts: dict[str, ConversationContext] = {}
    
    # ─── Провайдеры ──────────────────────────────────────
    
    def get_provider(self, provider_id: int):
        """Получение экземпляра провайдера (с кэшированием)"""
        if provider_id not in self._providers_cache:
            row = self.provider_repo.find_by_id(provider_id)
            if not row:
                raise ValueError(f"Провайдер с id={provider_id} не найден")
            self._providers_cache[provider_id] = ProviderFactory.create(row)
        
        return self._providers_cache[provider_id]
    
    def invalidate_provider_cache(self, provider_id: int):
        """Очистка кэша провайдера (при изменении конфигурации)"""
        self._providers_cache.pop(provider_id, None)
    
    # ─── Чат ──────────────────────────────────────────────
    
    def chat(self, ai_slug: str, user_message: str, session_id: str = "default",
             role_slug: str = None, **kwargs) -> dict:
        """
        Отправка сообщения AI и получение ответа.
        
        Args:
            ai_slug: Slug AI-личности
            user_message: Текст сообщения пользователя
            session_id: ID сессии (для хранения контекста)
            role_slug: Опциональная роль
            **kwargs: Доп. параметры
        
        Returns:
            {
                "content": "Ответ AI",
                "model_used": "gpt-4o",
                "provider_used": "openrouter",
                "usage": {...}
            }
        """
        # 1. Загружаем AI-личность
        ai = self.ai_repo.find_by_slug_with_models_and_roles(ai_slug)
        if not ai:
            raise ValueError(f"AI-личность '{ai_slug}' не найдена")
        
        # 2. Выбираем модель (основная + fallback)
        model_info = self._select_model(ai)
        if not model_info:
            raise ValueError(f"Нет доступных моделей для AI '{ai_slug}'")
        
        model, provider = model_info
        
        # 3. Формируем системные сообщения
        system_messages = ai.get_system_messages(role_slug)
        
        # 4. Получаем/создаём контекст
        context = self._get_context(session_id)
        context.set_system(system_messages)
        context.add_message(Message.role_user(user_message))
        
        # 5. Отправляем запрос
        messages = context.get_messages()
        kwargs.setdefault("temperature", ai.temperature)
        kwargs.setdefault("max_tokens", ai.max_tokens)
        
        try:
            result = provider.send(model.model_id, messages, **kwargs)
        except ProviderException as e:
            # Fallback на следующую модель
            result = self._try_fallback(ai, messages, model.id, str(e), **kwargs)
        
        # 6. Сохраняем ответ в контекст
        context.add_message(Message.role_ai(result["content"]))
        
        return {
            "content": result["content"],
            "model_used": model.model_id,
            "provider_used": provider.name,
            "usage": result.get("usage", {}),
        }
    
    def _select_model(self, ai):
        """Выбор модели: основная, с учётом fallback"""
        primary = ai.get_active_model()
        if not primary:
            return None
        
        provider = self.get_provider(primary.provider_id)
        return primary, provider
    
    def _try_fallback(self, ai, messages, failed_model_id, error_msg, **kwargs):
        """Попытка использовать модель fallback"""
        fallback_models = ai.get_fallback_models()
        
        for fallback in fallback_models:
            if fallback.id == failed_model_id:
                continue  # Пропускаем уже сломанную модель
            
            try:
                provider = self.get_provider(fallback.provider_id)
                result = provider.send(fallback.model_id, messages, **kwargs)
                return result
            except ProviderException:
                continue
        
        raise ProviderException(
            f"Все модели для AI исчерпаны. Последняя ошибка: {error_msg}"
        )
    
    # ─── Контекст ─────────────────────────────────────────
    
    def _get_context(self, session_id: str) -> ConversationContext:
        if session_id not in self._contexts:
            self._contexts[session_id] = ConversationContext()
        return self._contexts[session_id]
    
    def clear_context(self, session_id: str):
        """Очистка контекста сессии"""
        self._contexts.pop(session_id, None)
```

---

## 7. Репозитории (DAO)

### 7.1 Базовый репозиторий

```python
# src/core/database/repositories/BaseRepository.py

from abc import ABC, abstractmethod


class BaseRepository(ABC):
    """Базовый класс репозитория для работы с БД"""
    
    def __init__(self, db):
        self.db = db
    
    @abstractmethod
    def find_by_id(self, id: int) -> dict | None:
        pass
    
    @abstractmethod
    def find_all(self) -> list[dict]:
        pass
    
    @abstractmethod
    def create(self, data: dict) -> int:
        """Возвращает ID созданной записи"""
        pass
    
    @abstractmethod
    def update(self, id: int, data: dict) -> bool:
        pass
    
    @abstractmethod
    def delete(self, id: int) -> bool:
        pass
```

### 7.2 ProviderRepository

```python
# src/core/database/repositories/ProviderRepository.py

from .BaseRepository import BaseRepository


class ProviderRepository(BaseRepository):
    
    def find_by_id(self, id: int) -> dict | None:
        row = self.db.execute("SELECT * FROM providers WHERE id = ?", [id])
        return row.fetchone() if row else None
    
    def find_by_name(self, name: str) -> dict | None:
        row = self.db.execute("SELECT * FROM providers WHERE name = ?", [name])
        return row.fetchone() if row else None
    
    def find_all(self) -> list[dict]:
        rows = self.db.execute("SELECT * FROM providers ORDER BY name")
        return rows.fetchall() if rows else []
    
    def find_active(self) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM providers WHERE is_active = 1 ORDER BY name"
        )
        return rows.fetchall() if rows else []
    
    def create(self, data: dict) -> int:
        cursor = self.db.execute(
            """INSERT INTO providers (name, type, api_key, base_url, config, is_active)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [
                data["name"], data["type"], data["api_key"],
                data.get("base_url", ""), data.get("config", "{}"),
                data.get("is_active", 1)
            ]
        )
        return cursor.lastrowid
    
    def update(self, id: int, data: dict) -> bool:
        fields = []
        values = []
        
        for key in ["name", "type", "api_key", "base_url", "config", "is_active"]:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])
        
        if not fields:
            return False
        
        fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(id)
        
        self.db.execute(
            f"UPDATE providers SET {', '.join(fields)} WHERE id = ?",
            values
        )
        return True
    
    def delete(self, id: int) -> bool:
        self.db.execute("DELETE FROM providers WHERE id = ?", [id])
        return True
```

---

## 8. Миграции

### 8.1 Базовый класс миграции

```python
# src/core/database/migrations/Migration.py

from abc import ABC, abstractmethod


class Migration(ABC):
    
    @abstractmethod
    def get_name(self) -> str:
        pass
    
    @abstractmethod
    async def up(self, db):
        pass
    
    @abstractmethod
    async def down(self, db):
        pass
```

### 8.2 Миграция: Providers + Models + AI + Roles

```python
# src/core/database/migrations/Migration_001_AI_Tables.py

from .Migration import Migration


class Migration_001_Providers(Migration):
    
    def get_name(self) -> str:
        return "001_create_providers_table"
    
    async def up(self, db):
        await db.execute("""
            CREATE TABLE IF NOT EXISTS providers (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL UNIQUE,
                type        TEXT NOT NULL,
                api_key     TEXT NOT NULL,
                base_url    TEXT,
                config      TEXT DEFAULT '{}',
                is_active   INTEGER DEFAULT 1,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Провайдер по умолчанию
        await db.execute("""
            INSERT OR IGNORE INTO providers (name, type, api_key, base_url, config)
            VALUES (
                'openrouter',
                'openrouter',
                'YOUR_API_KEY_HERE',
                'https://openrouter.ai/api/v1',
                '{}'
            )
        """)
    
    async def down(self, db):
        await db.execute("DROP TABLE IF EXISTS providers")


class Migration_002_Models(Migration):
    
    def get_name(self) -> str:
        return "002_create_models_table"
    
    async def up(self, db):
        await db.execute("""
            CREATE TABLE IF NOT EXISTS models (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_id     INTEGER NOT NULL,
                model_id        TEXT NOT NULL,
                name            TEXT NOT NULL,
                description     TEXT,
                max_tokens      INTEGER DEFAULT 4096,
                context_window  INTEGER DEFAULT 128000,
                temperature     REAL DEFAULT 0.7,
                top_p           REAL DEFAULT 1.0,
                config          TEXT DEFAULT '{}',
                is_active       INTEGER DEFAULT 1,
                created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at      TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (provider_id) REFERENCES providers(id) ON DELETE CASCADE
            )
        """)
        
        # Модели по умолчанию
        await db.execute("""
            INSERT OR IGNORE INTO models (provider_id, model_id, name, description, max_tokens, context_window, config)
            VALUES
                (1, 'openai/gpt-4o', 'GPT-4o', 'Лучшая модель OpenAI', 4096, 128000,
                 '{"supports_streaming": true, "supports_tools": true, "supports_vision": true}'),
                (1, 'anthropic/claude-3.5-sonnet', 'Claude 3.5 Sonnet', 'Быстрая модель Anthropic', 4096, 200000,
                 '{"supports_streaming": true, "supports_tools": true}'),
                (1, 'meta-llama/llama-3.1-405b-instruct', 'Llama 3.1 405B', 'Open-source модель', 4096, 128000,
                 '{"supports_streaming": true, "supports_tools": true}')
        """)
    
    async def down(self, db):
        await db.execute("DROP TABLE IF EXISTS models")


class Migration_003_AI(Migration):
    
    def get_name(self) -> str:
        return "003_create_ai_and_ai_models_tables"
    
    async def up(self, db):
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ai (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL UNIQUE,
                slug            TEXT NOT NULL UNIQUE,
                soul            TEXT NOT NULL,
                avatar_url      TEXT,
                temperature     REAL DEFAULT 0.7,
                max_tokens      INTEGER DEFAULT 4096,
                is_default      INTEGER DEFAULT 0,
                is_active       INTEGER DEFAULT 1,
                created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at      TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ai_models (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ai_id       INTEGER NOT NULL,
                model_id    INTEGER NOT NULL,
                priority    INTEGER NOT NULL DEFAULT 0,
                is_active   INTEGER DEFAULT 1,
                FOREIGN KEY (ai_id) REFERENCES ai(id) ON DELETE CASCADE,
                FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE,
                UNIQUE(ai_id, model_id)
            )
        """)
        
        # AI по умолчанию
        await db.execute("""
            INSERT OR IGNORE INTO ai (name, slug, soul, is_default)
            VALUES (
                'Ассистент',
                'assistant',
                'Ты — умный и полезный AI-ассистент. Ты отвечаешь на русском языке, помогаешь с задачами и даёшь развёрнутые ответы.',
                1
            )
        """)
        
        # Привязка моделей к AI (GPT-4o основная, Claude fallback)
        await db.execute("""
            INSERT OR IGNORE INTO ai_models (ai_id, model_id, priority)
            VALUES (1, 1, 0), (1, 2, 1)
        """)
    
    async def down(self, db):
        await db.execute("DROP TABLE IF EXISTS ai_models")
        await db.execute("DROP TABLE IF EXISTS ai")


class Migration_004_AIRoles(Migration):
    
    def get_name(self) -> str:
        return "004_create_ai_roles_table"
    
    async def up(self, db):
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ai_roles (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ai_id       INTEGER NOT NULL,
                name        TEXT NOT NULL,
                slug        TEXT NOT NULL,
                prompt      TEXT NOT NULL,
                icon        TEXT,
                sort_order  INTEGER DEFAULT 0,
                is_active   INTEGER DEFAULT 1,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ai_id) REFERENCES ai(id) ON DELETE CASCADE
            )
        """)
        
        # Роли по умолчанию для Ассистента
        await db.execute("""
            INSERT OR IGNORE INTO ai_roles (ai_id, name, slug, prompt, icon, sort_order)
            VALUES
                (1, 'Консультант', 'consultant',
                 'Ты выступаешь в роли консультанта. Задавай уточняющие вопросы, помогай формулировать задачу.',
                 '💬', 0),
                (1, 'Переводчик', 'translator',
                 'Ты выступаешь в роли переводчика. Переводи тексты на указанный язык, сохраняя смысл и стиль.',
                 '🌐', 1),
                (1, 'Кодер', 'coder',
                 'Ты выступаешь в роли программиста. Помогай с кодом, объясняй алгоритмы, находи ошибки.',
                 '💻', 2)
        """)
    
    async def down(self, db):
        await db.execute("DROP TABLE IF EXISTS ai_roles")
```

---

## 9. API эндпоинты

### 9.1 AI Routes — провайдеры

```python
# src/core/api/ai_routes.py

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from core.app import get_container

router = APIRouter(prefix="/api/ai/providers", tags=["AI Providers"])


class ProviderCreateRequest(BaseModel):
    name: str
    type: str           # "openrouter" | "openai" | "anthropic"
    api_key: str
    base_url: Optional[str] = None
    config: Optional[str] = "{}"
    is_active: Optional[bool] = True


class ProviderUpdateRequest(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    config: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/")
def list_providers():
    """Получить список всех провайдеров"""
    container = get_container()
    repo = container.get("provider_repository")
    providers = repo.find_all()
    
    # Маскируем API ключи
    for p in providers:
        if p.get("api_key"):
            key = p["api_key"]
            p["api_key_masked"] = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
            del p["api_key"]
    
    return {"providers": providers}


@router.get("/{provider_id}")
def get_provider(provider_id: int):
    """Получить провайдера по ID"""
    container = get_container()
    repo = container.get("provider_repository")
    provider = repo.find_by_id(provider_id)
    
    if not provider:
        raise HTTPException(status_code=404, detail="Провайдер не найден")
    
    if provider.get("api_key"):
        key = provider["api_key"]
        provider["api_key_masked"] = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
        del provider["api_key"]
    
    return {"provider": provider}


@router.post("/")
def create_provider(request: ProviderCreateRequest):
    """Создать нового провайдера"""
    container = get_container()
    repo = container.get("provider_repository")
    
    # Проверка уникальности имени
    existing = repo.find_by_name(request.name)
    if existing:
        raise HTTPException(status_code=400, detail="Провайдер с таким именем уже существует")
    
    provider_id = repo.create(request.model_dump())
    return {"id": provider_id, "message": "Провайдер создан"}


@router.put("/{provider_id}")
def update_provider(provider_id: int, request: ProviderUpdateRequest):
    """Обновить провайдера"""
    container = get_container()
    repo = container.get("provider_repository")
    ai_service = container.get("ai_service")
    
    existing = repo.find_by_id(provider_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Провайдер не найден")
    
    data = {k: v for k, v in request.model_dump().items() if v is not None}
    repo.update(provider_id, data)
    
    # Очищаем кэш
    ai_service.invalidate_provider_cache(provider_id)
    
    return {"message": "Провайдер обновлён"}


@router.delete("/{provider_id}")
def delete_provider(provider_id: int):
    """Удалить провайдера"""
    container = get_container()
    repo = container.get("provider_repository")
    
    existing = repo.find_by_id(provider_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Провайдер не найден")
    
    repo.delete(provider_id)
    return {"message": "Провайдер удалён"}


@router.get("/types/supported")
def get_supported_types():
    """Получить список поддерживаемых типов провайдеров"""
    from core.ai.providers.ProviderFactory import ProviderFactory
    return {"types": ProviderFactory.get_supported_types()}
```

### 9.2 Models Routes

```python
# src/core/api/models_routes.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.app import get_container

router = APIRouter(prefix="/api/ai/models", tags=["AI Models"])


class ModelCreateRequest(BaseModel):
    provider_id: int
    model_id: str
    name: str
    description: Optional[str] = ""
    max_tokens: Optional[int] = 4096
    context_window: Optional[int] = 128000
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    config: Optional[str] = "{}"
    is_active: Optional[bool] = True


class ModelUpdateRequest(BaseModel):
    provider_id: Optional[int] = None
    model_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    max_tokens: Optional[int] = None
    context_window: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    config: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/")
def list_models():
    """Получить все модели"""
    container = get_container()
    repo = container.get("model_repository")
    models = repo.find_all()
    return {"models": models}


@router.get("/{model_id}")
def get_model(model_id: int):
    """Получить модель по ID"""
    container = get_container()
    repo = container.get("model_repository")
    model = repo.find_by_id(model_id)
    
    if not model:
        raise HTTPException(status_code=404, detail="Модель не найдена")
    
    return {"model": model}


@router.post("/")
def create_model(request: ModelCreateRequest):
    """Создать новую модель"""
    container = get_container()
    repo = container.get("model_repository")
    
    model_db_id = repo.create(request.model_dump())
    return {"id": model_db_id, "message": "Модель создана"}


@router.put("/{model_id}")
def update_model(model_id: int, request: ModelUpdateRequest):
    """Обновить модель"""
    container = get_container()
    repo = container.get("model_repository")
    
    existing = repo.find_by_id(model_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Модель не найдена")
    
    data = {k: v for k, v in request.model_dump().items() if v is not None}
    repo.update(model_id, data)
    
    return {"message": "Модель обновлена"}


@router.delete("/{model_id}")
def delete_model(model_id: int):
    """Удалить модель"""
    container = get_container()
    repo = container.get("model_repository")
    
    existing = repo.find_by_id(model_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Модель не найдена")
    
    repo.delete(model_id)
    return {"message": "Модель удалена"}
```

### 9.3 AI Persona + Roles Routes

```python
# src/core/api/personas_routes.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.app import get_container

router = APIRouter(prefix="/api/ai/personas", tags=["AI Personas"])


class PersonaCreateRequest(BaseModel):
    name: str
    slug: str
    soul: str
    avatar_url: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 4096
    is_default: Optional[bool] = False
    is_active: Optional[bool] = True


class PersonaUpdateRequest(BaseModel):
    name: Optional[str] = None
    soul: Optional[str] = None
    avatar_url: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class RoleCreateRequest(BaseModel):
    name: str
    slug: str
    prompt: str
    icon: Optional[str] = None
    sort_order: Optional[int] = 0


class AssignModelRequest(BaseModel):
    model_id: int
    priority: int = 0  # 0 = основная, 1+ = fallback


@router.get("/")
def list_personas():
    """Получить список всех AI-личностей"""
    container = get_container()
    repo = container.get("ai_repository")
    personas = repo.find_all_with_models_and_roles()
    return {"personas": [p.to_dict() for p in personas]}


@router.get("/{slug}")
def get_persona(slug: str):
    """Получить AI-личность по slug"""
    container = get_container()
    repo = container.get("ai_repository")
    persona = repo.find_by_slug_with_models_and_roles(slug)
    
    if not persona:
        raise HTTPException(status_code=404, detail="AI-личность не найдена")
    
    return {"persona": persona.to_dict()}


@router.post("/")
def create_persona(request: PersonaCreateRequest):
    """Создать новую AI-личность"""
    container = get_container()
    repo = container.get("ai_repository")
    
    persona_id = repo.create(request.model_dump())
    return {"id": persona_id, "message": "AI-личность создана"}


@router.put("/{persona_id}")
def update_persona(persona_id: int, request: PersonaUpdateRequest):
    """Обновить AI-личность"""
    container = get_container()
    repo = container.get("ai_repository")
    
    existing = repo.find_by_id(persona_id)
    if not existing:
        raise HTTPException(status_code=404, detail="AI-личность не найдена")
    
    data = {k: v for k, v in request.model_dump().items() if v is not None}
    repo.update(persona_id, data)
    
    return {"message": "AI-личность обновлена"}


@router.delete("/{persona_id}")
def delete_persona(persona_id: int):
    """Удалить AI-личность"""
    container = get_container()
    repo = container.get("ai_repository")
    repo.delete(persona_id)
    return {"message": "AI-личность удалена"}


# ─── Модели AI ───────────────────────────────────────────

@router.post("/{persona_id}/models")
def assign_model(persona_id: int, request: AssignModelRequest):
    """Привязать модель к AI-личности"""
    container = get_container()
    repo = container.get("ai_repository")
    repo.assign_model(persona_id, request.model_id, request.priority)
    return {"message": "Модель привязана"}


@router.delete("/{persona_id}/models/{model_id}")
def unassign_model(persona_id: int, model_id: int):
    """Отвязать модель от AI-личности"""
    container = get_container()
    repo = container.get("ai_repository")
    repo.unassign_model(persona_id, model_id)
    return {"message": "Модель отвязана"}


# ─── Роли AI ─────────────────────────────────────────────

@router.post("/{persona_id}/roles")
def create_role(persona_id: int, request: RoleCreateRequest):
    """Создать роль для AI-личности"""
    container = get_container()
    repo = container.get("ai_role_repository")
    
    data = request.model_dump()
    data["ai_id"] = persona_id
    
    role_id = repo.create(data)
    return {"id": role_id, "message": "Роль создана"}


@router.put("/{persona_id}/roles/{role_id}")
def update_role(persona_id: int, role_id: int, request: RoleCreateRequest):
    """Обновить роль"""
    container = get_container()
    repo = container.get("ai_role_repository")
    
    data = request.model_dump()
    repo.update(role_id, data)
    
    return {"message": "Роль обновлена"}


@router.delete("/{persona_id}/roles/{role_id}")
def delete_role(persona_id: int, role_id: int):
    """Удалить роль"""
    container = get_container()
    repo = container.get("ai_role_repository")
    repo.delete(role_id)
    return {"message": "Роль удалена"}
```

### 9.4 Chat Route

```python
# src/core/api/chat_routes.py

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from core.app import get_container

router = APIRouter(prefix="/api/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    message: str
    ai_slug: str = "assistant"
    role_slug: Optional[str] = None
    session_id: str = "default"
    stream: bool = False


@router.post("/send")
def send_message(request: ChatRequest):
    """Отправить сообщение AI и получить ответ"""
    container = get_container()
    ai_service = container.get("ai_service")
    
    try:
        result = ai_service.chat(
            ai_slug=request.ai_slug,
            user_message=request.message,
            session_id=request.session_id,
            role_slug=request.role_slug,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка AI: {str(e)}")


@router.post("/stream")
def stream_message(request: ChatRequest):
    """Streaming ответ AI через SSE"""
    container = get_container()
    ai_service = container.get("ai_service")
    
    def generate():
        try:
            ai = ai_service.ai_repo.find_by_slug_with_models_and_roles(request.ai_slug)
            if not ai:
                yield f"data: {{'error': 'AI not found'}}\n\n"
                return
            
            model = ai.get_active_model()
            provider = ai_service.get_provider(model.provider_id)
            
            system = ai.get_system_messages(request.role_slug)
            context = ai_service._get_context(request.session_id)
            context.set_system(system)
            context.add_message({"role": "user", "content": request.message})
            
            for chunk in provider.send_stream(model.model_id, context.get_messages()):
                if chunk:
                    yield f"data: {{'content': '{chunk}'}}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            yield f"data: {{'error': '{str(e)}'}}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@router.delete("/session/{session_id}")
def clear_session(session_id: str):
    """Очистить контекст сессии"""
    container = get_container()
    ai_service = container.get("ai_service")
    ai_service.clear_context(session_id)
    return {"message": "Сессия очищена"}
```

---

## 10. Регистрация в DI Container

### 10.1 Обновлённый `app.py`

```python
# src/core/app.py (обновлённый)

import jinja2
from fastapi import FastAPI
from core.container import Container
from core.config import Config, CloudflareConfig


def register_container():
    container = Container()
    
    # ─── Базовые ──────────────────────────────────
    container.singleton("app", lambda c: FastAPI())
    container.singleton("template", lambda c: jinja2.Environment())
    container.singleton("config", lambda c: Config())
    
    # ─── БД ───────────────────────────────────────
    container.singleton("database", lambda c: create_database(c))
    
    # ─── Репозитории ───────────────────────────────
    container.singleton("provider_repository", lambda c:
        ProviderRepository(c.get("database")))
    container.singleton("model_repository", lambda c:
        ModelRepository(c.get("database")))
    container.singleton("ai_repository", lambda c:
        AIRepository(c.get("database")))
    container.singleton("ai_role_repository", lambda c:
        AIRoleRepository(c.get("database")))
    
    # ─── AI Services ────────────────────────────────
    container.singleton("ai_service", lambda c: AIService(
        provider_repo=c.get("provider_repository"),
        model_repo=c.get("model_repository"),
        ai_repo=c.get("ai_repository"),
        role_repo=c.get("ai_role_repository"),
    ))
    
    # ─── MCP ────────────────────────────────────────
    container.singleton("mcp_manager", lambda c: MCPManager())
    
    return container


def create_database(container):
    """Создание экземпляра БД (SQLite для dev, D1 для prod)"""
    from core.database.Database import SQLiteDatabase
    config = container.get("config")
    db_path = config.get("DATABASE_PATH") or "data/baylang.db"
    return SQLiteDatabase(db_path)


# Импорты
from core.database.repositories.ProviderRepository import ProviderRepository
from core.database.repositories.ModelRepository import ModelRepository
from core.database.repositories.AIRepository import AIRepository
from core.database.repositories.AIRoleRepository import AIRoleRepository
from core.ai.AIService import AIService
from core.ai.mcp.MCPManager import MCPManager


container = register_container()
app = container.get("app")


def get_container():
    return container

def get_app():
    return app

def get_config():
    return container.get("config")


def register_routes():
    from core.routes import router
    from core.api.ai_routes import router as ai_router
    from core.api.models_routes import router as models_router
    from core.api.personas_routes import router as personas_router
    from core.api.chat_routes import router as chat_router
    
    app.include_router(router)
    app.include_router(ai_router)
    app.include_router(models_router)
    app.include_router(personas_router)
    app.include_router(chat_router)


def register_frontend():
    app.mount("/", directory="dist", name="frontend")


def create_app():
    register_routes()
    return app
```

---

## 11. Frontend: страницы администрирования AI

### 11.1 API сервис

```javascript
// src/services/AIApi.js

import { BaseApi } from "./BaseApi";

export class AIApi extends BaseApi {

    // ─── Провайдеры ──────────────────────────────────

    async getProviders() {
        return this.request("GET", "/api/ai/providers");
    }

    async getProvider(id) {
        return this.request("GET", `/api/ai/providers/${id}`);
    }

    async createProvider(data) {
        return this.request("POST", "/api/ai/providers", data);
    }

    async updateProvider(id, data) {
        return this.request("PUT", `/api/ai/providers/${id}`, data);
    }

    async deleteProvider(id) {
        return this.request("DELETE", `/api/ai/providers/${id}`);
    }

    async getSupportedProviderTypes() {
        return this.request("GET", "/api/ai/providers/types/supported");
    }

    // ─── Модели ───────────────────────────────────────

    async getModels() {
        return this.request("GET", "/api/ai/models");
    }

    async getModel(id) {
        return this.request("GET", `/api/ai/models/${id}`);
    }

    async createModel(data) {
        return this.request("POST", "/api/ai/models", data);
    }

    async updateModel(id, data) {
        return this.request("PUT", `/api/ai/models/${id}`, data);
    }

    async deleteModel(id) {
        return this.request("DELETE", `/api/ai/models/${id}`);
    }

    // ─── AI Личности ──────────────────────────────────

    async getPersonas() {
        return this.request("GET", "/api/ai/personas");
    }

    async getPersona(slug) {
        return this.request("GET", `/api/ai/personas/${slug}`);
    }

    async createPersona(data) {
        return this.request("POST", "/api/ai/personas", data);
    }

    async updatePersona(id, data) {
        return this.request("PUT", `/api/ai/personas/${id}`, data);
    }

    async deletePersona(id) {
        return this.request("DELETE", `/api/ai/personas/${id}`);
    }

    // ─── Модели AI ────────────────────────────────────

    async assignModelToPersona(personaId, data) {
        return this.request("POST", `/api/ai/personas/${personaId}/models`, data);
    }

    async unassignModelFromPersona(personaId, modelId) {
        return this.request("DELETE", `/api/ai/personas/${personaId}/models/${modelId}`);
    }

    // ─── Роли AI ──────────────────────────────────────

    async createRole(personaId, data) {
        return this.request("POST", `/api/ai/personas/${personaId}/roles`, data);
    }

    async updateRole(personaId, roleId, data) {
        return this.request("PUT", `/api/ai/personas/${personaId}/roles/${roleId}`, data);
    }

    async deleteRole(personaId, roleId) {
        return this.request("DELETE", `/api/ai/personas/${personaId}/roles/${roleId}`);
    }

    // ─── Чат ──────────────────────────────────────────

    async sendMessage(data) {
        return this.request("POST", "/api/chat/send", data);
    }

    async clearSession(sessionId) {
        return this.request("DELETE", `/api/chat/session/${sessionId}`);
    }
}
```

### 11.2 Модель: AI Admin Page

```javascript
// src/core/pages/ai/AIAdminPageModel.js

import { BaseModel } from "@/models/BaseModel";
import { AIApi } from "@/services/AIApi";

export class AIAdminPageModel extends BaseModel {
    
    constructor() {
        super();
        this.api = new AIApi();
        
        // Данные
        this.providers = [];
        this.models = [];
        this.personas = [];
        this.supportedTypes = [];
        
        // Состояние UI
        this.activeTab = "providers";    // "providers" | "models" | "personas"
        this.loading = false;
        this.error = null;
        
        // Формы
        this.showProviderForm = false;
        this.showModelForm = false;
        this.showPersonaForm = false;
        
        this.editingProvider = null;
        this.editingModel = null;
        this.editingPersona = null;
    }
    
    getPageTitle() {
        return "AI Administration";
    }
    
    async init() {
        this.loading = true;
        try {
            await Promise.all([
                this.loadProviders(),
                this.loadModels(),
                this.loadPersonas(),
                this.loadSupportedTypes(),
            ]);
        } catch (e) {
            this.error = e.message;
        } finally {
            this.loading = false;
        }
    }
    
    // ─── Providers ──────────────────────────────────
    
    async loadProviders() {
        const response = await this.api.getProviders();
        if (response.isSuccess()) {
            this.providers = response.data.providers;
        }
    }
    
    async saveProvider(providerData) {
        try {
            if (this.editingProvider) {
                await this.api.updateProvider(this.editingProvider.id, providerData);
            } else {
                await this.api.createProvider(providerData);
            }
            this.showProviderForm = false;
            this.editingProvider = null;
            await this.loadProviders();
        } catch (e) {
            this.error = e.message;
        }
    }
    
    async deleteProvider(id) {
        if (!confirm("Delete this provider?")) return;
        await this.api.deleteProvider(id);
        await this.loadProviders();
    }
    
    editProvider(provider) {
        this.editingProvider = { ...provider };
        this.showProviderForm = true;
    }
    
    // ─── Models ─────────────────────────────────────
    
    async loadModels() {
        const response = await this.api.getModels();
        if (response.isSuccess()) {
            this.models = response.data.models;
        }
    }
    
    async loadSupportedTypes() {
        const response = await this.api.getSupportedProviderTypes();
        if (response.isSuccess()) {
            this.supportedTypes = response.data.types;
        }
    }
    
    async saveModel(modelData) {
        try {
            if (this.editingModel) {
                await this.api.updateModel(this.editingModel.id, modelData);
            } else {
                await this.api.createModel(modelData);
            }
            this.showModelForm = false;
            this.editingModel = null;
            await this.loadModels();
        } catch (e) {
            this.error = e.message;
        }
    }
    
    async deleteModel(id) {
        if (!confirm("Delete this model?")) return;
        await this.api.deleteModel(id);
        await this.loadModels();
    }
    
    editModel(model) {
        this.editingModel = { ...model };
        this.showModelForm = true;
    }
    
    // ─── Personas ───────────────────────────────────
    
    async loadPersonas() {
        const response = await this.api.getPersonas();
        if (response.isSuccess()) {
            this.personas = response.data.personas;
        }
    }
    
    async savePersona(personaData) {
        try {
            if (this.editingPersona) {
                await this.api.updatePersona(this.editingPersona.id, personaData);
            } else {
                await this.api.createPersona(personaData);
            }
            this.showPersonaForm = false;
            this.editingPersona = null;
            await this.loadPersonas();
        } catch (e) {
            this.error = e.message;
        }
    }
    
    async deletePersona(id) {
        if (!confirm("Delete this persona?")) return;
        await this.api.deletePersona(id);
        await this.loadPersonas();
    }
    
    editPersona(persona) {
        this.editingPersona = { ...persona };
        this.showPersonaForm = true;
    }
    
    // ─── Tabs ───────────────────────────────────────
    
    setActiveTab(tab) {
        this.activeTab = tab;
    }
}
```

### 11.3 Vue-компонент: AI Admin Page

```vue
<!-- src/core/pages/ai/AIAdminPage.vue -->

<style scoped>
.ai_admin_page {
    padding: 24px;
    max-width: 1200px;
    margin: 0 auto;
}

.ai_admin_page h1 {
    font-size: 28px;
    margin-bottom: 24px;
    color: #1a1a2e;
}

/* ─── Tabs ────────────────────────────── */

.tabs {
    display: flex;
    gap: 4px;
    margin-bottom: 24px;
    border-bottom: 2px solid #e0e0e0;
    padding-bottom: 0;
}

.tab {
    padding: 10px 20px;
    cursor: pointer;
    border: none;
    background: transparent;
    font-size: 14px;
    font-weight: 500;
    color: #666;
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
    transition: all 0.2s;
}

.tab:hover {
    color: #333;
}

.tab.active {
    color: #6c5ce7;
    border-bottom-color: #6c5ce7;
}

/* ─── Table ───────────────────────────── */

.data_table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.data_table th {
    text-align: left;
    padding: 12px 16px;
    background: #f8f9fa;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    color: #666;
    letter-spacing: 0.5px;
}

.data_table td {
    padding: 12px 16px;
    border-top: 1px solid #f0f0f0;
    font-size: 14px;
}

.data_table tr:hover td {
    background: #f8f9ff;
}

/* ─── Buttons ─────────────────────────── */

.btn {
    padding: 8px 16px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    transition: all 0.2s;
}

.btn-primary {
    background: #6c5ce7;
    color: white;
}

.btn-primary:hover {
    background: #5a4bd1;
}

.btn-danger {
    background: #e74c3c;
    color: white;
}

.btn-danger:hover {
    background: #c0392b;
}

.btn-sm {
    padding: 4px 10px;
    font-size: 12px;
}

.btn-group {
    display: flex;
    gap: 6px;
}

/* ─── Status Badge ────────────────────── */

.badge {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
}

.badge-active {
    background: #d4edda;
    color: #155724;
}

.badge-inactive {
    background: #f8d7da;
    color: #721c24;
}

/* ─── Form Modal ──────────────────────── */

.modal-overlay {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}

.modal {
    background: white;
    border-radius: 12px;
    padding: 24px;
    width: 500px;
    max-height: 80vh;
    overflow-y: auto;
}

.modal h2 {
    margin-bottom: 16px;
    font-size: 20px;
}

.form-group {
    margin-bottom: 16px;
}

.form-group label {
    display: block;
    margin-bottom: 6px;
    font-size: 13px;
    font-weight: 500;
    color: #333;
}

.form-group input,
.form-group textarea,
.form-group select {
    width: 100%;
    padding: 10px 12px;
    border: 1px solid #ddd;
    border-radius: 6px;
    font-size: 14px;
    transition: border-color 0.2s;
}

.form-group input:focus,
.form-group textarea:focus,
.form-group select:focus {
    outline: none;
    border-color: #6c5ce7;
}

.form-group textarea {
    min-height: 120px;
    resize: vertical;
    font-family: monospace;
}

.form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 20px;
}
</style>

<template>
    <div class="ai_admin_page">
        <h1>{{ model.getPageTitle() }}</h1>

        <!-- Loading -->
        <div v-if="model.loading">Loading...</div>
        
        <!-- Error -->
        <div v-if="model.error" class="error">{{ model.error }}</div>

        <!-- Tabs -->
        <div class="tabs" v-if="!model.loading">
            <button 
                class="tab" 
                :class="{ active: model.activeTab === 'providers' }"
                @click="model.setActiveTab('providers')"
            >
                📡 Providers ({{ model.providers.length }})
            </button>
            <button 
                class="tab"
                :class="{ active: model.activeTab === 'models' }"
                @click="model.setActiveTab('models')"
            >
                🧠 Models ({{ model.models.length }})
            </button>
            <button 
                class="tab"
                :class="{ active: model.activeTab === 'personas' }"
                @click="model.setActiveTab('personas')"
            >
                🎭 Personas ({{ model.personas.length }})
            </button>
        </div>

        <!-- Providers Tab -->
        <div v-if="model.activeTab === 'providers'">
            <div style="margin-bottom: 12px;">
                <button class="btn btn-primary" @click="model.showProviderForm = true">
                    + Add Provider
                </button>
            </div>
            <table class="data_table">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Type</th>
                        <th>API Key</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="p in model.providers" :key="p.id">
                        <td><strong>{{ p.name }}</strong></td>
                        <td>{{ p.type }}</td>
                        <td><code>{{ p.api_key_masked }}</code></td>
                        <td>
                            <span class="badge" :class="p.is_active ? 'badge-active' : 'badge-inactive'">
                                {{ p.is_active ? 'Active' : 'Inactive' }}
                            </span>
                        </td>
                        <td>
                            <div class="btn-group">
                                <button class="btn btn-sm" @click="model.editProvider(p)">Edit</button>
                                <button class="btn btn-sm btn-danger" @click="model.deleteProvider(p.id)">Delete</button>
                            </div>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- Models Tab -->
        <div v-if="model.activeTab === 'models'">
            <div style="margin-bottom: 12px;">
                <button class="btn btn-primary" @click="model.showModelForm = true">
                    + Add Model
                </button>
            </div>
            <table class="data_table">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Model ID</th>
                        <th>Provider</th>
                        <th>Context</th>
                        <th>Temperature</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="m in model.models" :key="m.id">
                        <td><strong>{{ m.name }}</strong></td>
                        <td><code>{{ m.model_id }}</code></td>
                        <td>{{ m.provider_id }}</td>
                        <td>{{ m.context_window?.toLocaleString() }}</td>
                        <td>{{ m.temperature }}</td>
                        <td>
                            <div class="btn-group">
                                <button class="btn btn-sm" @click="model.editModel(m)">Edit</button>
                                <button class="btn btn-sm btn-danger" @click="model.deleteModel(m.id)">Delete</button>
                            </div>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- Personas Tab -->
        <div v-if="model.activeTab === 'personas'">
            <div style="margin-bottom: 12px;">
                <button class="btn btn-primary" @click="model.showPersonaForm = true">
                    + Add Persona
                </button>
            </div>
            <table class="data_table">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Slug</th>
                        <th>Temperature</th>
                        <th>Models</th>
                        <th>Roles</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="p in model.personas" :key="p.id">
                        <td><strong>{{ p.name }}</strong></td>
                        <td><code>{{ p.slug }}</code></td>
                        <td>{{ p.temperature }}</td>
                        <td>{{ p.models?.length || 0 }}</td>
                        <td>{{ p.roles?.length || 0 }}</td>
                        <td>
                            <span class="badge" :class="p.is_active ? 'badge-active' : 'badge-inactive'">
                                {{ p.is_active ? 'Active' : 'Inactive' }}
                            </span>
                        </td>
                        <td>
                            <div class="btn-group">
                                <button class="btn btn-sm" @click="model.editPersona(p)">Edit</button>
                                <button class="btn btn-sm btn-danger" @click="model.deletePersona(p.id)">Delete</button>
                            </div>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- Provider Form Modal -->
        <div class="modal-overlay" v-if="model.showProviderForm" @click.self="model.showProviderForm = false">
            <div class="modal">
                <h2>{{ model.editingProvider ? 'Edit Provider' : 'New Provider' }}</h2>
                <div class="form-group">
                    <label>Name</label>
                    <input v-model="providerForm.name" placeholder="openrouter" />
                </div>
                <div class="form-group">
                    <label>Type</label>
                    <select v-model="providerForm.type">
                        <option v-for="t in model.supportedTypes" :key="t" :value="t">{{ t }}</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>API Key</label>
                    <input v-model="providerForm.api_key" type="password" placeholder="sk-..." />
                </div>
                <div class="form-group">
                    <label>Base URL (optional)</label>
                    <input v-model="providerForm.base_url" placeholder="https://..." />
                </div>
                <div class="form-actions">
                    <button class="btn" @click="model.showProviderForm = false">Cancel</button>
                    <button class="btn btn-primary" @click="saveProvider">Save</button>
                </div>
            </div>
        </div>

        <!-- Model Form Modal -->
        <div class="modal-overlay" v-if="model.showModelForm" @click.self="model.showModelForm = false">
            <div class="modal">
                <h2>{{ model.editingModel ? 'Edit Model' : 'New Model' }}</h2>
                <div class="form-group">
                    <label>Provider</label>
                    <select v-model.number="modelForm.provider_id">
                        <option v-for="p in model.providers" :key="p.id" :value="p.id">{{ p.name }}</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Model ID</label>
                    <input v-model="modelForm.model_id" placeholder="gpt-4o" />
                </div>
                <div class="form-group">
                    <label>Display Name</label>
                    <input v-model="modelForm.name" placeholder="GPT-4o" />
                </div>
                <div class="form-group">
                    <label>Max Tokens</label>
                    <input v-model.number="modelForm.max_tokens" type="number" />
                </div>
                <div class="form-group">
                    <label>Context Window</label>
                    <input v-model.number="modelForm.context_window" type="number" />
                </div>
                <div class="form-group">
                    <label>Temperature</label>
                    <input v-model.number="modelForm.temperature" type="number" step="0.1" min="0" max="2" />
                </div>
                <div class="form-actions">
                    <button class="btn" @click="model.showModelForm = false">Cancel</button>
                    <button class="btn btn-primary" @click="saveModel">Save</button>
                </div>
            </div>
        </div>

        <!-- Persona Form Modal -->
        <div class="modal-overlay" v-if="model.showPersonaForm" @click.self="model.showPersonaForm = false">
            <div class="modal">
                <h2>{{ model.editingPersona ? 'Edit Persona' : 'New Persona' }}</h2>
                <div class="form-group">
                    <label>Name</label>
                    <input v-model="personaForm.name" placeholder="Assistant" />
                </div>
                <div class="form-group">
                    <label>Slug</label>
                    <input v-model="personaForm.slug" placeholder="assistant" />
                </div>
                <div class="form-group">
                    <label>Soul (System Prompt)</label>
                    <textarea v-model="personaForm.soul" placeholder="You are a helpful AI assistant..."></textarea>
                </div>
                <div class="form-group">
                    <label>Temperature</label>
                    <input v-model.number="personaForm.temperature" type="number" step="0.1" min="0" max="2" />
                </div>
                <div class="form-actions">
                    <button class="btn" @click="model.showPersonaForm = false">Cancel</button>
                    <button class="btn btn-primary" @click="savePersona">Save</button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { AIAdminPageModel } from "./AIAdminPageModel";

export default {
    name: "AIAdminPage",
    
    data() {
        return {
            providerForm: { name: "", type: "openrouter", api_key: "", base_url: "" },
            modelForm: { provider_id: 1, model_id: "", name: "", max_tokens: 4096, context_window: 128000, temperature: 0.7 },
            personaForm: { name: "", slug: "", soul: "", temperature: 0.7 },
        };
    },
    
    computed: {
        layout() {
            return this.$layout;
        },
        model() {
            if (!this.layout.getPage("AIAdminPage")) {
                this.layout.registerPage("AIAdminPage", new AIAdminPageModel());
            }
            return this.layout.getPage("AIAdminPage");
        }
    },
    
    async mounted() {
        await this.model.init();
        
        // Pre-fill forms when editing
        if (this.model.editingProvider) {
            this.providerForm = { ...this.model.editingProvider };
        }
    },
    
    methods: {
        async saveProvider() {
            await this.model.saveProvider(this.providerForm);
            this.providerForm = { name: "", type: "openrouter", api_key: "", base_url: "" };
        },
        async saveModel() {
            await this.model.saveModel(this.modelForm);
            this.modelForm = { provider_id: 1, model_id: "", name: "", max_tokens: 4096, context_window: 128000, temperature: 0.7 };
        },
        async savePersona() {
            await this.model.savePersona(this.personaForm);
            this.personaForm = { name: "", slug: "", soul: "", temperature: 0.7 };
        }
    },

    watch: {
        'model.editingProvider'(val) {
            if (val) this.providerForm = { ...val };
        },
        'model.editingModel'(val) {
            if (val) this.modelForm = { ...val };
        },
        'model.editingPersona'(val) {
            if (val) this.personaForm = { ...val };
        }
    }
}
</script>
```

---

## 12. Исправление MCPClient.py

```python
# src/core/ai/mcp/MCPClient.py

import subprocess
import json
import select


class MCPClient:
    """
    Клиент для Model Context Protocol (MCP).
    
    Исправления по сравнению с предыдущей версией:
    - Баг: variable `method` → `method_name` в send_message()
    - Добавлены таймауты через select.select()
    - Добавлен метод is_connected()
    - Добавлен контекстный менеджер (__enter__, __exit__)
    """
    
    def __init__(self, path: str, args: list = None):
        self.path = path
        self.args = args or []
        self.process = None
        self.request_id = 0
    
    def start_server(self):
        """Запуск MCP сервера через stdio"""
        try:
            self.process = subprocess.Popen(
                [self.path] + self.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8"
            )
        except Exception as e:
            raise Exception(f"Ошибка запуска MCP сервера: {e}")
    
    def stop_server(self):
        """Остановка MCP сервера"""
        if self.process:
            if self.process.poll() is None:  # Процесс ещё жив
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
            self.process = None
    
    def connect(self):
        """Подключение к MCP серверу с инициализацией"""
        if not self.process or self.process.poll() is not None:
            self.start_server()
            self.initialize()
    
    def is_connected(self) -> bool:
        """Проверка состояния подключения"""
        return self.process is not None and self.process.poll() is None
    
    def send_message(self, method_name: str, params: dict = None, timeout: int = 30) -> dict:
        """
        Отправка JSON-RPC запроса к MCP серверу.
        
        Args:
            method_name: Имя метода (например "initialize", "tools/list")
            params: Параметры запроса
            timeout: Таймаут ожидания ответа в секундах
        """
        self.connect()
        
        self.request_id += 1
        
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method_name,  # ← ИСПРАВЛЕНО: было "method"
            "params": params or {}
        }
        
        data = json.dumps(request)
        self.process.stdin.write(data + "\n")
        self.process.stdin.flush()
        
        # Чтение с таймаутом
        ready, _, _ = select.select([self.process.stdout], [], [], timeout)
        if not ready:
            raise Exception(f"Таймаут ({timeout}s) ожидания ответа от MCP сервера")
        
        response_text = self.process.stdout.readline()
        if not response_text:
            raise Exception("Пустой ответ от MCP сервера")
        
        try:
            return json.loads(response_text.strip())
        except json.JSONDecodeError as e:
            raise Exception(f"Ошибка парсинга JSON: {e}")
    
    def getVersion(self) -> str:
        return "2025-06-18"
    
    def initialize(self) -> dict:
        """Инициализация MCP соединения"""
        return self.send_message("initialize", {
            "protocolVersion": self.getVersion(),
            "capabilities": {},
            "clientInfo": {
                "name": "BayLang AI",
                "version": "1.0.0",
            }
        })
    
    def list_tools(self) -> list:
        """Получение списка доступных инструментов"""
        response = self.send_message("tools/list")
        return response.get("result", {}).get("tools", [])
    
    def execute(self, name: str, params: dict) -> dict:
        """Вызов инструмента"""
        return self.send_message("tools/call", {
            "name": name,
            "arguments": params,
        })
    
    # ─── Контекстный менеджер ─────────────────────────
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_server()
        return False
```

---

## 13. MCPManager

```python
# src/core/ai/mcp/MCPManager.py

import os
import json
from .MCPClient import MCPClient


class MCPManager:
    """
    Менеджер для управления несколькими MCP серверами.
    
    Загружает конфигурацию из переменных окружения,
    подключает серверы при старте и предоставляет
    единый интерфейс для вызова инструментов.
    """
    
    def __init__(self):
        self.clients = {}      # {name: MCPClient}
        self.tools_cache = {}  # {tool_name: client_name}
    
    def load_from_env(self):
        """Загрузка конфигурации из переменных окружения"""
        config_data = os.getenv("MCP_SERVERS_CONFIG")
        if config_data:
            try:
                config = json.loads(config_data)
                self.load_config(config)
            except json.JSONDecodeError as e:
                print(f"Ошибка парсинга MCP конфигурации: {e}")
    
    def load_config(self, servers_config: list):
        """Загрузка конфигурации из списка"""
        for server in servers_config:
            if server.get("enabled", True):
                name = server["name"]
                path = server["path"]
                args = server.get("args", [])
                
                client = MCPClient(path, args)
                self.clients[name] = client
    
    def connect_all(self):
        """Подключение всех серверов"""
        for name, client in self.clients.items():
            try:
                client.connect()
                print(f"MCP сервер '{name}' подключен")
            except Exception as e:
                print(f"Ошибка подключения MCP сервера '{name}': {e}")
    
    def get_all_tools(self) -> dict:
        """Получение инструментов со всех серверов"""
        all_tools = {}
        
        for name, client in self.clients.items():
            try:
                if client.is_connected():
                    tools = client.list_tools()
                    for tool in tools:
                        tool_key = f"{name}:{tool['name']}"
                        all_tools[tool_key] = {
                            "server": name,
                            "tool": tool
                        }
            except Exception as e:
                print(f"Ошибка получения инструментов с '{name}': {e}")
        
        return all_tools
    
    def execute_tool(self, full_tool_name: str, arguments: dict):
        """Выполнение инструмента (формат: server:tool)"""
        parts = full_tool_name.split(":", 1)
        if len(parts) != 2:
            raise ValueError(f"Неверный формат имени: {full_tool_name}")
        
        server_name, tool_name = parts
        
        if server_name not in self.clients:
            raise ValueError(f"Сервер '{server_name}' не найден")
        
        client = self.clients[server_name]
        if not client.is_connected():
            client.connect()
        
        return client.execute(tool_name, arguments)
    
    def disconnect_all(self):
        """Отключение всех серверов"""
        for name, client in self.clients.items():
            try:
                client.stop_server()
                print(f"MCP сервер '{name}' отключен")
            except Exception as e:
                print(f"Ошибка отключения MCP сервера '{name}': {e}")
```

---

## 14. Обновлённый LayoutModel

```javascript
// src/core/pages/LayoutModel.js (обновлённый)

export class LayoutModel {
    
    constructor() {
        this.pages = {};
        this.models = {};
    }
    
    // ─── Pages ─────────────────────────────────────
    
    registerPage(name, page) {
        this.pages[name] = page;
    }
    
    getPage(name) {
        return this.pages[name] || null;
    }
    
    // ─── Models (AI models list) ──────────────────
    
    setModels(models) {
        this.models = models;
    }
    
    getModels() {
        return this.models;
    }
    
    getModelById(id) {
        return this.models[id] || null;
    }
}
```

---

## 15. Требования к реализации

### 15.1 Приоритеты

| Приоритет | Задача | Описание |
|-----------|--------|----------|
| 🔴 Высокий | Миграции БД | Таблицы providers, models, ai, ai_roles, ai_models |
| 🔴 Высокий | BaseProvider + ProviderFactory | Абстракция и фабрика провайдеров |
| 🔴 Высокий | OpenRouterProvider | Реализация для основного провайдера |
| 🔴 Высокий | Репозитории | ProviderRepository, ModelRepository, AIRepository |
| 🔴 Высокий | API CRUD | Эндпоинты для управления всеми сущностями |
| 🟡 Средний | AIService (фасад) | Чат с fallback моделями |
| 🟡 Средний | Frontend: AIAdminPage | Страница администрирования |
| 🟡 Средний | Исправление MCPClient | Баг method_name, таймауты |
| 🟢 Низкий | OpenAIProvider | Дополнительный провайдер |
| 🟢 Низкий | AnthropicProvider | Дополнительный провайдер |
| 🟢 Низкий | Streaming | SSE для streaming ответов |
| 🟢 Низкий | MCPManager | Менеджер MCP серверов |

### 15.2 Оценка трудозатрат

| Модуль | Оценка |
|--------|--------|
| Миграции БД | 2–3 часа |
| Provider classes + Factory | 4–6 часов |
| Репозитории | 3–4 часа |
| API эндпоинты | 4–5 часов |
| AIService (фасад) | 3–4 часа |
| Frontend (AIAdminPage) | 4–6 часов |
| MCPClient исправления | 1–2 часа |
| Тестирование | 3–4 часа |
| **ИТОГО** | **24–34 часа** |

### 15.3 Зависимости

- Python 3.10+
- FastAPI + uvicorn
- SQLite3 (или Cloudflare D1)
- requests (для HTTP к LLM API)
- python-dotenv
- Vue 3 + Rollup

---

## 16. Итог

Данное техническое задание описывает полную архитектуру AI-подсистемы BayLang Cloud AGI: от базы данных и backend-классов до frontend-интерфейса администрирования.

**Ключевые архитектурные решения:**

1. **Полиморфизм провайдеров** — каждый провайдер (OpenRouter, OpenAI, Anthropic) реализует свой класс с уникальной логикой формирования запросов и парсинга ответов. Фабрика `ProviderFactory` создаёт нужный экземпляр по типу из БД.

2. **Модель с fallback** — AI-личность может привязать несколько моделей с приоритетами. Если основная модель недоступна, автоматически используется следующая.

3. **Системный промпт как灵魂 (soul)** — «душой» AI-личности является её системный промпт, который расширяется при выборе роли.

4. **Разделение backend/frontend** — Вся логика (провайдеры, БД, сервисы) живёт в Python. Vue-компоненты только отображают данные, полученные из моделей.

5. **DI Container** — Все зависимости управляются через контейнер, что обеспечивает тестируемость и гибкость.

**Итоговая оценка:** ~24–34 часа на полную реализацию MVP с рабочими CRUD-операциями, базовым чатом и интерфейсом администрирования.
