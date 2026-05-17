# Улучшение Runtime.AI: QuestionService и отправка запросов в LLM

## План реализации

| № | Задача | Статус | Файл/Модуль |
|---|--------|--------|-------------|
| 1 | Миграция БД (изменение типа `content` на JSON) | ✅ Выполнено | SQL миграция (`Migration_2026_Patch.bay`) |
| 2 | Модель `ChatMessage` (DTO) | ✅ Выполнено | `src/lib/Runtime.AI/bay/Models/ChatMessage.bay` |
| 3 | Модель `BaseMessage` (базовый класс) | ✅ Выполнено | `src/lib/Runtime.AI/bay/Models/Messages/BaseMessage.bay` |
| 4 | Модель `TextMessage` (реализация) | ✅ Выполнено | `src/lib/Runtime.AI/bay/Models/Messages/TextMessage.bay` |
| 5 | Обновление `ProviderConfig` (базовый класс) | ✅ Выполнено | `src/lib/Runtime.AI/bay/Models/Config/ProviderConfig.bay` |
| 6 | Обновление `GeminiConfig` | ✅ Выполнено | `src/lib/Runtime.AI/bay/Models/Config/GeminiConfig.bay` |
| 7 | Обновление `OpenAIConfig` | ✅ Выполнено | `src/lib/Runtime.AI/bay/Models/Config/OpenAIConfig.bay` |
| 8 | Обновление `QuestionService` (init, loadChatHistory, buildPrompt) | ✅ Выполнено | `src/lib/Runtime.AI/bay/Services/QuestionService.bay` |
| 9 | Реализация `sendToLLM` через `Runtime.Curl` | ✅ Выполнено | `src/lib/Runtime.AI/bay/Services/QuestionService.bay` |
| 10 | Интеграция методов конфигурации в `QuestionService` | ✅ Выполнено | `src/lib/Runtime.AI/bay/Services/QuestionService.bay` |

## Цель
Реализовать загрузку истории сообщений, обновить структуру данных для поддержки мультимодальности (используя `Vector<BaseMessage>`), реализовать отправку запросов в LLM через `Runtime.Curl` в `QuestionService` и асинхронную обработку событий.

## Задача

### 1. Обновление структуры сообщений и моделей

#### 1.1. Миграция базы данных
Таблица `ai_chat_history` должна хранить `content` как JSON. Для поддержки истории чатов и мультимодальности структура JSON будет содержать массив объектов (DTO).

**Статус:** Выполнено в `Migration_2026_Patch.bay` (метод `update_chat_history_content_type`).

#### 1.2. Модель ChatMessage (DTO)
В папке `src/lib/Runtime.AI/bay/Models/` создана модель `ChatMessage`. Это Data Transfer Object, который хранит полную информацию о сообщении в чате, включая вектор вложенных сообщений (текст, изображения).

**Статус:** Выполнено. Реализация соответствует плану с использованием `Vector<BaseMessage>`. Добавлен метод `getData()` для форматирования под LLM.

#### 1.3. Модель BaseMessage
Базовый класс для сообщений, использующий поле `type` для определения конкретного класса (полиморфизм).

**Статус:** Выполнено. Реализован метод `getTypeName` для десериализации конкретных типов сообщений.

#### 1.4. Пример записи в БД
В поле `content` таблицы `ai_chat_history` хранится JSON массив.

**Статус:** Миграция обновляет существующие записи и изменяет тип поля на JSON.

### 2. Загрузка истории сообщений в QuestionService

`QuestionService` должен загружать историю из БД, конвертируя JSON из `ChatHistory` в `Vector<ChatMessage>`, и добавлять их в промпт.

#### 2.1. Обновление QuestionService
Файл `src/lib/Runtime.AI/bay/Services/QuestionService.bay` обновлен:
- Добавлен метод `loadChatHistory` для загрузки истории из БД.
- Метод `buildPrompt` собирает промпт, включая память, историю чата и текущее сообщение.
- Реализована логика создания сообщений через `createMessage`.

**Статус:** Выполнено.

### 3. Отправка сообщения через Runtime.Curl

Метод `sendToLLM` использует `Runtime.Curl` для взаимодействия с API провайдера. Учитываются особенности OpenAI и Gemini.

**Статус:** Выполнено. Метод `sendToLLM` реализован в `QuestionService`. Используется `provider_config.prepareBody` для формирования тела запроса и `Runtime.Curl` для отправки.

### 4. Обновление конфигурации провайдеров

Чтобы обеспечить гибкость обработки ответов разных LLM провайдеров, добавлены методы в классы конфигурации для извлечения текста ответа (reply_text) и формирования тела запроса (body).

#### 4.1. ProviderConfig (Базовый класс)
Добавлены виртуальные методы `getReplyText` и `prepareBody`.

**Статус:** Выполнено.

#### 4.2. GeminiConfig
Реализована специфическая логика для Gemini (формат запроса и ответа).

**Статус:** Выполнено.

#### 4.3. OpenAIConfig
Реализована специфическая логика для OpenAI (формат запроса и ответа).

**Статус:** Выполнено.

### 5. Интеграция в QuestionService

Модифицирован `QuestionService`, чтобы использовать методы конфигурации для парсинга ответов и построения тела запроса.

**Статус:** Выполнено. В `processMessage` используется `provider_config.getReplyText`, а в `sendToLLM` — `provider_config.prepareBody`.

### 6. Пример использования

```baylang
namespace App.Services;

use Runtime.AI.Services.QuestionService;

class ExampleService
{
    async void example()
    {
        QuestionService question_service = new QuestionService();
        question_service.android_id = 1;
        question_service.chat_id = 1;
        question_service.user_id = 1;
        
        await question_service.init();
        
        /* Отправка сообщения */
        await question_service.send("Привет, как дела?");
    }
}
```

### 7. Пример ответов API

#### OpenAI / OpenRouter
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gpt-3.5-turbo",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Привет! Я в порядке, спасибо. Чем могу помочь?"
      },
      "finish_reason": "stop"
    }
  ]
}
```

#### Google Gemini
```json
{
  "candidates": [
    {
      "content": {
        "parts": [
          {
            "text": "Привет! Я в порядке, спасибо. Чем могу помочь?"
          }
        ],
        "role": "model"
      },
      "finishReason": "STOP"
    }
  ]
}
```