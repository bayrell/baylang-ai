# Техническое задание: API для команд файловой системы

**Дата:** 2026-06-22
**Модуль:** `Runtime.AI.Cabinet.Components.Chat.Commands`
**API:** `FileSaveApi.bay` (`ai.file`)
**Сервис:** `FileService.bay`

---

## 1. Цель

Добавить API-методы для команд файлового дерева, которые ещё не реализованы, и исправить существующие баги.

---

## 2. Анализ текущего состояния

### 2.1. Список команд

| Команда | API метод | Статус |
|---------|-----------|--------|
| CreateFolderCommand | `ai.file.create_folder` | ✅ Есть, но с багом |
| CreateFileCommand | `ai.file.save` | ✅ Работает |
| DeleteCommand | `ai.file.delete` | ✅ Есть, но с багом |
| RenameCommand | `ai.file.rename` | ❌ Не реализован |
| CopyCommand | (клиентская логика) | ✅ Работает |
| CutCommand | (клиентская логика) | ✅ Работает |
| PasteCommand (copy) | `ai.file.copy` | ❌ Не реализован |
| PasteCommand (cut) | `ai.file.move` | ❌ Не реализован |
| ReloadCommand | `ai.file.list` | ✅ Работает |

### 2.2. Требуемые API-методы

| Метод | Файл API | Статус |
|-------|----------|--------|
| `create_folder` | `FileSaveApi.bay` | ❌ Баг: не возвращает item |
| `delete` | `FileSaveApi.bay` | ❌ Баг: не удаляет дочерние элементы папки |
| `rename` | `FileSaveApi.bay` | ❌ Отсутствует |
| `move` | `FileSaveApi.bay` | ❌ Отсутствует |
| `copy` | `FileSaveApi.bay` | ❌ Отсутствует |

---

## 3. Исправление багов

### 3.1. Баг: `mkdirByPath` не возвращает FileItem

**Проблема:** В `actionCreateFolder()` результат `mkdirByPath` не сохраняется и не возвращается клиенту.

**Текущий код:**
```bay
@ApiMethod{ "name": "create_folder" }
async void actionCreateFolder()
{
    this.filterData();
    await this.initService();
    int group_id = this.data.get("group_id");
    string path = this.data.get("path");
    await this.service.mkdirByPath(path, group_id);  // ← результат теряется
    this.success();
}
```

**Исправленный код:**
```bay
@ApiMethod{ "name": "create_folder" }
async void actionCreateFolder()
{
    this.filterData();
    await this.initService();
    int group_id = this.data.get("group_id");
    string path = this.data.get("path");

    Map result = await this.service.mkdirByPath(path, group_id);
    this.result.data.set("item", result.get("file_item").getData());
    this.success();
}
```

**Файл:** `src/lib/Runtime.AI/bay/Api/File/FileSaveApi.bay`
**Метод:** `actionCreateFolder()`

---

### 3.2. Баг: Удаление папки не удаляет дочерние элементы

**Проблема:** `actionDelete()` удаляет только саму папку (FileItem), но не удаляет дочерние файлы и подпапки. В результате в таблице `ai_files` остаются orphaned записи.

**Текущий код:**
```bay
@ApiMethod{ "name": "delete" }
async void actionDelete()
{
    this.filterData();
    await this.initService();
    int group_id = this.data.get("group_id");
    string path = this.data.get("path");
    await this.service.deleteFileByPath(path, group_id);
    this.success();
}
```

**Решение:** Добавить метод `deleteFolderRecursive` в `FileService.bay`, который:
1. Получает список всех дочерних элементов через `listDirByItemId`
2. Удаляет каждый элемент (с очисткой orphaned файлов)
3. Удаляет саму папку

