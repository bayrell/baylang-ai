# Техническое задание: Доработка QuestionService — обработка ошибок и защита LLM-запросов

## 1. Введение

### 1.1. Цель
Улучшить обработку ошибок в `QuestionService`, добавить механизм повторных попыток (fallback) при ошибках API LLM и обеспечить отображение ошибок на фронтенде через веб-сокеты.

### 1.2. Задачи
1.  Добавить механизм fallback с ограничением количества попыток и задержкой между ними.
2.  Улучшить обработку ошибок API (HTTP 429, 500, таймауты и т.д.).
3.  Обеспечить отправку детализированных ошибок на фронтенд через веб-сокеты.
4.  Реализовать отображение ошибок на фронтенде в интерфейсе чата.

## 2. Архитектура

### 2.1. Структура изменений

```
src/lib/Runtime.AI/
├── bay/
│   ├── Services/
│   │   ├── QuestionService.bay   # (Обновленный)
│   │   └── ...
```

### 2.2. Компоненты

#### 2.2.1. Механизм fallback в sendToLLM

Добавить параметры конфигурации:
- `max_retries` — максимальное количество повторных попыток (по умолчанию 3)
- `retry_delay` — задержка между попытками в миллисекундах (по умолчанию 1000)

**Логика:**
1. При отправке запроса в LLM перехватывать ошибки API.
2. При ошибке 429 (Too Many Requests) или 500 (Internal Server Error) выполнять повторную попытку.
3. Увеличивать задержку экспоненциально (backoff): `retry_delay * retry_count`.
4. После исчерпания попыток выбрасывать исключение.

**Пример реализации:**

```baylang
/* В QuestionService.bay */
int max_retries = 3;
int retry_delay = 1000;

async Map sendToLLM()
{
	int retry_count = 0;
	
	while (retry_count <= this.max_retries)
	{
		try
		{
			/* ... существующий код отправки запроса ... */
			Map body = this.provider_config.prepareBody(
				ModelDTO::create(this.model.all()), messages, tool_definitions
			);
			
			Curl curl = new Curl();
			string api_url = rs::removeLastSlash(this.provider_config.getUrl()) ~ "/chat/completions";
			
			curl.url = api_url;
			curl.method = "POST";
			curl.headers = {
				"Content-Type": "application/json",
				"Authorization": "Bearer " ~ this.provider_config.getApiKey()
			};
			curl.post = body;
			
			string response_body = await curl.send();
			
			if (curl.isSuccess())
			{
				Map result = rtl::jsonDecode(response_body);
				return result;
			}
			else
			{
				/* Повторная попытка только для определенных ошибок */
				int status_code = curl.getStatusCode();
				if (status_code == 429 or status_code >= 500)
				{
					retry_count++;
					if (retry_count <= this.max_retries)
					{
						/* Экспоненциальная задержка */
						int delay = this.retry_delay * retry_count;
						rtl::wait(delay);
						continue;
					}
				}
				
				/* Для других ошибок выбрасываем исключение */
				throw new RuntimeException("API Error: " ~ response_body);
			}
		}
		catch (RuntimeException e)
		{
			if (retry_count >= this.max_retries)
			{
				throw e;
			}
			retry_count++;
		}
	}
	
	throw new RuntimeException("Max retries exceeded");
}
```

## 3. Реализация

### 3.1. Обновление QuestionService

1.  Добавить параметры `max_retries` и `retry_delay`.
2.  Реализовать механизм повторных попыток в `sendToLLM`.
3.  Обновить метод `sendError` для отправки детализированной информации.
