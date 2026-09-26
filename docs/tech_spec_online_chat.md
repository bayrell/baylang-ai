# Техническое задание: Онлайн чат с AI (Polling)

## 1. Введение

### 1.1 Назначение документа

Данный документ описывает архитектуру и реализацию **онлайн-чата** с AI в проекте BayLang Cloud AGI. Ключевое ограничение — **отказ от WebSocket** в пользу **polling-механизма**: клиент периодически отправляет HTTP-запросы для проверки обновлений.

### 1.2 Почему polling, а не WebSocket

| Критерий | WebSocket | Polling (наш выбор) |
|----------|-----------|---------------------|
| **Совместимость** | Требует поддержки WS прокси | Работает везде через HTTP |
| **Cloudflare Workers** | Ограничения в serverless | Полная поддержка |
| **Cloudflare D1** | Требует持久ного соединения | Нативно для REST |
| **Простота реализации** | Сложнее (handshake, heartbeat) | Проще (обычные GET/POST) |
| **Отладка** | Сложнее (нужны WS-клиенты) | Проще (curl, браузер) |

### 1.3 Модель работы

```
┌──────────┐  POST /api/chat/send   ┌──────────┐  OpenRouter API  ┌──────────┐
│ Frontend │ ──────────────────────► │ Backend  │ ──────────────► │ LLM API  │
│ (Vue 3)  │                         │ (FastAPI)│ ◄────────────── │ (GPT etc)│
│          │  GET  /api/chat/poll    │          │    ответ        │          │
│          │ ◄────────────────────── │          │                 └──────────┘
│          │  (каждые N сек)         │          │ ────────┐
└──────────┘                         │          │         │ сохранение
                                     │          │ ◄───────┘ в БД
                                     └──────────┘
```

**Ключевая идея:**
1. Пользователь отправляет сообщение → `POST /api/chat/send` → Backend начинает обработку
2. Frontend запускает polling → `GET /api/chat/poll?chat_id=X&last_message_id=Y`
3. Backend возвращает новые сообщения (ответ AI + результаты tools), если они появились
4. Все сообщения (пользователя, AI, system, tool results) хранятся в БД

---

## 2. Структура базы данных

### 2.1 Таблица `chats`

Хранит информацию о чатах (сессиях диалога).

```sql
CREATE TABLE chats (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,              -- FK → users.id
    ai_id       INTEGER NOT NULL,              -- FK → ai.id
    title       TEXT,                          -- Название чата (авто или ручное)
    role_slug   TEXT,                          -- Роль AI (slug)
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (ai_id) REFERENCES ai(id) ON DELETE SET NULL
);

CREATE INDEX idx_chats_user_id ON chats(user_id);
CREATE INDEX idx_chats_ai_id ON chats(ai_id);
```

### 2.2 Таблица `chat_messages`

Хранит все сообщения чата: пользовательские, ответы AI, результаты инструментов, системные.

```sql
CREATE TABLE chat_messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id         INTEGER NOT NULL,           -- FK → chats.id
    role            TEXT NOT NULL,              -- "user" | "assistant" | "system" | "tool"
    content         TEXT,                       -- Текст сообщения
    model_used      TEXT,                       -- Какая модель сгенерировала ответ
    provider_used   TEXT,                       -- Какой провайдер
    tool_name       TEXT,                       -- Имя вызванного инструмента (для role=tool)
    tool_call_id    TEXT,                       -- ID вызова инструмента (для сопоставления)
    tool_result     TEXT,                       -- Результат выполнения инструмента (JSON)
    metadata        TEXT DEFAULT '{}',          -- JSON: токены, время генерации и т.п.
    is_streaming    INTEGER DEFAULT 0,          -- Сообщение в процессе генерации
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
);

CREATE INDEX idx_chat_messages_chat_id ON chat_messages(chat_id);
CREATE INDEX idx_chat_messages_created_at ON chat_messages(created_at);
```

### 2.3 ER-диаграмма

```
┌──────────────┐       ┌──────────────────┐       ┌──────────────┐
│    users     │       │      chats       │       │      ai      │
├──────────────┤       ├──────────────────┤       ├──────────────┤
│ id (PK)      │◄──┐   │ id (PK)          │   ┌──►│ id (PK)      │
│ username     │   │   │ user_id (FK)     │───┘   │ name         │
│ email        │   └───│ ai_id (FK)       │       │ slug         │
│ ...          │       │ title            │       │ soul         │
└──────────────┘       │ role_slug        │       │ ...          │
                       │ created_at       │       └──────────────┘
                       │ updated_at       │
                       └────────┬─────────┘
                                │
                                │ 1:N
                                ▼
                       ┌──────────────────┐
                       │  chat_messages   │
                       ├──────────────────┤
                       │ id (PK)          │
                       │ chat_id (FK)     │
                       │ role             │  "user" | "assistant" | "system" | "tool"
                       │ content          │
                       │ model_used       │
                       │ provider_used    │
                       │ tool_name        │
                       │ tool_call_id     │
                       │ tool_result      │
                       │ metadata         │  JSON: tokens, timing
                       │ is_streaming     │
                       │ created_at       │
                       └──────────────────┘
```

---

## 3. Типы сообщений в чате

Сообщения в чате имеют四种角色 (roles):

### 3.1 `user` — Сообщение пользователя

```json
{
    "id": 42,
    "chat_id": 1,
    "role": "user",
    "content": "Прочитай файл config.json и найди ошибку",
    "created_at": "2026-09-25T17:00:00"
}
```

### 3.2 `assistant` — Ответ AI

```json
{
    "id": 43,
    "chat_id": 1,
    "role": "assistant",
    "content": "Сейчас прочитаю файл config.json...",
    "model_used": "gpt-4o",
    "provider_used": "openrouter",
    "tool_calls": [
        {
            "id": "call_abc123",
            "name": "read_file",
            "arguments": {"path": "config.json"}
        }
    ],
    "metadata": {
        "prompt_tokens": 250,
        "completion_tokens": 45,
        "total_tokens": 295,
        "generation_time_ms": 1200
    },
    "created_at": "2026-09-25T17:00:01"
}
```

### 3.3 `tool` — Результат инструмента

```json
{
    "id": 44,
    "chat_id": 1,
    "role": "tool",
    "tool_name": "read_file",
    "tool_call_id": "call_abc123",
    "content": "Содержимое файла config.json...",
    "tool_result": {
        "success": true,
        "data": "{...}",
        "size": 1024
    },
    "created_at": "2026-09-25T17:00:02"
}
```

### 3.4 `system` — Системные сообщения

```json
{
    "id": 45,
    "chat_id": 1,
    "role": "system",
    "content": "Контекст сессии: пользователь работает над проектом BayLang Cloud AGI",
    "created_at": "2026-09-25T17:00:03"
}
```

---

## 4. API Эндпоинты

