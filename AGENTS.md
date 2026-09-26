# BayLang Cloud AGI

## О проекте

**BayLang Cloud AGI** — облачная AGI система с веб-интерфейсом, построенная на **FastAPI** (backend) и **Vue 3** (frontend). Проект разработан для запуска в **Docker-контейнерах** и **Cloudflare Workers** (serverless), с возможностью расширения на другие провайдеры.

Система интегрирует LLM через OpenRouter API и поддерживает **MCP (Model Context Protocol)** для расширения возможностей AI через внешние инструменты и плагины.

---

## Технологический стек

| Слой | Технология |
|------|-----------|
| **Backend** | Python 3, FastAPI, Uvicorn |
| **Frontend** | Vue 3 (Composition API + Options API), Rollup |
| **AI** | OpenRouter API (GPT, Claude, Llama, etc.) |
| **Интеграции** | MCP Protocol (Model Context Protocol) |
| **Сборка фронтенда** | Rollup + @vitejs/plugin-vue + SCSS |
| **Контейнеризация** | Docker (Node 24 + Python 3) |
| **Serverless** | Cloudflare Workers (Pyodide Python) |
| **Деплой** | build.sh → docker / browse / deploy / vue-shell |

---

## Архитектура: Модели и Компоненты

**Ключевой принцип проекта — разделение ответственности:**

> **Модели** хранят данные и бизнес-логику.
> **Vue-компоненты** отображают данные и обрабатывают пользовательские события.

Это не просто convention, а архитектурное решение. Модели являются автономными.units, которые можно переиспользовать, тестировать и подменять независимо от UI.

---

### Структура проекта

```
BayLang Cloud AGI/
├── Dockerfile                    # Multi-stage: Node 24 + Python 3
├── build.sh                      # Скрипт сборки (docker/browse/deploy/vue-shell)
├── AGENTS.md                     # Этот файл
├── src/
│   ├── core/                     # Backend ядро
│   │   ├── app.py               # FastAPI + DI Container
│   │   ├── container.py         # Dependency Injection контейнер
│   │   ├── config.py            # Конфигурация (Config / CloudflareConfig)
│   │   ├── routes.py            # API роуты
│   │   ├── ai/
│   │   │   └── MCPClient.py     # MCP протокол клиент
│   │   └── pages/
│   │       ├── Layout.vue       # Корневой layout компонент
│   │       └── LayoutModel.js   # Модель layout
│   ├── console.py               # Консольный ИИ-ассистент (CLI)
│   ├── main.py                  # Cloudflare Worker entry point
│   ├── server.py                # Локальный dev сервер (uvicorn)
│   ├── main.js                  # Vue entry point
│   ├── rollup.config.js         # Конфигурация Rollup сборки
│   └── package.json             # Node.js зависимости
└── docs/
    ├── auth.md                  # Техническое задание на авторизацию
    └── tech_spec_mcp_integration.md  # ТЗ на MCP интеграцию
```

---

### Dependency Injection (DI Container)

Проект использует простой DI-контейнер для управления зависимостями на стороне backend:

```python
# container.py
class Container:
    def __init__(self):
        self.instances = {}   # Singleton экземпляры
        self.registry = {}    # Фабрики

    def register(self, name, f):       # Transient
        self.registry[name] = {"f": f, "singleton": False}

    def singleton(self, name, f):      # Singleton
        self.registry[name] = {"f": f, "singleton": True}

    def get(self, name):               # Получить экземпляр
        ...
```

Регистрация контейнера в `app.py`:

```python
def register_container():
    container = Container()
    container.singleton("app", lambda container: FastAPI())
    container.singleton("template", lambda container: jinja2.Environment())
    container.singleton("config", lambda container: Config())
    return container
```

---

### Frontend: Vue 3 с Моделями

**Основная идея:** В Vue-компоненте хранятся **только обработчики событий** и **шаблон отображения**. Вся бизнес-логика, данные и API-вызовы живут в **моделях**.

#### Как это работает

1. **LayoutModel** — глобальная модель, доступная через `this.$layout` во всех компонентах.
2. **Страницные модели** (например `IndexPageModel`) — создаются для каждой страницы и регистрируются в LayoutModel.
3. **Компонент** получает модель через `computed` свойство и связывает данные с шаблоном.