**Новый метод в FileService.bay:**
```bay
/**
 * Delete folder and all its children recursively.
 *
 * @param string path - folder path
 * @param int chat_group_id - chat group ID
 */
async void deleteFolderByPath(string path, int chat_group_id)
{
    FileItem folder = await this.findFileItemByPath(path, chat_group_id);
    if (folder == null)
    {
        throw new ApiError(new ItemNotFound("FileItem"));
    }

    int folder_id = folder.get("id");

    /* Get all child items (recursive) */
    Vector children = await this.listDirByItemId(
        folder_id, true, 0, chat_group_id
    );

    /* Delete children in reverse order (deepest first) */
    for (int i = children.count() - 1; i >= 0; i--)
    {
        Map child = children.get(i);
        int child_file_id = child.get("file_id");

        /* Soft-delete the child file item */
        FileItem childItem = await this.fileItemRelation.findById(
            child.get("id")
        );
        if (childItem)
        {
            await childItem.delete();

            /* Cleanup orphaned file if it's a file (not a folder) */
            if (child_file_id > 0)
            {
                await this.cleanupOrphanedFile(child_file_id);
            }
        }
    }

    /* Delete the folder itself */
    int folder_file_id = folder.get("file_id");
    await folder.delete();

    if (folder_file_id > 0)
    {
        await this.cleanupOrphanedFile(folder_file_id);
    }
}
```

**Метод `actionDelete` (обновлённый):**
```bay
@ApiMethod{ "name": "delete" }
async void actionDelete()
{
    this.filterData();
    await this.initService();

    int group_id = this.data.get("group_id");
    string path = this.data.get("path");

    /* Check if path is a folder */
    bool is_folder = await this.service.isFolder(path, group_id);

    if (is_folder)
    {
        await this.service.deleteFolderByPath(path, group_id);
    }
    else
    {
        await this.service.deleteFileByPath(path, group_id);
    }

    this.success();
}
```

**Файлы:**
- `src/lib/Runtime.AI/bay/Services/FileService.bay` — новый метод `deleteFolderByPath()`
- `src/lib/Runtime.AI/bay/Api/File/FileSaveApi.bay` — обновлённый `actionDelete()`

---

## 4. Новые API-методы

### 4.1. Метод `rename` — Переименование файла/папки

**Вызов из фронтенда (RenameCommand.bay):**
```bay
ApiResult result = await this.layout.sendApi({
    "api_name": "ai.file",
    "method_name": "rename",
    "data":
    {
        "foreign_key": { "space_id": model.group.space_id },
        "group_id": model.group.id,
        "path": model.getPath(this.item_path),
        "new_name": this.dialog.value,
    }
});
```

**Параметры:**

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| group_id | int | Да | ID чат-группы |
| path | string | Да | Текущий путь к файлу/папке |
| new_name | string | Да | Новое имя |

**Ответ:**
```json
{
    "data": {
        "item": { "id": 123, "file_name": "new_name.txt", ... }
    }
}
```

**Реализация в FileService.bay:**
```bay
/**
 * Rename a file or folder.
 *
 * @param string path - current path
 * @param string new_name - new name
 * @param int chat_group_id - chat group ID
 * @return FileItem - renamed item
 */
async FileItem renameItemByPath(
    string path, string new_name, int chat_group_id
)
{
    FileItem item = await this.findFileItemByPath(path, chat_group_id);
    if (item == null)
    {
        throw new ApiError(new ItemNotFound("FileItem"));
    }

    /* Update name and slug */
    item.set("file_name", new_name);
    item.set("slug", this.generateSlug(new_name));
    await item.save();

    return item;
}
```

**Реализация в FileSaveApi.bay:**
```bay
/**
 * Action rename - Rename a file or folder
 *
 * @param group_id int - required
 * @param path string - required
 * @param new_name string - required
 */
@ApiMethod{ "name": "rename" }
async void actionRename()
{
    this.filterData();
    await this.initService();

    int group_id = this.data.get("group_id");
    string path = this.data.get("path");
    string new_name = this.data.get("new_name");

    FileItem item = await this.service.renameItemByPath(
        path, new_name, group_id
    );

    this.result.data.set("item", item.getData());
    this.success();
}
```

**Файлы:**
- `src/lib/Runtime.AI/bay/Services/FileService.bay` — новый метод `renameItemByPath()`
- `src/lib/Runtime.AI/bay/Api/File/FileSaveApi.bay` — новый метод `actionRename()`

---

### 4.2. Метод `move` — Перемещение файла/папки