### 4.1 Создание чата

```
POST /api/chat/create
```

**Request:**
```json
{
    "ai_slug": "assistant",
    "role_slug": null,
    "title": null
}
```

**Response:**
```json
{
    "chat_id": 1,
    "title": "Диалог с Ассистентом",
    "created_at": "2026-09-25T17:00:00"
}
```

### 4.2 Отправка сообщения

```
POST /api/chat/send
```

**Request:**
```json
{
    "chat_id": 1,
    "content": "Прочитай файл config.json и найди ошибку",
    "tools": true
}
```

**Response (синхронный режим):**
```json
{
    "message_id": 43,
    "status": "processing",
    "created_at": "2026-09-25T17:00:01"
}
```

> **Важно:** Ответ возвращается сразу с `status: "processing"`. Полный ответ AI (включая результаты tools) появится после обработки и будет доступен через polling.

### 4.3 Polling — Проверка обновлений

```
GET /api/chat/poll?chat_id=1&last_message_id=42
```

**Параметры:**
| Параметр | Тип | Описание |
|----------|-----|----------|
| `chat_id` | int | ID чата |
| `last_message_id` | int | ID последнего полученного сообщения клиента |
| `limit` | int | Макс. кол-во сообщений (по умолчанию 50) |

**Response:**
```json
{
    "messages": [
        {
            "id": 43,
            "role": "assistant",
            "content": "Сейчас прочитаю файл...",
            "model_used": "gpt-4o",
            "provider_used": "openrouter",
            "tool_calls": [...],
            "created_at": "2026-09-25T17:00:01"
        },
        {
            "id": 44,
            "role": "tool",
            "tool_name": "read_file",
            "tool_call_id": "call_abc123",
            "content": "Содержимое файла...",
            "tool_result": {...},
            "created_at": "2026-09-25T17:00:02"
        },
        {
            "id": 45,
            "role": "assistant",
            "content": "Нашёл ошибку в строке 15: ...",
            "model_used": "gpt-4o",
            "provider_used": "openrouter",
            "created_at": "2026-09-25T17:00:05"
        }
    ],
    "last_message_id": 45,
    "has_more": false
}
```

### 4.4 Список чатов пользователя

```
GET /api/chat/list?page=1&limit=20
```

**Response:**
```json
{
    "chats": [
        {
            "id": 1,
            "title": "Диалог с Ассистентом",
            "ai_id": 1,
            "ai_name": "Ассистент",
            "message_count": 45,
            "last_message_at": "2026-09-25T17:00:05",
            "created_at": "2026-09-25T17:00:00"
        }
    ],
    "total": 15,
    "page": 1,
    "pages": 1
}
```

### 4.5 История чата

```
GET /api/chat/history?chat_id=1&page=1&limit=50
```

**Response:**
```json
{
    "messages": [
        {
            "id": 1,
            "role": "user",
            "content": "Привет!",
            "created_at": "2026-09-25T17:00:00"
        },
        {
            "id": 2,
            "role": "assistant",
            "content": "Привет! Чем могу помочь?",
            "model_used": "gpt-4o",
            "created_at": "2026-09-25T17:00:01"
        }
    ],
    "total": 45,
    "page": 1,
    "pages": 1
}
```

### 4.6 Очистка чата

```
DELETE /api/chat/clear?chat_id=1
```

### 4.7 Удаление чата

```
DELETE /api/chat/delete?chat_id=1
```

### 4.8 Переименование чата

```
PUT /api/chat/rename
```

**Request:**
```json
{
    "chat_id": 1,
    "title": "Новое название"
}
```

---

## 5. Backend: Сервисы

### 5.1 ChatService — основной сервис

