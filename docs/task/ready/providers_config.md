# Улучшение Runtime.AI: Провайдеры и Модели

## Цель

Расширить функциональность Runtime.AI для поддержки множества LLM-провайдеров, добавить управление API-ключами и реализовать полиморфизм моделей.

## План выполнения

| № | Задача | Статус |
|---|--------|--------|
| 1 | Создать DTO модели для конфигурации провайдеров (ProviderConfig, OpenAIConfig, OpenRouterConfig, GeminiConfig) | ✅ |
| 2 | Создать реестр конфигурации провайдеров (ConfigRegistry.bay) | ✅ |
| 3 | Создать DTO модели для параметров модели (ModelParams, OpenRouterParams) | ✅ |
| 4 | Обновить UI интерфейс для управления провайдерами (ProviderPageModel) | ✅ |
| 5 | Обновить UI интерфейс для управления моделями (ModelPageModel) | ✅ |
| 6 | Создать динамический компонент для отображения конфигурации (ConfigForm) | ✅ |
| 7 | Интегрировать компонент в страницы провайдеров и моделей | ✅ |

## Список созданных файлов

| Файл | Описание | Статус |
|------|----------|--------|
| `src/lib/Runtime.AI/bay/Models/Config/ProviderConfig.bay` | Базовый класс конфигурации провайдера | ✅ |
| `src/lib/Runtime.AI/bay/Models/Config/OpenAiConfig.bay` | Конфигурация OpenAI | ✅ |
| `src/lib/Runtime.AI/bay/Models/Config/OpenRouterConfig.bay` | Конфигурация OpenRouter | ✅ |
| `src/lib/Runtime.AI/bay/Models/Config/GeminiConfig.bay` | Конфигурация Gemini | ✅ |
| `src/lib/Runtime.AI/bay/Models/Config/ModelParams.bay` | Параметры модели | ✅ |
| `src/lib/Runtime.AI/bay/Models/Config/OpenRouterParams.bay` | Параметры OpenRouter | ✅ |
| `src/lib/Runtime.AI/bay/Providers/ConfigRegistry.bay` | Реестр конфигурации провайдеров | ✅ |
| `src/lib/Runtime.AI/bay/Cabinet/Components/Blocks/ConfigForm.bay` | Динамический компонент формы конфигурации | ✅ |
| `src/lib/Runtime.AI/bay/Cabinet/Components/Providers/ProviderPageModel.bay` | Модель страницы провайдеров | ✅ |
| `src/lib/Runtime.AI/bay/Cabinet/Components/Models/ModelPageModel.bay` | Модель страницы моделей | ✅ |

## Задача

### 1. Добавление типов провайдеров и управление настройками

**Проблема**: В текущей реализации нет явной конфигурации для разных типов провайдеров (OpenAI, OpenRouter, Gemini и т.д.). API ключи и специфичные параметры не управляются через UI/API.

**Решение**:

#### 1.1. Обновление модели Provider

Файл `src/lib/Runtime.AI/bay/Models/Provider.bay` содержит необходимые поля:
- `type` - тип провайдера (openai, openrouter, gemini)
- `config` - JSON конфигурация провайдера

#### 1.2 Создание реестра конфигурации провайдеров

Файл `src/lib/Runtime.AI/bay/Providers/ConfigRegistry.bay` содержит перечисление всех моделей конфигурации провайдеров и метод `getConfigByType(type_name)` для получения конфигурации по типу.

#### 1.3. Создание DTO моделей для конфигурации провайдеров

Папка `src/lib/Runtime.AI/bay/Models/Config/` содержит модели:
- **ProviderConfig** - базовый класс конфигурации провайдера
- **OpenAIConfig** - конфигурация OpenAI
- **OpenRouterConfig** - конфигурация OpenRouter
- **GeminiConfig** - конфигурация Gemini

Каждый класс содержит метод `formFields()`, который возвращает описание полей формы для динамического отображения.

#### 1.4. Обновление модели Model

Файл `src/lib/Runtime.AI/bay/Models/Model.bay` уже содержит необходимые поля:
- `provider_id` - ID провайдера
- `model_name` - Имя для API (gpt-4, gpt-3.5-turbo)
- `config` - JSON конфигурации модели
- `temperature`, `max_tokens`, `top_p` - параметры модели

#### 1.5. Создание DTO модели для параметров модели

Созданы файлы:
- `src/lib/Runtime.AI/bay/Models/Config/ModelParams.bay` - базовые параметры модели
- `src/lib/Runtime.AI/bay/Models/Config/OpenRouterParams.bay` - параметры OpenRouter

#### 1.6. Создание динамической формы для параметров провайдера и модели

Создан компонент `src/lib/Runtime.AI/bay/Cabinet/Components/Blocks/ConfigForm.bay`, который:
- Принимает массив fields с описанием полей
- Принимает модель model с данными
- Динамически отображает поля в зависимости от их типа (Input, Select, Textarea)
- Поддерживает привязку данных (двустороннюю)

### 2. Обновление UI интерфейса

#### ProviderPageModel

Обновлен `src/lib/Runtime.AI/bay/Cabinet/Components/Providers/ProviderPageModel.bay`:
- Добавлена инициализация типов провайдеров через ConfigRegistry
- Добавлено поле `providerConfig` для хранения конфигурации выбранного типа
- Добавлен метод `onTypeChange()` для обработки изменения типа провайдера
- Добавлен динамический компонент конфигурации в form_fields

#### ModelPageModel

Обновлен `src/lib/Runtime.AI/bay/Cabinet/Components/Models/ModelPageModel.bay`:
- Добавлено поле `providerConfig` для хранения конфигурации выбранного провайдера
- Добавлен метод `onProviderTypeChange()` для обработки изменения провайдера
- Добавлен динамический компонент конфигурации в form_fields
- Обновлен метод `loadProviders()` для загрузки типа провайдера вместе с опциями

### 3. Пример данных

#### Пример провайдера OpenAI:

```json
{
  "name": "OpenAI",
  "type": "openai",
  "slug": "openai",
  "config": {
    "api_key": "sk-...",
    "base_url": "https://api.openai.com/v1",
  }
}
```

#### Пример провайдера OpenRouter:

```json
{
  "name": "OpenRouter",
  "type": "openrouter",
  "slug": "openrouter",
  "config": {
    "api_key": "sk-...",
    "base_url": "https://openrouter.ai/api/v1",
  }
}
```

#### Пример модели:

```json
{
  "name": "GPT-4",
  "provider_id": 1,
  "model_name": "gpt-4",
  "temperature": 70,
  "max_tokens": 4096,
  "top_p": 100,
  "config": {
    "response_format": "text",
    "stop": []
  }
}
```

### 4. Особенности реализации

1. **Динамическое отображение форм**: Компонент ConfigForm автоматически отображает поля в зависимости от типа компонента (Input, Select, Textarea).

2. **Полиморфизм конфигураций**: Каждый тип провайдера (OpenAI, OpenRouter, Gemini) имеет свой класс конфигурации, который наследуется от ProviderConfig и переопределяет методы `getType()`, `getUrl()` и `formFields()`.

3. **Интеграция с ConfigRegistry**: Все типы провайдеров регистрируются в ConfigRegistry, что позволяет динамически получать конфигурацию по типу.

4. **Обновление формы при изменении типа**: При изменении типа провайдера или модели автоматически обновляются поля конфигурации в форме редактирования.