**Вызов из фронтенда (PasteCommand.bay):**
```bay
ApiResult result = await this.layout.sendApi({
    "api_name": "ai.file",
    "method_name": "move",
    "data":
    {
        "foreign_key": { "space_id": model.group.space_id },
        "group_id": model.group.id,
        "source_path": cut_command.cutted_item_path_string,
        "target_path": model.getPath(item_path),
    }
});
```

**Параметры:**

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| group_id | int | Да | ID чат-группы |
| source_path | string | Да | Текущий путь к файлу/папке |
| target_path | string | Да | Целевой путь (папка назначения) |

**Ответ:**
```json
{
    "data": {
        "item": { "id": 123, "parent_id": 456, ... }
    }
}
```

**Реализация в FileService.bay:**
```bay
/**
 * Move a file or folder to a new parent.
 *
 * @param string source_path - current path of the item
 * @param string target_path - target folder path
 * @param int chat_group_id - chat group ID
 * @return FileItem - moved item
 */
async FileItem moveItemByPath(
    string source_path, string target_path, int chat_group_id
)
{
    FileItem item = await this.findFileItemByPath(source_path, chat_group_id);
    if (item == null)
    {
        throw new ApiError(new ItemNotFound("FileItem"));
    }

    int item_id = item.get("id");

    /* Resolve target parent_id */
    int new_parent_id = 0;
    if (target_path != "" and target_path != "/")
    {
        FileItem targetFolder = await this.findFileItemByPath(
            target_path, chat_group_id
        );
        if (targetFolder == null)
        {
            throw new ApiError(new ItemNotFound("Target folder"));
        }
        new_parent_id = targetFolder.get("id");
    }

    /* Prevent moving a folder into itself */
    if (item.get("file_type") == static::FILE_TYPE_FOLDER)
    {
        bool is_inside = await this.isItemInside(item_id, new_parent_id);
        if (is_inside)
        {
            throw new ApiError(new RuntimeException(
                "Cannot move a folder into itself or its subfolder"
            ));
        }
    }

    /* Update parent_id */
    item.set("parent_id", new_parent_id);
    await item.save();

    return item;
}
```

**Реализация в FileSaveApi.bay:**
```bay
/**
 * Action move - Move a file or folder to a new location
 *
 * @param group_id int - required
 * @param source_path string - required
 * @param target_path string - required
 */
@ApiMethod{ "name": "move" }
async void actionMove()
{
    this.filterData();
    await this.initService();

    int group_id = this.data.get("group_id");
    string source_path = this.data.get("source_path");
    string target_path = this.data.get("target_path");

    FileItem item = await this.service.moveItemByPath(
        source_path, target_path, group_id
    );

    this.result.data.set("item", item.getData());
    this.success();
}
```

**Файлы:**
- `src/lib/Runtime.AI/bay/Services/FileService.bay` — новый метод `moveItemByPath()`
- `src/lib/Runtime.AI/bay/Api/File/FileSaveApi.bay` — новый метод `actionMove()`

---

### 4.3. Метод `copy` — Копирование файла/папки

**Вызов из фронтенда (PasteCommand.bay):**
```bay
ApiResult result = await this.layout.sendApi({
    "api_name": "ai.file",
    "method_name": "copy",
    "data":
    {
        "foreign_key": { "space_id": model.group.space_id },
        "group_id": model.group.id,
        "source_path": copy_command.copied_item_path_string,
        "target_path": model.getPath(item_path),
    }
});
```

**Параметры:**

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| group_id | int | Да | ID чат-группы |
| source_path | string | Да | Путь к оригиналу |
| target_path | string | Да | Целевой путь (папка назначения) |

**Ответ:**
```json
{
    "data": {
        "item": { "id": 789, "file_name": "copy.txt", "parent_id": 456, ... }
    }
}
```

