# Техническое задание: Реализация инструментов (Tools) для LLM в QuestionService

## 1. Введение

### 1.1. Цель
Реализовать поддержку инструментов (Tools) в `QuestionService` для взаимодействия с Large Language Models (LLM), поддерживающих вызов функций (например, OpenAI Function Calling). Это позволит LLM запрашивать выполнение внешних действий (например, поиск информации, управление памятью, вызов API) и получать результаты обратно в контекст диалога.

### 1.2. Задачи
1.  Создать базовый класс `BaseTool` для определения инструментов.
2.  Реализовать `ToolRegistry` как `BaseProvider` для регистрации и хранения доступных инструментов.
3.  Создать DTO для описания инструментов и их вызовов.
4.  Интегрировать инструменты в `QuestionService`:
	*   Получение реестра инструментов через провайдер `@.provider`.
	*   Отправка доступных инструментов в запросе к LLM.
	*   Обработка вызовов инструментов от LLM через отдельные функции `sendWithTools` и `executeTools`.
	*   Добавление сообщений с результатами выполнения в промпт (историю сообщений).
	*   Возврат результатов выполнения в LLM.
5.  Обновить структуру хранения сообщений для поддержки вызовов функций.

## 2. Архитектура

### 2.1. Структура проекта

```
src/lib/Runtime.AI/
├── bay/
│   ├── Models/
│   │   ├── ToolItem.bay          # DTO определения инструмента (для LLM)
│   │   └── ToolResponse.bay      # DTO ответа инструмента (в LLM)
│   ├── Services/
│   │   ├── ToolRegistry.bay      # Реестр инструментов (BaseProvider)
│   │   └── QuestionService.bay   # (Обновленный)
│   ├── Tools/
│   │   ├── BaseTool.bay          # Базовый класс инструмента
```


### 2.2. Компоненты

#### 2.2.1. BaseTool
Абстрактный класс для определения инструмента. Каждый конкретный инструмент (например, `GetMemoryTool`, `SearchNoteTool`) наследуется от `BaseTool`.

**Методы:**
- `getName()`: Возвращает имя инструмента (уникальное).
- `getDescription()`: Описание для LLM.
- `getParameters()`: JSON Schema параметров инструмента.
- `execute(QuestionService service, Map params)`: Асинхронный метод выполнения логики. Возвращает `Map` (результат).
- `getMessage(Map params)`: Сообщение пользователю.

**Пример:**
```baylang
namespace Runtime.AI.Tools;

use Runtime.BaseObject;
use Runtime.AI.Services.QuestionService;
use Runtime.AI.Tools.ToolResult;

class MemoryTool extends BaseObject
{
	pure string getName() => "memory";
	pure string getDescription() => "Получить содержимое памяти пользователя";
	pure Map getParameters() => {
		"type": "object",
		"properties": {},
	};

	async ToolResult execute(QuestionService service, Map params)
	{
		ToolResult result = new ToolResult;
		result.success = true;
		result.message = "Result";
		return result;
	}
}
```

#### 2.2.2. ToolRegistry (BaseProvider)
Сервис, управляющий списком доступных инструментов, реализующий интерфейс `BaseProvider`.

**Методы:**
- `init()`: Инициализация и регистрация доступных инструментов.
- `register(BaseTool tool)`: Регистрация инструмента.
- `get(string name)`: Получение инструмента по имени.
- `getAll()`: Получение всех инструментов.
- `getDefinitions()`: Получение списка определений для отправки в LLM.

#### 2.2.3. DTO Модели

**ToolItem** (для LLM):
Содержит описание инструмента в формате, которая возвращает LLM.
- `id`: String
- `function`: Map
  - `name`: String
  - `arguments`: String
- `item`: BaseTool

**ToolResponse** (в LLM):
Содержит результат выполнения инструмента для отправки обратно LLM.
- `id`: String
- `name`: String
- `answer`: String