```python
# src/core/ai/chat/ChatService.py

import json
import time
from typing import Optional, List

from core.ai.providers.ProviderFactory import ProviderFactory, ProviderException
from core.ai.messages.Message import Message
from core.ai.context.ConversationContext import ConversationContext
from core.ai.mcp.MCPManager import MCPManager


class ChatService:
    """
    Сервис управления чатами и обработки сообщений.
    
    Ключевые особенности:
    - Все сообщения сохраняются в БД
    - Результаты инструментов (tools) хранятся как отдельные сообщения
    - AI может вызывать инструменты несколько раз (agentic loop)
    - Polling: клиент проверяет новые сообщения через GET /poll
    """
    
    def __init__(self, db, ai_repository, provider_repository, 
                 mcp_manager: Optional[MCPManager] = None):
        self.db = db
        self.ai_repo = ai_repository
        self.provider_repo = provider_repository
        self.mcp_manager = mcp_manager
        
        # Кэш провайдеров
        self._providers_cache = {}
    
    # ─── Чаты ─────────────────────────────────────────
    
    async def create_chat(self, user_id: int, ai_slug: str, 
                          role_slug: str = None, title: str = None) -> dict:
        """Создание нового чата"""
        ai = await self.ai_repo.find_by_slug_with_models_and_roles(ai_slug)
        if not ai:
            raise ValueError(f"AI '{ai_slug}' не найдена")
        
        if not title:
            title = f"Диалог с {ai.name}"
        
        cursor = await self.db.execute(
            """INSERT INTO chats (user_id, ai_id, title, role_slug)
               VALUES (?, ?, ?, ?)""",
            [user_id, ai.id, title, role_slug]
        )
        
        chat_id = cursor.lastrowid
        
        # Сохраняем системное сообщение (soul)
        system_content = ai.soul
        if role_slug:
            for role in ai.roles:
                if role.slug == role_slug:
                    system_content += f"\n\n---\nРоль: {role.name}\nИнструкция: {role.prompt}"
                    break
        
        await self._save_message(chat_id, "system", system_content)
        
        return {
            "chat_id": chat_id,
            "title": title,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S")
        }
    
    async def get_user_chats(self, user_id: int, page: int = 1, 
                             limit: int = 20) -> dict:
        """Получение списка чатов пользователя"""
        offset = (page - 1) * limit
        
        # Общее количество
        count_row = await self.db.fetch_one(
            "SELECT COUNT(*) as count FROM chats WHERE user_id = ?",
            [user_id]
        )
        total = count_row["count"] if count_row else 0
        
        # Чаты с доп. информацией
        chats = await self.db.fetch_all(
            """SELECT c.*, 
                      a.name as ai_name,
                      (SELECT COUNT(*) FROM chat_messages WHERE chat_id = c.id) as message_count,
                      (SELECT MAX(created_at) FROM chat_messages WHERE chat_id = c.id) as last_message_at
               FROM chats c
               LEFT JOIN ai ON c.ai_id = ai.id
               WHERE c.user_id = ?
               ORDER BY last_message_at DESC NULLS LAST, c.created_at DESC
               LIMIT ? OFFSET ?""",
            [user_id, limit, offset]
        )
        
        return {
            "chats": chats,
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit
        }
    
    async def delete_chat(self, chat_id: int, user_id: int) -> bool:
        """Удаление чата (с проверкой владельца)"""
        chat = await self.db.fetch_one(
            "SELECT * FROM chats WHERE id = ? AND user_id = ?",
            [chat_id, user_id]
        )
        if not chat:
            return False
        
        await self.db.execute("DELETE FROM chat_messages WHERE chat_id = ?", [chat_id])
        await self.db.execute("DELETE FROM chats WHERE id = ?", [chat_id])
        return True
    
    async def rename_chat(self, chat_id: int, user_id: int, title: str) -> bool:
        """Переименование чата"""
        result = await self.db.execute(
            "UPDATE chats SET title = ? WHERE id = ? AND user_id = ?",
            [title, chat_id, user_id]
        )
        return True
    
    # ─── Сообщения ────────────────────────────────────
    
    async def send_message(self, chat_id: int, user_id: int, 
                           content: str, use_tools: bool = True) -> dict:
        """
        Отправка сообщения пользователя и обработка ответа AI.
        
        Это ОСНОВНОЙ метод, который:
        1. Сохраняет сообщение пользователя
        2. Загружает историю чата
        3. Отправляет в AI (с tools если нужно)
        4. Обрабатывает цикл tool calls (agentic loop)
        5. Сохраняет все ответы в БД
        
        Returns:
            {"message_id": int, "status": "completed"|"processing"}
        """
        # Проверяем, что чат принадлежит пользователю
        chat = await self.db.fetch_one(
            "SELECT * FROM chats WHERE id = ? AND user_id = ?",
            [chat_id, user_id]
        )
        if not chat:
            raise ValueError("Чат не найден")
        
        # 1. Сохраняем сообщение пользователя
        user_msg_id = await self._save_message(chat_id, "user", content)
        
        # 2. Загружаем AI-личность
        ai = await self.ai_repo.find_by_slug_with_models_and_roles(chat.get("ai_slug", "assistant"))
        if not ai:
            # Fallback: загружаем по ai_id из чата
            ai_row = await self.db.fetch_one(
                "SELECT * FROM ai WHERE id = ?", [chat["ai_id"]]
            )
            if not ai_row:
                raise ValueError("AI-личность не найдена")
            ai = await self.ai_repo.find_by_slug_with_models_and_roles(ai_row["slug"])
        
        # 3. Собираем контекст из истории БД
        history_messages = await self._build_context_from_db(chat_id)
        
        # 4. Выбираем модель
        model = ai.get_active_model()
        if not model:
            raise ValueError("Нет доступных моделей")
        
        provider = self._get_provider(model.provider_id)
        
        # 5. Agentic loop: AI может вызывать tools несколько раз
        max_iterations = 10  # Защита от бесконечного цикла
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Отправляем запрос к AI
            start_time = time.time()
            
            tools_schema = None
            if use_tools and self.mcp_manager:
                tools_schema = self._get_tools_schema()
            
            try:
                kwargs = {
                    "temperature": ai.temperature,
                    "max_tokens": ai.max_tokens,
                }
                if tools_schema:
                    kwargs["tools"] = tools_schema
                
                result = provider.send(model.model_id, history_messages, **kwargs)
                
            except ProviderException:
                # Fallback на следующую модель
                result = await self._try_fallback(ai, history_messages, model.id, **kwargs)
            
            generation_time_ms = int((time.time() - start_time) * 1000)
            
            content_text = result.get("content", "")
            tool_calls = result.get("tool_calls", [])
            
            # 6. Сохраняем ответ AI (даже если пустой — важны tool_calls)
            ai_msg_id = await self._save_message(
                chat_id, "assistant", content_text,
                model_used=model.model_id,
                provider_used=provider.name,
                tool_calls=tool_calls,
                metadata=json.dumps({
                    "prompt_tokens": result.get("usage", {}).get("prompt_tokens", 0),
                    "completion_tokens": result.get("usage", {}).get("completion_tokens", 0),
                    "total_tokens": result.get("usage", {}).get("total_tokens", 0),
                    "generation_time_ms": generation_time_ms,
                    "iteration": iteration
                })
            )
            
            # 7. Если нет tool_calls — завершаем
            if not tool_calls:
                break
            
            # 8. Выполняем каждый tool call и сохраняем результат
            for tc in tool_calls:
                tool_name = tc.get("function", {}).get("name", "")
                tool_args_str = tc.get("function", {}).get("arguments", "{}")
                tool_call_id = tc.get("id", "")
                
                try:
                    tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                except json.JSONDecodeError:
                    tool_args = {}
                
                # Выполняем инструмент
                tool_result = await self._execute_tool(tool_name, tool_args)
                
                # Сохраняем результат как сообщение role=tool
                await self._save_message(
                    chat_id, "tool", 
                    content=json.dumps(tool_result, ensure_ascii=False),
                    tool_name=tool_name,
                    tool_call_id=tool_call_id,
                    tool_result=json.dumps(tool_result, ensure_ascii=False)
                )
                
                # Добавляем в контекст для следующей итерации
                history_messages.append({
                    "role": "assistant",
                    "content": content_text,
                    "tool_calls": tool_calls
                })
                history_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": json.dumps(tool_result, ensure_ascii=False)
                })
        
        return {
            "message_id": ai_msg_id,
            "status": "completed"
        }
    
    async def poll_messages(self, chat_id: int, user_id: int, 
                            last_message_id: int = 0, limit: int = 50) -> dict:
        """
        Polling: получение новых сообщений после last_message_id.
        
        Клиент вызывает этот метод каждые N секунд.
        Возвращает только новые сообщения (增量).
        """
        # Проверяем доступ
        chat = await self.db.fetch_one(
            "SELECT * FROM chats WHERE id = ? AND user_id = ?",
            [chat_id, user_id]
        )
        if not chat:
            raise ValueError("Чат не найден")
        
        # Получаем сообщения новее last_message_id
        messages = await self.db.fetch_all(
            """SELECT id, chat_id, role, content, model_used, provider_used,
                      tool_name, tool_call_id, tool_result, metadata, 
                      is_streaming, created_at
               FROM chat_messages
               WHERE chat_id = ? AND id > ?
               ORDER BY id ASC
               LIMIT ?""",
            [chat_id, last_message_id, limit]
        )
        
        # Парсим JSON поля
        for msg in messages:
            if msg.get("tool_result"):
                try:
                    msg["tool_result"] = json.loads(msg["tool_result"])
                except json.JSONDecodeError:
                    pass
            if msg.get("metadata"):
                try:
                    msg["metadata"] = json.loads(msg["metadata"])
                except json.JSONDecodeError:
                    pass
        
        last_id = messages[-1]["id"] if messages else last_message_id
        
        return {
            "messages": messages,
            "last_message_id": last_id,
            "has_more": len(messages) == limit
        }
    
    async def get_chat_history(self, chat_id: int, user_id: int,
                               page: int = 1, limit: int = 50) -> dict:
        """Получение полной истории чата (с пагинацией)"""
        chat = await self.db.fetch_one(
            "SELECT * FROM chats WHERE id = ? AND user_id = ?",
            [chat_id, user_id]
        )
        if not chat:
            raise ValueError("Чат не найден")
        
        offset = (page - 1) * limit
        
        count_row = await self.db.fetch_one(
            "SELECT COUNT(*) as count FROM chat_messages WHERE chat_id = ?",
            [chat_id]
        )
        total = count_row["count"] if count_row else 0
        
        messages = await self.db.fetch_all(
            """SELECT id, chat_id, role, content, model_used, provider_used,
                      tool_name, tool_call_id, tool_result, metadata,
                      is_streaming, created_at
               FROM chat_messages
               WHERE chat_id = ?
               ORDER BY id ASC
               LIMIT ? OFFSET ?""",
            [chat_id, limit, offset]
        )
        
        for msg in messages:
            if msg.get("tool_result"):
                try:
                    msg["tool_result"] = json.loads(msg["tool_result"])
                except json.JSONDecodeError:
                    pass
            if msg.get("metadata"):
                try:
                    msg["metadata"] = json.loads(msg["metadata"])
                except json.JSONDecodeError:
                    pass
        
        return {
            "messages": messages,
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit
        }
    
    async def clear_chat(self, chat_id: int, user_id: int) -> bool:
        """Очистка сообщений чата (сохраняет сам чат)"""
        chat = await self.db.fetch_one(
            "SELECT * FROM chats WHERE id = ? AND user_id = ?",
            [chat_id, user_id]
        )
        if not chat:
            return False
        
        await self.db.execute(
            "DELETE FROM chat_messages WHERE chat_id = ?", [chat_id]
        )
        return True
    
    # ─── Внутренние методы ────────────────────────────
    
    async def _save_message(self, chat_id: int, role: str, content: str,
                            model_used: str = None, provider_used: str = None,
                            tool_calls: list = None, tool_name: str = None,
                            tool_call_id: str = None, tool_result: str = None,
                            metadata: str = None) -> int:
        """Сохранение сообщения в БД"""
        # Для assistant с tool_calls сохраняем tool_calls в metadata
        if tool_calls and not metadata:
            metadata = json.dumps({"tool_calls": tool_calls})
        elif tool_calls and metadata:
            try:
                m = json.loads(metadata)
                m["tool_calls"] = tool_calls
                metadata = json.dumps(m)
            except json.JSONDecodeError:
                metadata = json.dumps({"tool_calls": tool_calls})
        
        cursor = await self.db.execute(
            """INSERT INTO chat_messages 
               (chat_id, role, content, model_used, provider_used,
                tool_name, tool_call_id, tool_result, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [chat_id, role, content, model_used, provider_used,
             tool_name, tool_call_id, tool_result, metadata]
        )
        
        # Обновляем updated_at чата
        await self.db.execute(
            "UPDATE chats SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            [chat_id]
        )
        
        return cursor.lastrowid
    
    async def _build_context_from_db(self, chat_id: int) -> list:
        """Построение контекста (history) из БД для отправки в LLM"""
        messages = await self.db.fetch_all(
            """SELECT role, content, tool_name, tool_call_id, tool_result, metadata
               FROM chat_messages
               WHERE chat_id = ? AND role != 'tool'
               ORDER BY id ASC""",
            [chat_id]
        )
        
        context = []
        for msg in messages:
            role = msg["role"]
            
            if role == "system":
                context.append({"role": "system", "content": msg["content"]})
            
            elif role == "user":
                context.append({"role": "user", "content": msg["content"]})
            
            elif role == "assistant":
                entry = {"role": "assistant", "content": msg["content"] or ""}
                
                # Добавляем tool_calls если есть
                if msg.get("metadata"):
                    try:
                        meta = json.loads(msg["metadata"])
                        if "tool_calls" in meta:
                            entry["tool_calls"] = meta["tool_calls"]
                    except json.JSONDecodeError:
                        pass
                
                context.append(entry)
        
        return context
    
    def _get_provider(self, provider_id: int):
        """Получение провайдера (с кэшированием)"""
        if provider_id not in self._providers_cache:
            row = self.provider_repo.find_by_id(provider_id)
            if not row:
                raise ValueError(f"Провайдер id={provider_id} не найден")
            self._providers_cache[provider_id] = ProviderFactory.create(row)
        return self._providers_cache[provider_id]
    
    def _get_tools_schema(self) -> list:
        """Получение схемы инструментов для LLM (формат OpenAI)"""
        if not self.mcp_manager:
            return []
        
        all_tools = self.mcp_manager.get_all_tools()
        schema = []
        
        for tool_key, tool_info in all_tools.items():
            tool = tool_info["tool"]
            schema.append({
                "type": "function",
                "function": {
                    "name": tool_key,
                    "description": tool.get("description", ""),
                    "parameters": tool.get("inputSchema", {})
                }
            })
        
        return schema
    
    async def _execute_tool(self, tool_name: str, arguments: dict) -> dict:
        """Выполнение инструмента через MCPManager"""
        if not self.mcp_manager:
            return {"error": "MCP не подключен"}
        
        try:
            result = self.mcp_manager.execute_tool(tool_name, arguments)
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _try_fallback(self, ai, messages, failed_model_id, **kwargs):
        """Попытка fallback на другую модель"""
        fallback_models = ai.get_fallback_models()
        
        for fallback in fallback_models:
            if fallback.id == failed_model_id:
                continue
            try:
                provider = self._get_provider(fallback.provider_id)
                return provider.send(fallback.model_id, messages, **kwargs)
            except ProviderException:
                continue
        
        raise ProviderException("Все модели исчерпаны")
```