**Реализация в FileService.bay:**
```bay
/**
 * Copy a file or folder to a new parent.
 * For files: creates a new File + FileItem with same content.
 * For folders: creates a new folder + recursively copies children.
 *
 * @param string source_path - path of the item to copy
 * @param string target_path - target folder path
 * @param int chat_group_id - chat group ID
 * @return FileItem - copied item
 */
async FileItem copyItemByPath(
    string source_path, string target_path, int chat_group_id
)
{
    FileItem sourceItem = await this.findFileItemByPath(
        source_path, chat_group_id
    );
    if (sourceItem == null)
    {
        throw new ApiError(new ItemNotFound("FileItem"));
    }

    /* Resolve target parent_id */
    int target_parent_id = 0;
    if (target_path != "" and target_path != "/")
    {
        FileItem targetFolder = await this.findFileItemByPath(
            target_path, chat_group_id
        );
        if (targetFolder == null)
        {
            throw new ApiError(new ItemNotFound("Target folder"));
        }
        target_parent_id = targetFolder.get("id");
    }

    /* Check for name conflict and generate unique name */
    string new_name = sourceItem.get("file_name");
    string slug = this.generateSlug(new_name);
    FileItem existing = await this.findFileItemBySlug(
        target_parent_id, slug, chat_group_id
    );
    if (existing != null)
    {
        new_name = this.generateUniqueName(
            new_name, target_parent_id, chat_group_id
        );
    }

    /* Copy file or folder */
    if (sourceItem.get("file_type") == static::FILE_TYPE_FOLDER)
    {
        return await this.copyFolder(
            sourceItem, target_parent_id, new_name, chat_group_id
        );
    }
    else
    {
        return await this.copyFile(
            sourceItem, target_parent_id, new_name, chat_group_id
        );
    }
}


/**
 * Copy a file (creates new File + FileItem)
 */
async FileItem copyFile(
    FileItem sourceItem, int target_parent_id,
    string new_name, int chat_group_id
)
{
    int source_file_id = sourceItem.get("file_id");

    if (source_file_id > 0)
    {
        /* Load source file */
        File sourceFile = await this.findFile(source_file_id);
        if (sourceFile == null)
        {
            throw new ApiError(new ItemNotFound("Source file"));
        }

        /* Create new file with same content */
        File newFile = await this.createFileRecord(
            new_name, sourceFile.get("content")
        );
        await newFile.save();

        /* Create file item */
        FileItem newItem = this.createFileItem(
            newFile.get("id"), chat_group_id,
            target_parent_id, new_name
        );
        newItem.set("file_type", static::FILE_TYPE_FILE);
        await newItem.save();

        return newItem;
    }

    /* File with no backing file record */
    FileItem newItem = this.createFileItem(
        0, chat_group_id, target_parent_id, new_name
    );
    newItem.set("file_type", static::FILE_TYPE_FILE);
    await newItem.save();

    return newItem;
}


/**
 * Copy a folder and all its children recursively
 */
async FileItem copyFolder(
    FileItem sourceItem, int target_parent_id,
    string new_name, int chat_group_id
)
{
    /* Create the new folder */
    FileItem newFolder = await this.createFolder(
        new_name, target_parent_id, chat_group_id
    );

    /* Get all children of the source folder */
    int source_id = sourceItem.get("id");
    Vector children = await this.listDirByItemId(
        source_id, true, 0, chat_group_id
    );

    /* Build a map of parent_id → children for efficient lookup */
    Map<int, Vector> childrenByParent = {};
    for (Map child in children)
    {
        int pid = child.get("parent_id");
        if (not childrenByParent.has(pid))
        {
            childrenByParent.set(pid, []);
        }
        childrenByParent.get(pid).push(child);
    }

    /* BFS copy */
    Map<int, int> idMap = {};
    idMap.set(source_id, newFolder.get("id"));

    Vector queue = [];
    queue.push({
        "source_parent_id": source_id,
        "target_parent_id": newFolder.get("id"),
    });

    while (queue.count() > 0)
    {
        Map current = queue.first();
        queue.remove(0);

        int source_parent_id = current.get("source_parent_id");
        int target_parent_id = current.get("target_parent_id");

        Vector childrenList = childrenByParent.get(source_parent_id, []);
        for (Map child in childrenList)
        {
            string child_name = child.get("file_name");
            string child_slug = this.generateSlug(child_name);

            /* Check for name conflict */
            FileItem existing = await this.findFileItemBySlug(
                target_parent_id, child_slug, chat_group_id
            );
            if (existing != null)
            {
                child_name = this.generateUniqueName(
                    child_name, target_parent_id, chat_group_id
                );
            }

            if (child.get("file_type") == static::FILE_TYPE_FOLDER)
            {
                /* Create folder */
                FileItem newChildFolder = await this.createFolder(
                    child_name, target_parent_id, chat_group_id
                );
                idMap.set(child.get("id"), newChildFolder.get("id"));

                queue.push({
                    "source_parent_id": child.get("id"),
                    "target_parent_id": newChildFolder.get("id"),
                });
            }
            else
            {
                /* Copy file */
                await this.copyFile(
                    await this.fileItemRelation.findById(child.get("id")),
                    target_parent_id, child_name, chat_group_id
                );
            }
        }
    }

    return newFolder;
}


/**
 * Generate a unique name by appending a number suffix
 */
string generateUniqueName(
    string name, int parent_id, int chat_group_id
)
{
    string baseName = name;
    string ext = "";
    int dotIndex = rs::indexOf(name, ".");
    if (dotIndex > 0)
    {
        baseName = rs::substr(name, 0, dotIndex);
        ext = rs::substr(name, dotIndex, rs::strlen(name) - dotIndex);
    }

    int counter = 1;
    while (counter < 1000)
    {
        string testName = baseName ~ " (" ~ rtl::toString(counter) ~ ")" ~ ext;
        string testSlug = this.generateSlug(testName);
        FileItem existing = await this.findFileItemBySlug(
            parent_id, testSlug, chat_group_id
        );
        if (existing == null)
        {
            return testName;
        }
        counter++;
    }

    return baseName ~ " (" ~ rtl::toString(counter) ~ ")" ~ ext;
}
```

