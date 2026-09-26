# Техническое задание: Интеграция MCP серверов через переменные окружения

## 1. Описание текущей архитектуры

### 1.1 Console.py
- Основной файл консольного интерфейса ИИ-ассистента
- Реализован цикл ввода-вывода с историей сообщений
- Используется класс `Context` для хранения контекста диалога
- Класс `Provider` и его наследник `OpenRouter` для работы с LLM
- Функция `send_llm()` для отправки запросов к модели

### 1.2 MCPClient.py
- Клиент для подключения к MCP (Model Context Protocol) серверам
- Работает через stdin/stdout (stdio транспорт)
- Реализованы базовые методы: `initialize`, `list_tools`, `execute`
- Есть методы запуска и остановки сервера

## 2. Цели доработки

### 2.1 Основная цель
Добавить возможность динамического подключения нескольких MCP серверов через переменные окружения и использовать их инструменты в диалоге с ИИ.

### 2.2 Частные задачи
1. Конфигурирование MCP серверов через `.env` файл
2. Автоматическое подключение серверов при старте приложения
3. Интеграция инструментов MCP в системный промпт
4. Обработка вызовов инструментов во время диалога
5. Корректная обработка ошибок и переподключение

## 3. Требования к функциональности

### 3.1 Конфигурация через .env
Добавить в `.env` файл переменные для конфигурации MCP серверов:

```env
# Формат: MCP_SERVERS='имя_сервера:путь:аргументы;имя_сервера2:путь2:аргументы2'
MCP_SERVERS='filesystem:/usr/local/bin/mcp-filesystem:--root;/api/mcp-server:--verbose'

### 3.2 Класс MCPManager (новый)
Создать менеджер для управления несколькими MCP серверами:

```python
class MCPManager:
    def __init__(self):
        self.clients = {}  # {name: MCPClient}
        self.tools = {}    # {tool_name: client_name}
    
    def load_config(self, config_json):
        """Загрузка конфигурации из JSON строки"""
        
    def connect_all(self):
        """Подключение всех активных серверов"""
        
    def get_all_tools(self):
        """Получение списка всех инструментов со всех серверов"""
        
    def execute_tool(self, tool_name, arguments):
        """Выполнение инструмента по имени"""
        
    def disconnect_all(self):
        """Отключение всех серверов"""
```

### 3.3 Интеграция с Context
Изменить системный промпт для включения списка доступных инструментов:

```python
def getSystemPrompt():
    base_prompt = "Ты IT помощник для программистов"
    
    # Добавить информацию об инструментах MCP
    if mcp_manager:
        tools_description = get_tools_description(mcp_manager.get_all_tools())
        base_prompt += f"\n\nДоступные инструменты:\n{tools_description}"
    
    return base_prompt
```

### 3.4 Обработка вызовов инструментов
Модифицировать цикл диалога для обработки вызовов инструментов:

```python
# В цикле while True после получения response:
if response contains tool_call:
    tool_name = extract_tool_name(response)
    tool_args = extract_tool_args(response)
    
    try:
        result = mcp_manager.execute_tool(tool_name, tool_args)
        # Добавить результат в контекст
        context.add(TextMessage(TextMessage.ROLE_SYSTEM, 
            f"Результат инструмента {tool_name}: {result}"))
    except Exception as e:
        context.add(TextMessage(TextMessage.ROLE_SYSTEM, 
            f"Ошибка выполнения инструмента {tool_name}: {str(e)}"))
```

### 3.5 Обработка ошибок и восстановление
- Автоматическое переподключение при обрыве соединения
- Таймауты для операций с MCP серверами
- Логирование ошибок
- Graceful shutdown всех серверов при выходе

## 4. Изменения в файлах

### 4.1 MCPClient.py
1. Исправить баг в `send_message()` (используется `method` вместо `method_name`)
2. Добавить таймауты для операций ввода/вывода
3. Добавить проверку состояния процесса перед отправкой
4. Реализовать контекстный менеджер (`__enter__`, `__exit__`)
5. Добавить метод `is_connected()` для проверки статуса

### 4.2 Console.py
1. Добавить импорт `MCPManager`
2. Загрузить конфигурацию MCP из переменных окружения
3. Инициализировать `MCPManager` перед основным циклом
4. Модифицировать `getSystemPrompt()` для включения списка инструментов
5. Добавить обработку вызовов инструментов в основном цикле
6. Реализовать корректное завершение работы MCP серверов

### 4.3 .env файл
Добавить переменные конфигурации:

```env
# Включить/выключить MCP интеграцию
MCP_ENABLED=true

# Конфигурация серверов (JSON формат)
MCP_SERVERS_CONFIG='filesystem:/usr/local/bin/mcp-filesystem:--root;/api/mcp-server:--verbose'
```

## 5. Доработка MCPClient.py

### 5.1 Исправление критических багов
```python
# В методе send_message исправить:
# Было:
"method": method,
# Должно быть:
"method": method_name,
```

### 5.2 Добавление таймаутов
```python
import select