### 5.2 Триггер обновления (Push-уведомление)

Для уменьшения задержки между получением ответа AI и его отображением на клиенте, используется **гибридный подход**: polling + короткий push-сигнал.

```
POST /api/chat/send         →  Клиент отправляет сообщение
     ↓
Backend обрабатывает        →  Сохраняет ответ в БД
     ↓
POST /api/chat/push-ready   →  Backend уведомляет клиент (через POST с callback URL)
```

Но для простоты MVP используем **адаптивный polling**:

```javascript
// Адаптивный polling на клиенте
class ChatPoller {
    constructor(chatId, lastMessageId) {
        this.chatId = chatId;
        this.lastMessageId = lastMessageId;
        this.interval = 2000;         // Начальный интервал: 2 сек
        this.minInterval = 1000;      // Минимум: 1 сек
        this.maxInterval = 10000;     // Максимум: 10 сек
        this.isProcessing = false;    // Есть ли в обработке сообщение
        this.timer = null;
    }
    
    start() {
        this._poll();
    }
    
    stop() {
        clearTimeout(this.timer);
    }
    
    setProcessing(processing) {
        this.isProcessing = processing;
        if (processing) {
            this.interval = this.minInterval;  // Ускоряем polling
        }
    }
    
    async _poll() {
        try {
            const response = await fetch(
                `/api/chat/poll?chat_id=${this.chatId}&last_message_id=${this.lastMessageId}`
            );
            const data = await response.json();
            
            if (data.messages && data.messages.length > 0) {
                // Есть новые сообщения!
                this.lastMessageId = data.last_message_id;
                this.onMessages(data.messages);
                
                // Если были assistant сообщения — замедляем polling
                const hasAssistant = data.messages.some(m => m.role === "assistant");
                if (hasAssistant) {
                    this.isProcessing = false;
                    this.interval = this.maxInterval;
                }
            } else {
                // Нет новых сообщений — постепенно замедляем
                if (!this.isProcessing) {
                    this.interval = Math.min(this.interval * 1.5, this.maxInterval);
                }
            }
        } catch (e) {
            console.error("Polling error:", e);
        }
        
        // Следующий poll
        this.timer = setTimeout(() => this._poll(), this.interval);
    }
    
    onMessages(messages) {
        // Переопределяется извне
        console.log("New messages:", messages);
    }
}
```