**Реализация в FileSaveApi.bay:**
```bay
/**
 * Action copy - Copy a file or folder to a new location
 *
 * @param group_id int - required
 * @param source_path string - required
 * @param target_path string - required
 */
@ApiMethod{ "name": "copy" }
async void actionCopy()
{
    this.filterData();
    await this.initService();

    int group_id = this.data.get("group_id");
    string source_path = this.data.get("source_path");
    string target_path = this.data.get("target_path");

    FileItem item = await this.service.copyItemByPath(
        source_path, target_path, group_id
    );

    this.result.data.set("item", item.getData());
    this.success();
}
```

**Файлы:**
- `src/lib/Runtime.AI/bay/Services/FileService.bay` — новые методы: `copyItemByPath()`, `copyFile()`, `copyFolder()`, `generateUniqueName()`
- `src/lib/Runtime.AI/bay/Api/File/FileSaveApi.bay` — новый метод `actionCopy()`

---

## 5. Исправление фронтенда (PasteCommand)

### 5.1. Реализация `executeCopy` в PasteCommand.bay

**Текущий код (TODO):**
```bay
async void executeCopy(CopyCommand copy_command, FileTreeItem item, Vector<int> item_path)
{
    /* TODO: Implement copy paste API */
    print("Copy paste executed. Source:", copy_command.copied_item_path_string);
    print("Target path:", this.getTree().getPath(item_path));
}
```

**Исправленный код:**
```bay
async void executeCopy(CopyCommand copy_command, FileTreeItem item, Vector<int> item_path)
{
    FileTreeModel model = this.getTree();

    ApiResult result = await this.layout.sendApi({
        "api_name": "ai.file",
        "method_name": "copy",
        "data":
        {
            "foreign_key":
            {
                "space_id": model.group.space_id,
            },
            "group_id": model.group.id,
            "source_path": copy_command.copied_item_path_string,
            "target_path": model.getPath(item_path),
        }
    });

    if (result.isSuccess())
    {
        /* Add copied item to tree */
        FileTreeItem parent_item = item_path ? model.tree.root.get(item_path, null) : model.tree.root;
        if (parent_item)
        {
            FileTreeItem newItem = FileTreeItem::newItem(FileItem::create(result.data.get("item")));
            parent_item.items.push(newItem);
            parent_item.sort();
        }

        /* Clear copy state */
        copy_command.reset();
    }
}
```

**Файл:** `src/lib/Runtime.AI/bay/Cabinet/Components/Chat/Commands/Paste/PasteCommand.bay`

---

## 6. Добавление data rules

В `getDataRules` класса `FileSaveApi.bay` нужно добавить:

