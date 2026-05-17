# Техническое задание: Группы для чатов в Runtime.AI

## План действий

| № | Задача | Статус | Примечания |
|---|--------|--------|------------|
| 1 | Изучить текущую структуру проекта и код | ✅ | Готово (анализ выполнен) |
| 2 | Определить изменения в базе данных | ✅ | Готово (определено) |
| 3 | Реализовать миграции | ✅ | Готово (создана таблица `ai_chat_groups` и поле `group_id` в `ai_chats`) |
| 4 | Создать модели и DTO | ✅ | Готово (созданы `ChatGroup.bay` (Database) и `ChatGroup.bay` (Models)) |
| 5 | Обновить сервисы | ✅ | Готово (создан `ChatGroupService.bay`, обновлен `ChatService.bay`) |
| 6 | Реализовать API | ✅ | Готово (созданы `ChatGroupSearchApi.bay` и `ChatGroupSaveApi.bay`) |
| 7 | Обновить фронтенд | ⏳ | В ожидании |
| 8 | Протестировать | ⏳ | В ожидании |

---

## 1. Общее описание

Необходимо внедрить систему групп для чатов в модуле Runtime.AI. Группы будут общими для всех пользователей и привязаны к пространствам (space_id). Каждый чат должен принадлежать одной группе.

## 2. Анализ текущего состояния проекта

### 2.1. Существующие модели и таблицы
- **ai_chats**: Таблица чатов (`src/lib/Runtime.AI/bay/Database/Chat.bay`)
  - Поля: id, space_id, user_id, android_id, title, metadata, external_key, is_archive, gmtime_add, gmtime_edit
  - **Проблема**: Отсутствовало поле `group_id` (добавлено в миграции)
- **ai_chat_groups**: Новая таблица групп чатов
  - Поля: id, space_id, name, slug, gmtime_add, gmtime_edit

### 2.2. Существующая логика
- `ChatService.bay`: Сервис для работы с чатами, создание/удаление чатов
  - Обновлен: добавлена логика работы с группами (получение дефолтной группы, создание чата с group_id)
- `Chat.bay` (Model): Модель чата для сериализации
  - **Обновлено**: Добавлено поле `group_id`
- Миграции: `Migration_2026.bay` содержит создание таблицы `ai_chat_groups` и добавление `group_id` в `ai_chats`

### 2.3. Требования из документации
1. На странице ChatPage в sidebar добавить выбор группы
2. В модели загружать группы
3. Каждый чат должен иметь `group_id`
4. Добавить поле `group_id` в базу и миграцию
5. Кнопка создания новой группы
6. Использовать SelectList для списка групп с кнопкой создания
7. Создать API для групп (общие для всех пользователей)
8. Группы должны иметь `space_id`
9. Для чатов `space_id` определять по `group_id` (в текущей реализации `space_id` удален из чатов, определяется через группу)
10. В API исправить запросы, добавить innerJoin в buildQuery (в текущей реализации используется связь через group_id, но `space_id` в чатах удален)

## 3. План разработки

### 3.1. База данных