---

## 6. API роуты (FastAPI)

```python
# src/core/api/chat_routes.py

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/api/chat", tags=["Chat"])


# ─── Request Models ─────────────────────────────────

class CreateChatRequest(BaseModel):
    ai_slug: str = "assistant"
    role_slug: Optional[str] = None
    title: Optional[str] = None

class SendMessageRequest(BaseModel):
    chat_id: int
    content: str
    tools: bool = True

class PollRequest(BaseModel):
    chat_id: int
    last_message_id: int = 0
    limit: int = 50

class RenameChatRequest(BaseModel):
    chat_id: int
    title: str


# ─── Auth Dependency ────────────────────────────────

def get_current_user():
    """Получение текущего пользователя из JWT"""
    from core.auth.jwt_service import JWTService
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from fastapi import Depends
    
    security = HTTPBearer()
    jwt_service = JWTService()
    
    async def _get_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
        payload = jwt_service.verify_token(credentials.credentials)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid token")
        return payload
    
    return Depends(_get_user)


# ─── Эндпоинты ─────────────────────────────────────

@router.post("/create")
async def create_chat(request: CreateChatRequest, user: dict = get_current_user()):
    """Создание нового чата"""
    from core.app import get_container
    chat_service = get_container().get("chat_service")
    
    try:
        result = await chat_service.create_chat(
            user_id=user["sub"],
            ai_slug=request.ai_slug,
            role_slug=request.role_slug,
            title=request.title
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/send")
async def send_message(request: SendMessageRequest, user: dict = get_current_user()):
    """Отправка сообщения в чат"""
    from core.app import get_container
    chat_service = get_container().get("chat_service")
    
    try:
        result = await chat_service.send_message(
            chat_id=request.chat_id,
            user_id=user["sub"],
            content=request.content,
            use_tools=request.tools
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/poll")
async def poll_messages(
    chat_id: int,
    last_message_id: int = 0,
    limit: int = 50,
    user: dict = get_current_user()
):
    """Polling: проверка новых сообщений"""
    from core.app import get_container
    chat_service = get_container().get("chat_service")
    
    try:
        result = await chat_service.poll_messages(
            chat_id=chat_id,
            user_id=user["sub"],
            last_message_id=last_message_id,
            limit=limit
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/list")
async def list_chats(
    page: int = 1,
    limit: int = 20,
    user: dict = get_current_user()
):
    """Список чатов пользователя"""
    from core.app import get_container
    chat_service = get_container().get("chat_service")
    
    return await chat_service.get_user_chats(
        user_id=user["sub"],
        page=page,
        limit=limit
    )


@router.get("/history")
async def get_history(
    chat_id: int,
    page: int = 1,
    limit: int = 50,
    user: dict = get_current_user()
):
    """История сообщений чата"""
    from core.app import get_container
    chat_service = get_container().get("chat_service")
    
    try:
        return await chat_service.get_chat_history(
            chat_id=chat_id,
            user_id=user["sub"],
            page=page,
            limit=limit
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/rename")
async def rename_chat(request: RenameChatRequest, user: dict = get_current_user()):
    """Переименование чата"""
    from core.app import get_container
    chat_service = get_container().get("chat_service")
    
    success = await chat_service.rename_chat(
        chat_id=request.chat_id,
        user_id=user["sub"],
        title=request.title
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Чат не найден")
    
    return {"message": "Чат переименован"}


@router.delete("/clear")
async def clear_chat(chat_id: int, user: dict = get_current_user()):
    """Очистка сообщений чата"""
    from core.app import get_container
    chat_service = get_container().get("chat_service")
    
    success = await chat_service.clear_chat(chat_id, user["sub"])
    if not success:
        raise HTTPException(status_code=404, detail="Чат не найден")
    
    return {"message": "Чат очищен"}


@router.delete("/delete")
async def delete_chat(chat_id: int, user: dict = get_current_user()):
    """Удаление чата"""
    from core.app import get_container
    chat_service = get_container().get("chat_service")
    
    success = await chat_service.delete_chat(chat_id, user["sub"])
    if not success:
        raise HTTPException(status_code=404, detail="Чат не найден")
    
    return {"message": "Чат удалён"}
```

---

## 7. Миграция БД

```python
# src/core/database/migrations/Migration_005_Chat.py

from .Migration import Migration


class Migration_005_Chats(Migration):
    
    def get_name(self) -> str:
        return "005_create_chats_table"
    
    async def up(self, db):
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                ai_id       INTEGER NOT NULL,
                title       TEXT,
                role_slug   TEXT,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at  TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (ai_id) REFERENCES ai(id) ON DELETE SET NULL
            )
        """)
        await db.execute("CREATE INDEX idx_chats_user_id ON chats(user_id)")
        await db.execute("CREATE INDEX idx_chats_ai_id ON chats(ai_id)")
    
    async def down(self, db):
        await db.execute("DROP TABLE IF EXISTS chats")


class Migration_006_ChatMessages(Migration):
    
    def get_name(self) -> str:
        return "006_create_chat_messages_table"
    
    async def up(self, db):
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id         INTEGER NOT NULL,
                role            TEXT NOT NULL,
                content         TEXT,
                model_used      TEXT,
                provider_used   TEXT,
                tool_name       TEXT,
                tool_call_id    TEXT,
                tool_result     TEXT,
                metadata        TEXT DEFAULT '{}',
                is_streaming    INTEGER DEFAULT 0,
                created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
            )
        """)
        await db.execute("CREATE INDEX idx_chat_messages_chat_id ON chat_messages(chat_id)")
        await db.execute("CREATE INDEX idx_chat_messages_created_at ON chat_messages(created_at)")
    
    async def down(self, db):
        await db.execute("DROP TABLE IF EXISTS chat_messages")
```