```bay
void getDataRules(MapType rules)
{
    rules.addType("group_id", new Required());
    rules.addType("group_id", new IntegerType());
    rules.addType("path", new Required());
    rules.addType("path", new StringType());
    rules.addType("content", new StringType());
    rules.addType("new_name", new StringType());
    rules.addType("source_path", new StringType());
    rules.addType("target_path", new StringType());
}
```

---

## 7. Сводка изменений в файлах

### `src/lib/Runtime.AI/bay/Api/File/FileSaveApi.bay`

| Метод | Тип изменения |
|-------|---------------|
| `actionCreateFolder()` | Исправлен баг: возвращает `item` |
| `actionDelete()` | Исправлен баг: рекурсивное удаление папок |
| `actionRename()` | **Новый** метод |
| `actionMove()` | **Новый** метод |
| `actionCopy()` | **Новый** метод |
| `getDataRules()` | Добавлены `new_name`, `source_path`, `target_path` |

### `src/lib/Runtime.AI/bay/Services/FileService.bay`

| Метод | Тип изменения |
|-------|---------------|
| `deleteFolderByPath()` | **Новый** метод |
| `renameItemByPath()` | **Новый** метод |
| `moveItemByPath()` | **Новый** метод (обёртка над существующей логикой) |
| `copyItemByPath()` | **Новый** метод |
| `copyFile()` | **Новый** метод |
| `copyFolder()` | **Новый** метод |
| `generateUniqueName()` | **Новый** метод |

### `src/lib/Runtime.AI/bay/Cabinet/Components/Chat/Commands/Paste/PasteCommand.bay`

| Метод | Тип изменения |
|-------|---------------|
| `executeCopy()` | Исправлен: вызывает `ai.file.copy` вместо TODO |

---

## 8. Тестовые сценарии

### 8.1. create_folder — возвращает item
1. Вызвать `ai.file.create_folder` с `path: "/test-folder"`, `group_id: 1`
2. Проверить что в ответе есть `data.item` с `file_name: "test-folder"` и `file_type: "folder"`

### 8.2. delete — папка с содержимым
1. Создать папку `/test-folder`
2. Создать файл `/test-folder/file1.txt`
3. Создать подпапку `/test-folder/subfolder`
4. Создать файл `/test-folder/subfolder/file2.txt`
5. Удалить папку `/test-folder`
6. Проверить что все 4 записи удалены из `ai_file_items`
7. Проверить что orphaned файлы удалены из `ai_files`

### 8.3. rename — файл
1. Создать файл `/old-name.txt`
2. Вызвать `ai.file.rename` с `path: "/old-name.txt"`, `new_name: "new-name.txt"`
3. Проверить что `file_name` обновлён

### 8.4. rename — папка
1. Создать папку `/old-folder`
2. Вызвать `ai.file.rename` с `path: "/old-folder"`, `new_name: "new-folder"`
3. Проверить что `file_name` обновлён

### 8.5. move — файл в другую папку
1. Создать папку `/source` и `/target`
2. Создать файл `/source/file.txt`
3. Вызвать `ai.file.move` с `source_path: "/source/file.txt"`, `target_path: "/target"`
4. Проверить что `parent_id` обновлён

### 8.6. move — папка в другую папку
1. Создать папку `/source` с файлом внутри
2. Создать папку `/target`
3. Вызвать `ai.file.move` с `source_path: "/source"`, `target_path: "/target"`
4. Проверить что папка перемещена

### 8.7. move — защита от перемещения в себя
1. Создать папку `/folder` с подпапкой `/folder/sub`
2. Попытаться переместить `/folder` в `/folder/sub`
3. Ожидаемая ошибка: "Cannot move a folder into itself or its subfolder"

### 8.8. copy — файл
1. Создать файл `/original.txt` с контентом
2. Вызвать `ai.file.copy` с `source_path: "/original.txt"`, `target_path: "/"`
3. Проверить что создан новый файл с тем же контентом

### 8.9. copy — папка с содержимым
1. Создать папку `/folder` с файлом и подпапкой
2. Вызвать `ai.file.copy` с `source_path: "/folder"`, `target_path: "/"`
3. Проверить что скопирована вся иерархия