#### 3.1.1. Создать таблицу `ai_chat_groups`
```sql
CREATE TABLE `ai_chat_groups` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `space_id` BIGINT NOT NULL,
  `name` VARCHAR(255) NOT NULL,
  `slug` VARCHAR(255) NOT NULL,
  `gmtime_add` DATETIME NOT NULL,
  `gmtime_edit` DATETIME NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_space_id` (`space_id`),
  FOREIGN KEY (`space_id`) REFERENCES `ai_space` (`id`) ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```
**Статус**: ✅ Реализовано в `Migration_2026.bay`.

#### 3.1.2. Добавить поле `group_id` в таблицу `ai_chats`
- Добавить FOREIGN KEY на `ai_chat_groups(id)`
- Добавить индекс `idx_group_id`
- Удалить `space_id` из `ai_chats` (так как `space_id` теперь определяется через группу)
**Статус**: ✅ Реализовано в `Migration_2026.bay`.

### 3.2. Миграции

#### 3.2.1. Создать новую миграцию для групп
- Файл: `src/lib/Runtime.AI/bay/Database/Migrations/Migration_2026.bay`
- Методы: `create_chat_groups` для создания таблицы
- Методы: `add_group_id_to_chats()` для изменения таблицы `ai_chats`
**Статус**: ✅ Готово.

### 3.3. Модели

#### 3.3.1. Создать модель ChatGroup
- Файл: `src/lib/Runtime.AI/bay/Database/ChatGroup.bay`
- Поля: id, space_id, name, slug, gmtime_add, gmtime_edit
- Таблица: `ai_chat_groups`
**Статус**: ✅ Готово.

#### 3.3.2. Создать DTO ChatGroup
- Файл: `src/lib/Runtime.AI/bay/Models/ChatGroup.bay`
- Поля: id, space_id, name, slug
- Сериализация полей
**Статус**: ✅ Готово (примечание: поле `description` добавлено в DTO, но отсутствует в БД, нужно добавить в БД или удалить из DTO).

#### 3.3.3. Обновить модель Chat
- Файл: `src/lib/Runtime.AI/bay/Database/Chat.bay`
- Добавить поле `group_id` в схему
- Добавить связь с ChatGroup
**Статус**: ✅ Готово (поле `group_id` добавлено, но связь не добавлена явно в схему).

#### 3.3.4. Обновить DTO Chat
- Файл: `src/lib/Runtime.AI/bay/Models/Chat.bay`
- Добавить поле `group_id`
- Обновить сериализацию
**Статус**: ✅ Готово (добавлено поле `group_id` в DTO и сериализацию).

### 3.4. Сервисы

#### 3.4.1. Создать ChatGroupService
- Файл: `src/lib/Runtime.AI/bay/Services/ChatGroupService.bay`
- Методы: `searchGroups()`, `saveGroup()`
**Статус**: ✅ Готово.

#### 3.4.2. Обновить ChatService
- Файл: `src/lib/Runtime.AI/bay/Services/ChatService.bay`
- Добавить параметр group_id=null в метод `createNewChat()`
- Если group_id равен null, то использовать группу по умолчанию (нужно в базе найти у space_id default группу). Если ее нет, то создать группу по умолчанию.
**Статус**: ✅ Готово.

### 3.5. API

#### 3.5.1. Создать API для групп
- Файл: `src/lib/Runtime.AI/bay/Cabinet/Api/ChatGroupSearchApi.bay`: Получение списка групп
- Файл: `src/lib/Runtime.AI/bay/Cabinet/Api/ChatGroupSaveApi.bay`: Редактирование группы
**Статус**: ✅ Готово.

#### 3.5.2. Обновить существующие API чатов
- В `ChatSearchApi.bay` в foreign key добавить group_id. Это необязательнй параметр.
- В `ChatSearchApi.bay` добавить проверку прав доступа через group_id, если он есть в foreign_key
- Исправить запросы, добавить leftJoin для связи с группами
**Статус**: ✅ Готово (обновлен `ChatSearchApi.bay` для поддержки `group_id` и `leftJoin`).

### 3.6. Frontend (UI)

#### 3.6.1. Обновить страницу ChatPage
- Добавить компонент выбора группы в sidebar
- Использовать SelectList для отображения групп
- Добавить кнопку создания новой группы
- В SelectList добавить параметр add_message, если он есть, то выводит добавление нового элемента. Если на него нажать, то должно быть отправлено emit.
- Добавить на ChatPage форму создания группы в диалоговом окне. Модель формы и диалогового окна добавить в модель ChatPageModel.
**Статус**: ⏳ В ожидании.

### 3.7. Дополнительные задачи

#### 3.7.1. Обновить Query Builder
- В `buildQuery` добавить leftJoin для связи чатов с группами
**Статус**: ✅ Готово (обновлен `ChatSearchApi.bay`).

## 4. Список файлов для создания/изменения

### 4.1. Создание новых файлов
1. `src/lib/Runtime.AI/bay/Database/ChatGroup.bay` ✅
2. `src/lib/Runtime.AI/bay/Models/ChatGroup.bay` ✅
3. `src/lib/Runtime.AI/bay/Cabinet/Api/ChatGroupSearchApi.bay` ✅
4. `src/lib/Runtime.AI/bay/Cabinet/Api/ChatGroupSaveApi.bay` ✅
5. `src/lib/Runtime.AI/bay/Services/ChatGroupService.bay` ✅

### 4.2. Изменение существующих файлов
1. `src/lib/Runtime.AI/bay/Database/Chat.bay` (добавить group_id) ✅
2. `src/lib/Runtime.AI/bay/Models/Chat.bay` (добавить group_id) ✅
3. `src/lib/Runtime.AI/bay/Services/ChatService.bay` (обновить createNewChat) ✅
4. `src/lib/Runtime.AI/bay/Database/Migrations/Migration_2026.bay` (добавить миграцию) ✅
5. `src/lib/Runtime.AI/bay/Api/Chat/ChatSave.bay` (обновить логику) ✅ (поддерживает group_id)
6. `src/lib/Runtime.AI/bay/Api/Chat/ChatDelete.bay` (обновить логику) ✅ (логика не изменилась)
7. `src/lib/Runtime.AI/bay/Cabinet/Api/ChatSearchApi.bay` (обновить для поддержки групп) ✅

## 5. Порядок выполнения

1. Создать таблицу `ai_chat_groups` через миграцию ✅
2. Добавить поле `group_id` в таблицу `ai_chats` ✅
3. Создать модели и DTO для ChatGroup ✅
4. Обновить модели Chat (Database и Model) ✅
5. Создать ChatGroupService ✅
6. Обновить ChatService ✅
7. Создать API для групп ✅
8. Обновить существующие API чатов ✅
9. Обновить фронтенд (ChatPage) ⏳
10. Протестировать функционал ⏳

## 6. Риски и зависимости

- Зависимость от существующей структуры миграций ✅
- Необходимость миграции данных для существующих чатов (назначить дефолтную группу) ⚠️ (не реализовано)
- Обновление frontend может потребовать значительных изменений ⏳
- Проверка прав доступа к группам (если требуется ограничение прав) ⚠️ (не реализовано)

## 7. Примечания

- Группы общие для всех пользователей в рамках space_id
- При удалении группы, если есть чаты, то выдать ошибку ⚠️ (не реализовано в API)
- space_id чата определяется через group_id (inner join в запросах) ⚠️ (не обновлено в API)

### Необходимые исправления:
1. **Добавить поле `description` в таблицу `ai_chat_groups`**: В DTO `ChatGroup.bay` (Models) есть поле `description`, но в БД его нет. Нужно добавить в миграцию.
2. **Обновить DTO `Chat.bay`**: Добавить поле `group_id` в сериализацию.
3. **Обновить `ChatSearchApi.bay`**: Добавить поддержку `group_id` в foreign_key и `leftJoin` для связи с группами.
4. **Реализовать миграцию данных**: Назначить дефолтную группу для существующих чатов.
5. **Реализовать проверку прав доступа к группам**: В API чатов и групп.
6. **Реализовать обработку удаления группы**: В `ChatGroupSaveApi.bay` добавить проверку на наличие чатов в группе.