---

## 8. Frontend: Модели и компоненты

### 8.1 ChatService (API)

```javascript
// src/core/services/ChatService.js

import { ApiService } from "./ApiService";

export class ChatService extends ApiService {
    
    // ─── Чаты ─────────────────────────────────────
    
    async createChat(aiSlug = "assistant", roleSlug = null, title = null) {
        return this.post("/api/chat/create", {
            ai_slug: aiSlug,
            role_slug: roleSlug,
            title: title,
        });
    }
    
    async getChats(page = 1, limit = 20) {
        return this.get(`/api/chat/list?page=${page}&limit=${limit}`);
    }
    
    async deleteChat(chatId) {
        return this.delete(`/api/chat/delete?chat_id=${chatId}`);
    }
    
    async renameChat(chatId, title) {
        return this.put("/api/chat/rename", { chat_id: chatId, title });
    }
    
    // ─── Сообщения ────────────────────────────────
    
    async sendMessage(chatId, content, tools = true) {
        return this.post("/api/chat/send", {
            chat_id: chatId,
            content: content,
            tools: tools,
        });
    }
    
    async pollMessages(chatId, lastMessageId = 0, limit = 50) {
        return this.get(
            `/api/chat/poll?chat_id=${chatId}&last_message_id=${lastMessageId}&limit=${limit}`
        );
    }
    
    async getHistory(chatId, page = 1, limit = 50) {
        return this.get(
            `/api/chat/history?chat_id=${chatId}&page=${page}&limit=${limit}`
        );
    }
    
    async clearChat(chatId) {
        return this.delete(`/api/chat/clear?chat_id=${chatId}`);
    }
}
```

### 8.2 ChatModel

```javascript
// src/core/pages/chatPage/ChatPageModel.js

import { ChatService } from "@/core/services/ChatService";

export class ChatPageModel {
    
    constructor() {
        this.chatService = new ChatService();
        
        // Данные
        this.chats = [];                  // Список чатов
        this.currentChatId = null;        // Текущий чат
        this.messages = [];               // Сообщения текущего чата
        this.lastMessageId = 0;           // ID последнего сообщения
        
        // Состояние
        this.loading = false;
        this.sending = false;
        this.error = null;
        
        // Polling
        this.pollTimer = null;
        this.pollInterval = 3000;         // 3 сек по умолчанию
        this.isProcessing = false;        // AI обрабатывает ответ
    }
    
    getPageTitle() {
        return "Чат";
    }
    
    // ─── Инициализация ─────────────────────────────
    
    async init() {
        await this.loadChats();
    }
    
    // ─── Чаты ─────────────────────────────────────
    
    async loadChats() {
        this.loading = true;
        try {
            const response = await this.chatService.getChats();
            if (response.isSuccess()) {
                this.chats = response.data.chats;
            }
        } catch (e) {
            this.error = e.message;
        } finally {
            this.loading = false;
        }
    }
    
    async createChat(aiSlug = "assistant") {
        const response = await this.chatService.createChat(aiSlug);
        if (response.isSuccess()) {
            await this.loadChats();
            await this.openChat(response.data.chat_id);
            return response.data;
        }
    }
    
    async openChat(chatId) {
        this.currentChatId = chatId;
        this.messages = [];
        this.lastMessageId = 0;
        
        // Загружаем историю
        const response = await this.chatService.getHistory(chatId);
        if (response.isSuccess()) {
            this.messages = response.data.messages;
            if (this.messages.length > 0) {
                this.lastMessageId = this.messages[this.messages.length - 1].id;
            }
        }
        
        // Запускаем polling
        this.startPolling();
    }
    
    async deleteChat(chatId) {
        await this.chatService.deleteChat(chatId);
        if (this.currentChatId === chatId) {
            this.stopPolling();
            this.currentChatId = null;
            this.messages = [];
        }
        await this.loadChats();
    }
    
    // ─── Сообщения ────────────────────────────────
    
    async sendMessage(content) {
        if (!this.currentChatId || !content.trim()) return;
        
        this.sending = true;
        this.isProcessing = true;
        
        try {
            // Добавляем сообщение пользователя в UI сразу
            this.messages.push({
                id: Date.now(), // Временный ID
                role: "user",
                content: content,
                created_at: new Date().toISOString()
            });
            
            // Отправляем на сервер
            const response = await this.chatService.sendMessage(
                this.currentChatId, content, true
            );
            
            if (!response.isSuccess()) {
                this.error = response.error;
                this.isProcessing = false;
            }
            // Ответ AI появится через polling
            
        } catch (e) {
            this.error = e.message;
            this.isProcessing = false;
        } finally {
            this.sending = false;
        }
    }
    
    // ─── Polling ──────────────────────────────────
    
    startPolling() {
        this.stopPolling();
        this._poll();
    }
    
    stopPolling() {
        if (this.pollTimer) {
            clearTimeout(this.pollTimer);
            this.pollTimer = null;
        }
    }
    
    async _poll() {
        if (!this.currentChatId) return;
        
        try {
            const response = await this.chatService.pollMessages(
                this.currentChatId,
                this.lastMessageId
            );
            
            if (response.isSuccess() && response.data.messages.length > 0) {
                const newMessages = response.data.messages;
                
                // Добавляем новые сообщения (избегаем дублей)
                const existingIds = new Set(this.messages.map(m => m.id));
                for (const msg of newMessages) {
                    if (!existingIds.has(msg.id)) {
                        this.messages.push(msg);
                    }
                }
                
                this.lastMessageId = response.data.last_message_id;
                
                // Проверяем, закончил ли AI отвечать
                const lastMsg = newMessages[newMessages.length - 1];
                if (lastMsg.role === "assistant") {
                    this.isProcessing = false;
                }
            }
        } catch (e) {
            console.error("Polling error:", e);
        }
        
        // Следующий poll (адаптивный интервал)
        const interval = this.isProcessing ? 1000 : this.pollInterval;
        this.pollTimer = setTimeout(() => this._poll(), interval);
    }
    
    // ─── Утилиты ──────────────────────────────────
    
    getCurrentChat() {
        return this.chats.find(c => c.id === this.currentChatId);
    }
    
    formatTime(dateStr) {
        if (!dateStr) return "";
        const d = new Date(dateStr);
        return d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
    }
}
```

### 8.3 Vue-компонент ChatPage