### 2.3. Интеграция с QuestionService

`QuestionService` должен быть расширен для работы с инструментами.

1.  **Инициализация**: `QuestionService` получает `ToolRegistry` через провайдер `@.provider`.
2.  **Формирование запроса**:
	*   Метод `sendToLLM` должен включать список инструментов в тело запроса (поле `tools`).
	*   Сообщения в промпте должны поддерживать роль `tool` (для результатов выполнения).
3.  **Обработка ответа**:
	*   В `processMessage` вызывается метод `sendWithTools`, который управляет циклом взаимодействия с LLM (пока есть вызовы инструментов).
	*   Метод `executeTools` отвечает за выполнение логики инструментов и добавление результатов в историю сообщений (промпт).
	*   Если вызовов нет, обрабатывается текстовый ответ.

### 2.4. Обновление моделей сообщений

Модель `ChatMessage` должна поддерживать роль `tool`.

```baylang
/* В ChatMessage.bay */
const string ROLE_TOOL = "tool";

/* В getData() методе */
string role = "system";
if (this.role == static::ROLE_ANDROID) role = "assistant";
else if (this.role == static::ROLE_USER) role = "user";
else if (this.role == static::ROLE_TOOL) role = "tool";
```

Также необходимо обновить `BaseMessage` и создать `ToolMessage` для хранения результатов выполнения инструментов, если это необходимо для структуры данных, хотя OpenAI часто использует роль `tool` в стандартном сообщении.

## 3. Реализация

### 3.1. Создание DTO

1.  **ToolResponse.bay**:
```baylang
namespace Runtime.AI.Models;

use Runtime.BaseDTO;
use Runtime.Serializer.ObjectType;
use Runtime.Serializer.StringType;

class ToolResponse extends BaseDTO
{
	string id = "";
	string name = "";
	string answer = "";

	static void serialize(ObjectType rules)
	{
		parent(rules);
		rules.addType("id", new StringType());
		rules.addType("name", new StringType());
		rules.addType("answer", new StringType());
	}
}
```

### 3.2. Создание BaseTool и ToolRegistry

1.  **BaseTool.bay**:
```baylang
namespace Runtime.AI.Tools;

use Runtime.BaseObject;

abstract class BaseTool extends BaseObject
{
	pure string getName();
	pure string getDescription();
	pure Map getParameters();
	async ToolResponse execute(Map args);
}
```

2.  **ToolRegistry.bay**:
```baylang
namespace Runtime.AI.Services;

use Runtime.BaseProvider;
use Runtime.AI.Services.Tools.BaseTool;

class ToolRegistry extends BaseProvider
{
	Map<string, BaseTool> tools = {};

	void init()
	{
		parent();
		/* Регистрация инструментов при инициализации провайдера */
		/* this.register(new GetTimeTool()); */
	}

	void register(BaseTool tool)
	{
		this.tools.set(tool.getName(), tool);
	}

	BaseTool get(string name)
	{
		return this.tools.get(name);
	}

	Vector<BaseTool> getAll()
	{
		return this.tools.transition(BaseTool (BaseTool tool) => tool);
	}

	Vector<Map> getDefinitions()
	{
		return this.getAll().map(Map (BaseTool tool) => {
			"name": tool.getName(),
			"description": tool.getDescription(),
			"parameters": tool.getParameters(),
		});
	}
}
```

### 3.3. Интеграция в QuestionService

1.  **Получение ToolRegistry**:
`QuestionService` получает инстанс `ToolRegistry` через провайдер `@.provider`.
```baylang
ToolRegistry toolRegistry = @.provider("Runtime.AI.Services.ToolRegistry");
```