def send_message(self, method_name, params, timeout=30):
    # ... формирование запроса ...
    
    # Запись с таймаутом
    self.process.stdin.write(data)
    self.process.stdin.write("\n")
    self.process.stdin.flush()
    
    # Чтение с таймаутом
    ready, _, _ = select.select([self.process.stdout], [], [], timeout)
    if not ready:
        raise Exception("Timeout waiting for response")
    
    response_text = self.process.stdout.readline()
    # ... остальная обработка ...
```

### 5.3 Проверка состояния
```python
def is_connected(self):
    return self.process is not None and self.process.poll() is None
```

### 5.4 Контекстный менеджер
```python
def __enter__(self):
    self.connect()
    return self

def __exit__(self, exc_type, exc_val, exc_tb):
    self.stop_server()
    return False
```

## 6. Новый файл: src/ai/MCPManager.py

```python
import os
import json
from .MCPClient import MCPClient

class MCPManager:
    
    def __init__(self):
        self.clients = {}
        self.tools_cache = {}
    
    def load_from_env(self):
        """Загрузка конфигурации из переменных окружения"""
        config_data = os.getenv("MCP_SERVERS_CONFIG")
        if config_data:
            try:
                config = self.parse_config(config_data)
                self.load_config(config)
            except json.JSONDecodeError as e:
                print(f"Ошибка парсинга MCP конфигурации: {e}")
    
    def load_config(self, servers_config):
        """Загрузка конфигурации из списка словарей"""
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
    
    def get_all_tools(self):
        """Получение инструментов со всех серверов"""
        all_tools = {}
        
        for name, client in self.clients.items():
            try:
                if client.is_connected():
                    tools = client.list_tools()
                    if tools:
                        for tool in tools:
                            tool_key = f"{name}:{tool['name']}"
                            all_tools[tool_key] = {
                                "server": name,
                                "tool": tool
                            }
            except Exception as e:
                print(f"Ошибка получения инструментов с '{name}': {e}")
        
        return all_tools
    
    def execute_tool(self, full_tool_name, arguments):
        """Выполнение инструмента (формат: server:tool)"""
        parts = full_tool_name.split(":", 1)
        if len(parts) != 2:
            raise ValueError(f"Неверный формат имени инструмента: {full_tool_name}")
        
        server_name, tool_name = parts
        
        if server_name not in self.clients:
            raise ValueError(f"Сервер '{server_name}' не найден")
        
        client = self.clients[server_name]
        if not client.is_connected():
            client.connect()
        
        response = client.execute(tool_name, arguments)
        
        return response
    
    def disconnect_all(self):
        """Отключение всех серверов"""
        for name, client in self.clients.items():
            try:
                client.stop_server()
                print(f"MCP сервер '{name}' отключен")
            except Exception as e:
                print(f"Ошибка отключения MCP сервера '{name}': {e}")
```

## 7. Изменения в .env

```env
# Текущие переменные...
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL_NAME=model_name
SYSTEM_PROMPT=prompts/system.txt
CHAT_HISTORY_PATH=history/

# MCP Конфигурация
MCP_ENABLED=true
MCP_SERVERS_CONFIG=''
```

## 8. Требования к тестированию

### 8.1 Юнит-тесты
- Тестирование MCPManager с мок-клиентами
- Тестирование загрузки конфигурации
- Тестирование обработки ошибок

### 8.2 Интеграционные тесты
- Тестирование реального подключения к MCP серверу
- Тестирование выполнения инструментов
- Тестирование восстановления после ошибок

### 8.3 Тестовые сценарии
1. Подключение одного сервера
2. Подключение нескольких серверов
3. Вызов инструмента из диалога
4. Обработка ошибки подключения
5. Переподключение при обрыве
6. Корректное завершение работы

## 9. Приоритеты реализации

### Высокий приоритет
1. Исправление бага в MCPClient.py (method → method_name)
2. Создание MCPManager.py
3. Загрузка конфигурации из .env
4. Подключение серверов при старте

### Средний приоритет
5. Интеграция с системным промптом
6. Обработка вызовов инструментов
7. Таймауты и обработка ошибок

### Низкий приоритет
8. Автоматическое переподключение
9. Логирование
10. Юнит-тесты

## 10. Оценка трудозатрат

- Исправление багов в MCPClient.py: 1-2 часа
- Создание MCPManager.py: 3-4 часа
- Интеграция с console.py: 2-3 часа
- Тестирование: 2-3 часа
- **Итого: 8-12 часов**

## 11. Зависимости

- Python 3.8+
- библиотека `select` (стандартная)
- Доступ к MCP серверам для тестирования

## 12. Риски

1. **Производительность**: Чтение из stdout может блокировать поток
   - Решение: Использование select с таймаутами
   
2. **Стабильность соединения**: MCP серверы могут падать
   - Решение: Реализация переподключения и retry логики
   
3. **Совместимость**: Разные версии протокола MCP
   - Решение: Проверка версии при инициализации