```vue
<!-- src/core/pages/chatPage/ChatPage.vue -->

<style scoped>
.chat_page {
    display: flex;
    height: calc(100vh - 60px);
    background: #f5f5f5;
}

/* ─── Sidebar ──────────────────────────── */

.chat_sidebar {
    width: 280px;
    background: #fff;
    border-right: 1px solid #e0e0e0;
    display: flex;
    flex-direction: column;
}

.sidebar_header {
    padding: 16px;
    border-bottom: 1px solid #e0e0e0;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.sidebar_header h3 {
    margin: 0;
    font-size: 16px;
}

.chat_list {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
}

.chat_item {
    padding: 12px;
    border-radius: 8px;
    cursor: pointer;
    margin-bottom: 4px;
    transition: background 0.2s;
}

.chat_item:hover {
    background: #f0f0f0;
}

.chat_item.active {
    background: #e8e4ff;
    color: #6c5ce7;
}

.chat_item_title {
    font-weight: 500;
    font-size: 14px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.chat_item_time {
    font-size: 11px;
    color: #999;
    margin-top: 4px;
}

/* ─── Main Chat Area ───────────────────── */

.chat_main {
    flex: 1;
    display: flex;
    flex-direction: column;
}

.chat_header {
    padding: 16px 20px;
    background: #fff;
    border-bottom: 1px solid #e0e0e0;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.chat_messages {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.message {
    max-width: 70%;
    padding: 12px 16px;
    border-radius: 12px;
    font-size: 14px;
    line-height: 1.5;
    animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.message_user {
    align-self: flex-end;
    background: #6c5ce7;
    color: white;
    border-bottom-right-radius: 4px;
}

.message_assistant {
    align-self: flex-start;
    background: #fff;
    border: 1px solid #e0e0e0;
    border-bottom-left-radius: 4px;
}

.message_system {
    align-self: center;
    background: transparent;
    color: #999;
    font-size: 12px;
    font-style: italic;
}

.message_tool {
    align-self: flex-start;
    background: #f8f9fa;
    border: 1px dashed #ddd;
    border-radius: 8px;
    font-family: monospace;
    font-size: 12px;
    max-width: 85%;
}

.message_meta {
    font-size: 11px;
    color: #999;
    margin-top: 6px;
}

.tool_name {
    color: #e67e22;
    font-weight: 600;
}

.tool_result {
    margin-top: 8px;
    padding: 8px;
    background: #fff;
    border-radius: 4px;
    max-height: 200px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-word;
}

/* ─── Input Area ───────────────────────── */

.chat_input_area {
    padding: 16px 20px;
    background: #fff;
    border-top: 1px solid #e0e0e0;
    display: flex;
    gap: 12px;
    align-items: flex-end;
}

.chat_input {
    flex: 1;
    padding: 12px 16px;
    border: 1px solid #ddd;
    border-radius: 12px;
    font-size: 14px;
    resize: none;
    max-height: 120px;
    font-family: inherit;
    transition: border-color 0.2s;
}

.chat_input:focus {
    outline: none;
    border-color: #6c5ce7;
}

.send_button {
    padding: 12px 24px;
    background: #6c5ce7;
    color: white;
    border: none;
    border-radius: 12px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.2s;
}

.send_button:hover:not(:disabled) {
    background: #5a4bd1;
}

.send_button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.processing_indicator {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    color: #999;
    font-size: 13px;
}

.processing_dot {
    width: 8px;
    height: 8px;
    background: #6c5ce7;
    border-radius: 50%;
    animation: pulse 1.4s infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 0.3; }
    50% { opacity: 1; }
}
</style>

<template>
    <div class="chat_page">
        <!-- Sidebar -->
        <div class="chat_sidebar">
            <div class="sidebar_header">
                <h3>💬 Чаты</h3>
                <button class="btn btn-primary btn-sm" @click="handleNewChat">
                    + Новый
                </button>
            </div>
            <div class="chat_list">
                <div 
                    v-for="chat in model.chats" 
                    :key="chat.id"
                    class="chat_item"
                    :class="{ active: chat.id === model.currentChatId }"
                    @click="model.openChat(chat.id)"
                >
                    <div class="chat_item_title">{{ chat.title || 'Диалог' }}</div>
                    <div class="chat_item_time">
                        {{ chat.message_count }} сообщ. · {{ model.formatTime(chat.last_message_at) }}
                    </div>
                </div>
            </div>
        </div>

        <!-- Main -->
        <div class="chat_main">
            <div class="chat_header" v-if="currentChat">
                <div>
                    <strong>{{ currentChat.title }}</strong>
                    <span style="color: #999; margin-left: 8px; font-size: 13px;">
                        {{ currentChat.ai_name }}
                    </span>
                </div>
                <div>
                    <button class="btn btn-sm" @click="handleClear">Очистить</button>
                    <button class="btn btn-sm btn-danger" @click="handleDelete">Удалить</button>
                </div>
            </div>

            <!-- Messages -->
            <div class="chat_messages" ref="messagesContainer">
                <div v-if="model.messages.length === 0 && !model.loading" class="empty_state">
                    <p>Начните диалог с AI ✨</p>
                </div>

                <div 
                    v-for="msg in model.messages" 
                    :key="msg.id"
                    class="message"
                    :class="'message_' + msg.role"
                >
                    <!-- User message -->
                    <template v-if="msg.role === 'user'">
                        {{ msg.content }}
                    </template>

                    <!-- Assistant message -->
                    <template v-if="msg.role === 'assistant'">
                        {{ msg.content }}
                        <div class="message_meta" v-if="msg.model_used">
                            🤖 {{ msg.model_used }}
                            <template v-if="msg.metadata?.generation_time_ms">
                                · {{ msg.metadata.generation_time_ms }}ms
                            </template>
                        </div>
                    </template>

                    <!-- Tool message -->
                    <template v-if="msg.role === 'tool'">
                        <span class="tool_name">🛠️ {{ msg.tool_name }}</span>
                        <div class="tool_result">{{ msg.content }}</div>
                    </template>

                    <!-- System message -->
                    <template v-if="msg.role === 'system'">
                        {{ msg.content }}
                    </template>
                </div>

                <!-- Processing indicator -->
                <div v-if="model.isProcessing" class="processing_indicator">
                    <div class="processing_dot"></div>
                    AI думает...
                </div>
            </div>

            <!-- Input -->
            <div class="chat_input_area" v-if="model.currentChatId">
                <textarea 
                    class="chat_input"
                    v-model="inputText"
                    @keydown.enter.exact="handleSend"
                    placeholder="Введите сообщение..."
                    rows="1"
                ></textarea>
                <button 
                    class="send_button"
                    @click="handleSend"
                    :disabled="!inputText.trim() || model.sending"
                >
                    {{ model.sending ? '...' : '→' }}
                </button>
            </div>
        </div>
    </div>
</template>

<script>
export default {
    name: "ChatPage",
    
    data() {
        return {
            inputText: "",
        };
    },
    
    computed: {
        layout() {
            return this.$layout;
        },
        model() {
            return this.layout.getPage("ChatPageModel");
        },
        currentChat() {
            return this.model?.getCurrentChat();
        }
    },
    
    async mounted() {
        if (!this.model) {
            // Регистрируем модель если ещё не зарегистрирована
            const { ChatPageModel } = await import("./ChatPageModel");
            this.layout.registerPage("ChatPageModel", new ChatPageModel());
        }
        await this.model.init();
    },
    
    beforeUnmount() {
        this.model?.stopPolling();
    },
    
    methods: {
        async handleSend() {
            if (!this.inputText.trim()) return;
            const text = this.inputText;
            this.inputText = "";
            
            await this.model.sendMessage(text);
            this.scrollToBottom();
        },
        
        async handleNewChat() {
            await this.model.createChat("assistant");
            this.scrollToBottom();
        },
        
        async handleClear() {
            if (confirm("Очистить все сообщения?")) {
                await this.model.clearChat(this.model.currentChatId);
            }
        },
        
        async handleDelete() {
            if (confirm("Удалить чат?")) {
                await this.model.deleteChat(this.model.currentChatId);
            }
        },
        
        scrollToBottom() {
            this.$nextTick(() => {
                const container = this.$refs.messagesContainer;
                if (container) {
                    container.scrollTop = container.scrollHeight;
                }
            });
        }
    },
    
    watch: {
        'model.messages.length'() {
            this.scrollToBottom();
        }
    }
}
</script>
```