#### Пример компонента

```vue
<style scoped>
.index_page {
    padding: 20px;
}
</style>

<template>
    <div class="index_page">
        <h1>{{ model.getPageTitle() }}</h1>
        <div v-for="item in model.items" :key="item.id">
            {{ item.name }}
        </div>
    </div>
</template>

<script>
export default {
    computed: {
        layout() {
            return this.$layout;
        },
        model() {
            return this.$layout.getPageModel("IndexPageModel");
        }
    }
}
</script>
```

#### Пример модели

```javascript
import { IndexPageApi } from "@/services/IndexPageApi";

export class IndexPageModel extends BaseModel {
    constructor() {
        super();
        this.api = new IndexPageApi();
        this.items = [];
    }

    getPageTitle() {
        return "Index page";
    }

    async init() {
        await this.loadItems();
    }

    async loadItems() {
        const response = await this.api.getItems();
        if (response.isSuccess()) {
            this.items = response.data.items;
        }
    }
}
```

#### Точка входа Vue

```javascript
// main.js
import { createApp, reactive } from 'vue'
import { LayoutModel } from './core/pages/LayoutModel.js'
import App from './core/App.vue'

const layout = new LayoutModel();

const app = createApp(App)
app.config.globalProperties.$layout = reactive(layout);

app.mount('.app_container')
```

---

## Деплой

Проект поддерживает два режима запуска:

### 1. Docker (классический сервер)

```bash
./build.sh docker    # Сборка Docker образа
./build.sh browse    # Запуск и открытие в браузере
```

- FastAPI раздаёт статику из `dist/` (собранный Vue)
- Uvicorn на порту 8000

### 2. Cloudflare Workers (serverless)

```bash
./build.sh deploy    # Деплой в Cloudflare
```

- Используется Pyodide для запуска Python в WASM
- Entry point: `src/main.py` → `WorkerEntrypoint`
- Конфиг подменяется на `CloudflareConfig`

---

## AI и MCP

### Консольный ассистент (`console.py`)

Быстрый CLI-прототип для тестирования LLM:

- Подключается к OpenRouter API
- Поддерживает системный промпт
- История контекста в сессии
- Сохранение истории в JSON

### MCP Client (`core/ai/MCPClient.py`)

Клиент для **Model Context Protocol** — стандарта для подключения внешних инструментов к AI:

- Транспорт: **stdio** (subprocess)
- Протокол: JSON-RPC 2.0
- Возможности:
  - `initialize` — инициализация соединения
  - `tools/list` — список доступных инструментов
  - `tools/call` — вызов инструмента

---

## Сборка фронтенда

Vue собирается через **Rollup** (не Webpack, не Vite):

```javascript
// rollup.config.js
{
    input: 'main.js',
    output: { file: 'dist/main.js', format: 'umd' },
    plugins: [
        alias({ entries: [{ find: "@", replacement: path.resolve(__dirname) }] }),
        vue(),
        commonjs(),
        scss({ fileName: "main.css" }),
        production && terser()
    ]
}
```

- `@` алиас указывает на `src/` директорию
- SCSS компилируется в `dist/main.css`
- В production: сжатие + удаление console.log

---

## Правила разработки

### Backend (Python / FastAPI)

- Использовать DI-контейнер для управления зависимостями
- Регистрировать маршруты через `APIRouter`
- Конфигурация через `Config` / `CloudflareConfig`
- Не хранить состояние в глобальных переменных (кроме контейнера)

### Frontend (Vue 3)

- **Использовать Options API** (не `<script setup>`)
- **Вся бизнес-логика — в моделях** (классы)
- В компоненте — только обработчики событий и шаблон
- Модели регистрируются в `LayoutModel` и доступны через `this.$layout`
- API-вызовы делать через сервисы (`*Api.js`)
- Использовать `@` алиас для импортов

### Общее

- Не дублировать логику между моделью и компонентом
- Модели должны быть тестируемыми независимо от UI
- Использовать反應式 свойства Vue через `reactive()` в main.js
