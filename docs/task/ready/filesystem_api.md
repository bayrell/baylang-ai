# API для файловой системы

## Описание задачи

Нужно разработать API для файловой системы. Файлы хранятся в базе данных, а бинарные в S3 хранилище. Также они находятся в chat_group, при этом один файл может находиться в разных группах и в одной тоже. Требуется реализовать поддержку иерархии и версий. Использовать модуль Runtime.AI.

Требования:
- Нужно создать FileSaveApi и FileSearchApi, которые наследуются от SaveApi и SearchApi. Также должно быть Api для работы с версиями
- Создать FileService и юнит тесты

---

## Архитектура решения

### Структура БД (3 таблицы)

#### `files` — хранилище файлов и папок

| Поле | Тип | Описание |
|------|-----|----------|
| id | bigint, AI, PK | Уникальный идентификатор |
| name | string | Имя файла/папки |
| slug | string | URL-safe идентификатор |
| file_type | enum('file','folder') | Тип: файл или папка |
| mime_type | string | MIME-тип (для файлов) |
| storage_type | enum('database','s3') | Где хранится контент |
| content | text | Содержимое (для текстовых файлов в БД) |
| s3_key | string | Ключ в S3 (для бинарных файлов) |
| size | bigint | Размер в байтах |
| hash | string | SHA-256 хеш контента |
| is_archived | bool | В архиве ли файл |
| is_latest | bool | Является ли последней версией |
| metadata | json | Дополнительные метаданные |
| gmtime_add | datetime | Дата создания (авто) |
| gmtime_edit | datetime | Дата изменения (авто) |

#### `file_items` — привязка файлов к чат-группам и иерархия

| Поле | Тип | Описание |
|------|-----|----------|
| id | bigint, AI, PK | Уникальный идентификатор |
| file_id | bigint, FK → files.id | Ссылка на файл |
| chat_group_id | bigint, FK → ai_chat_groups.id | Чат-группа |
| parent_id | bigint, nullable, FK → file_items.id | Родительская папка (null = корень) |
| is_symlink | bool | Является ли симлинком |
| symlink_source_id | bigint, nullable, FK → file_items.id | Источник симлинка |
| sort_order | int | Порядок сортировки |
| gmtime_add | datetime | Дата создания (авто) |
| gmtime_edit | datetime | Дата изменения (авто) |

> Один файл может быть в нескольких chat_group и даже несколько раз в одной группе (через разные parent_id или как симлинки).

#### `file_versions` — версионирование файлов

| Поле | Тип | Описание |
|------|-----|----------|
| id | bigint, AI, PK | Уникальный идентификатор |
| file_id | bigint, FK → files.id | Ссылка на файл |
| file_item_id | bigint, FK → file_items.id | Конкретная привязка в группе |
| version_number | int | Номер версии (1, 2, 3...) |
| content | text | Контент версии |
| s3_key | string | Ключ S3 для бинарных версий |
| hash | string | SHA-256 хеш |
| size | bigint | Размер |
| gmtime_add | datetime | Дата создания версии |

---

## Ключевые решения

### Иерархия
- Иерархия реализована через `parent_id` в таблице `file_items`, что позволяет одному файлу находиться в разных местах (разных папках / группах).
- Рекурсивное построение дерева через `WITH RECURSIVE` SQL-запросы.

### Версии
- Каждое изменение контента файла создаёт новую запись в `file_versions`.
- Восстановление версии — запись нового контента в `content` и инкремент `version_number`.
- Поле `is_latest` в `files` указывает на актуальную версию.

### Хранение
- Текстовые файлы (`.md`, `.txt`, `.json`, `.csv`, `.html`, `.xml`, `.log`) хранятся в БД (`storage_type = 'database'`).
- Бинарные файлы (`.pdf`, `.docx`, `.xlsx`, `.png`, `.jpg`, .`zip` и т.д.) хранятся в S3 (`storage_type = 's3'`).

### Связь с ChatGroup
- Файлы не имеют собственной таблицы групп — они привязываются к существующим `chat_group` из модуля Cabinet через таблицу `file_items`.
- Один файл может быть привязан к нескольким чат-группам одновременно.
- Поддержка симлинков (`is_symlink`) для перекрёстных ссылок.

---

## Файлы, созданные / изменённые

### Новые файлы БД (Runtime.AI):
- `src/lib/Runtime.AI/bay/Database/File.bay`
- `src/lib/Runtime.AI/bay/Database/FileItem.bay`
- `src/lib/Runtime.AI/bay/Database/FileVersion.bay`
- `src/lib/Runtime.AI/bay/Database/Migrations/Migration_2026_FileSystem.bay`

### Новые сервисы:
- `src/lib/Runtime.AI/bay/Services/FileService.bay`

### Новые модели (DTO):
- `src/lib/Runtime.AI/bay/Models/FileItem.bay`

### Изменённые файлы:
- `src/lib/Runtime.AI/bay/Database/ModuleDescription.bay` — добавлены entity для File, FileItem, FileVersion
- `src/lib/Runtime.AI/bay/ModuleDescription.bay` — добавлены API и Database entities