---

## 9. Оптимизации polling

### 9.1 Адаптивный интервал

| Состояние | Интервал polling | Причина |
|-----------|-----------------|---------|
| AI обрабатывает | 1 сек | Быстрое получение ответа |
| Ожидание | 3 сек | Базовый интервал |
| Нет активности > 30 сек | 5 сек | Экономия ресурсов |
| Нет активности > 2 мин | 10 сек | Минимальная нагрузка |

### 9.2 Long Polling (опционально)

Если нужно минимизировать задержку без WebSocket:

```python
# Backend: Long Polling
@router.get("/long-poll")
async def long_poll(chat_id: int, last_message_id: int, user: dict = get_current_user()):
    """
    Long polling: сервер удерживает соединение до появления нового сообщения
    или таймаута (30 сек).
    """
    import asyncio
    timeout = 30  # секунд
    check_interval = 1  # секунда
    elapsed = 0
    
    while elapsed < timeout:
        # Проверяем новые сообщения
        messages = await chat_service.poll_messages(chat_id, user["sub"], last_message_id)
        if messages["messages"]:
            return messages
        
        await asyncio.sleep(check_interval)
        elapsed += check_interval
    
    # Таймаут — возвращаем пустой ответ
    return {"messages": [], "last_message_id": last_message_id, "has_more": False}
```

### 9.3 Кэширование

```python
# Использование ETag для условных запросов
@router.get("/poll")
async def poll_messages(..., request: Request):
    response = await chat_service.poll_messages(...)
    
    # ETag на основе last_message_id
    etag = f'"{response["last_message_id"]}"'
    
    # Если клиент уже имеет актуальные данные
    if request.headers.get("If-None-Match") == etag:
        return Response(status_code=304)
    
    result = JSONResponse(response)
    result.headers["ETag"] = etag
    result.headers["Cache-Control"] = "no-cache"
    return result
```

---

## 10. Требования к реализации

### 10.1 Приоритеты

| Приоритет | Задача | Описание |
|-----------|--------|----------|
| 🔴 Высокий | Миграции БД | Таблицы chats и chat_messages |
| 🔴 Высокий | ChatService | Основной сервис чата |
| 🔴 Высокий | API эндпоинты | send, poll, list, history |
| 🔴 Высокий | ChatPageModel | Модель фронтенда |
| 🔴 Высокий | ChatPage.vue | Компонент чата |
| 🟡 Средний | Agentic loop | Цикл tool calls |
| 🟡 Средний | Адаптивный polling | Интервал polling |
| 🟡 Средний | Отображение tool results | UI для результатов инструментов |
| 🟢 Низкий | Long polling | Удержание соединения |
| 🟢 Низкий | ETag кэширование | Оптимизация запросов |
| 🟢 Низкий | Поиск по чатам | Фильтрация |

### 10.2 Оценка трудозатрат

| Модуль | Оценка |
|--------|--------|
| Миграции БД | 1–2 часа |
| ChatService | 4–6 часов |
| API эндпоинты | 2–3 часа |
| ChatService.js (фронт) | 2–3 часа |
| ChatPageModel.js | 3–4 часа |
| ChatPage.vue | 4–6 часов |
| Agentic loop (tools) | 2–3 часа |
| Адаптивный polling | 1–2 часа |
| Тестирование | 2–3 часа |
| **ИТОГО** | **21–32 часа** |

### 10.3 Зависимости

- Существующая система авторизации (JWT)
- AI подсистема (providers, models, ai, ai_roles)
- MCP интеграция (MCPManager) — опционально
- Python 3.10+, FastAPI, SQLite/D1
- Vue 3 + Rollup

---

## 11. Пример работы (сценарий)

```
Пользователь: "Прочитай файл main.py и найди баг"
                    ↓
[User message → БД]
                    ↓
AI: "Сейчас прочитаю файл main.py"
                    ↓
[Assistant message → БД]
                    ↓
AI вызывает инструмент read_file(path="main.py")
                    ↓
[Tool message → БД] ← результат чтения файла
                    ↓
AI: "Нашёл баг в строке 42: ..."
                    ↓
[Assistant message → БД]
                    ↓
Клиент (polling) → GET /poll → Получает 3 новых сообщения
                    ↓
Отображает: 
  💬 "Сейчас прочитаю файл..."
  🛠️ read_file: [содержимое файла]
  🤖 "Нашёл баг в строке 42..."
```

---

## 12. Итог

Данное ТЗ описывает **онлайн-чат с AI** на основе **polling-механизма** вместо WebSocket. Основные архитектурные решения:

1. **Polling вместо WebSocket** — обеспечивает совместимость с Cloudflare Workers и простоту реализации. Адаптивный интервал (1–10 сек) балансирует между отзывчивостью и нагрузкой.

2. **Все сообщения в БД** — пользовательские, ответы AI, результаты инструментов (tools) хранятся в таблице `chat_messages` с role-based подходом.

3. **Agentic loop** — AI может вызывать инструменты несколько раз подряд. Каждый вызов и его результат сохраняется в БД как отдельное сообщение.

4. **Инкрементальный polling** — клиент запоминает `last_message_id` и получает только новые сообщения, минимизируя трафик.

5. **Гибридный подход** — для further оптимизации можно добавить Long Polling или SSE (Server-Sent Events) как альтернативу простому polling.

**Итоговая оценка:** ~21–32 часа на полную реализацию с рабочим чатом, отображением tool results и адаптивным polling.

---

**Последнее обновление:** 25 сентября 2026 года  
**Статус:** Готово к реализации  
**Ответственный:** Лея