2.  **Обновление sendToLLM**:
Добавить поле `tools` в тело запроса, если инструменты доступны.
```baylang
async Map sendToLLM()
{
	/* ... существующий код ... */
	Map body = this.provider_config.prepareBody(
		ModelDTO::create(this.model.all()), messages
	);

	/* Добавление инструментов */
	Vector<Map> tools = this.toolRegistry.getDefinitions();
	if (tools.count() > 0)
	{
		body.set("tools", tools);
		// Для OpenAI: tool_choice: "auto" или конкретное имя
		body.set("tool_choice", "auto");
	}

	/* ... отправка запроса ... */
}
```

3.  **Обработка вызовов инструментов (sendWithTools и executeTools)**:
В `processMessage` добавить логику обработки `tool_calls`, разбитую на функции. Используется цикл `while` с переменной `next_loop` для обработки последовательных вызовов инструментов.
```baylang
async void processMessage(string message)
{
	try
	{
		await this.buildPrompt(message);
		
		/* Запуск цикла обработки инструментов */
		await this.sendWithTools();
	}
	catch (RuntimeException e)
	{
		await this.sendError(e);
	}
	finally
	{
		await this.sendEvent(new ChatEvent{
			"chat_id": this.chat_id,
			"kind": ChatEvent::KIND_STOP,
		});
	}
}

async void sendWithTools()
{
	bool next_loop = true;
	while (next_loop)
	{
		Map llm_response = await this.sendToLLM();

		string reply_text = this.provider_config.getReplyText(llm_response);

		/* Сохранение обычного ответа LLM (если есть) */
		if (reply_text)
		{
			ChatMessage reply_message = this.createMessage(
				ChatMessage::ROLE_ANDROID, reply_text
			);
			await this.saveMessage(reply_message);
			await this.sendEvent(new MessageEvent{
				"chat_id": this.chat_id,
				"message": reply_message,
			});
		}
		
		Vector<ToolItem> tools = this.provider_congig.getTools(llm_response);
		
		/* Проверка на наличие вызовов инструментов */
		if (tools and tools.count() > 0)
		{
			/* Выполнение инструментов и добавление результатов в промпт */
			await this.executeTools(tools);
			
			/* Продолжить цикл для отправки результатов обратно LLM */
			next_loop = true;
		}
		else
		{
			/* Обычный ответ, цикл завершается */
			next_loop = false;
		}
		
		rtl::wait(this.model.delay);
	}
}

async void executeTools(Vector<ToolItem> tools)
{
	ChatMessage message = new ChatMessage();
	message.role = ChatMessage::ROLE_ANDROID;
	message.addTools(tools);
	
	/* Save message */
	await this.saveMessage(message);
	
	for (Map data in tools)
	{
		ToolItem tool = ToolItem::create(data);
		tool.item = this.toolRegistry.get(tool.getName());
		if (tool)
		{
			ToolResponse result = await tool.execute(tool.getParams());
			
			/* Создание сообщения с результатом */
			ChatMessage message = new ChatMessage();
			message.role = ChatMessage::ROLE_TOOL;
			message.addToolResponse(tool, result);
			
			/* Сохранение в историю (добавление в промпт) */
			await this.saveMessage(message);
		}
	}
}
```
*Примечание: Рекурсивный вызов `sendWithTools` может привести к бесконечному циклу, если LLM постоянно вызывает инструменты. Рекомендуется добавить счетчик вызовов или лимит итераций.*

## Список файлов для создания/изменения

1.  `src/lib/Runtime.AI/bay/Tools/BaseTool.bay` (Новый)
4.  `src/lib/Runtime.AI/bay/Tools/ToolResponse.bay` (Новый)
5.  `src/lib/Runtime.AI/bay/Services/ToolRegistry.bay` (Новый, реализует BaseProvider)
7.  `src/lib/Runtime.AI/bay/Models/ChatMessage.bay` (Изменение: добавление роли `tool`)
8.  `src/lib/Runtime.AI/bay/Services/QuestionService.bay` (Изменение: интеграция инструментов, методы sendWithTools и executeTools)
```
