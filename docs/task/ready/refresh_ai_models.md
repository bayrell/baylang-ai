# Техническое задание: Добавление кнопки обновления моделей через API OpenAI

## Цель

Добавить функционал автоматического обновления списка моделей провайдера через кнопку "Обновить модели" в интерфейсе управления провайдерами.

## Задача

### 1. Изменения в интерфейсе (Frontend)

#### 1.1. Компонент `ProviderPage.bay`

Добавить кнопку "Обновить модели" в форму редактирования провайдера. Кнопку нужно разместить после config. Сделать как отдельный компонент.

Этот компонент должен содержать кнопку и сообщение результат api. По нажатию на кнопку должен быть вызван метод refreshModels модели.

**Файл:** `src/lib/Runtime.AI/bay/Cabinet/Components/Providers/ProviderPageModel.bay`

#### 1.2. Модель `ProviderPageModel.bay`
Добавить метод `refreshModels` для вызова API.

**Файл:** `src/lib/Runtime.AI/bay/Cabinet/Components/Providers/ProviderPageModel.bay`

Добавить импорт API (если еще не добавлен):
```baylang
use Runtime.AI.Cabinet.Api.ProviderRefreshApi;
```

Добавить метод:
```baylang
/**
 * Refresh models from API
 */
async void refreshModels()
{
    /* Вызов api cabinet.ai.provider frefresh*/
}
```

### 2. Изменения в API (Backend)

#### 2.1. Изменени API `ProviderSaveApi`

Добавить в ProviderSaveApi метод refresh. Использовать Runtime.Curl для отправки запроса

**Файл:** `src/lib/Runtime.AI/bay/Cabinet/Api/ProviderSaveApi.bay`

В ProviderConfig нужно добавить поле со список моделей. refresh должен использовать url и api key и обновлять этот список, а затем сохранить изменения в базу данных конфиг провайдера.

## Пример ответа API

Успешный ответ:
```json
{
  "success": true,
  "message": "Модели успешно обновлены",
  "data": {
    "id": 1
  }
}
```

Ошибка:
```json
{
  "success": false,
  "error": "Ошибка API OpenAI: ..."
}
```