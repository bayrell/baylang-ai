# Техническое задание: Команда Open для редактирования файла

**Дата:** 2026-06-23
**Модуль:** `Runtime.AI.Cabinet.Components.Chat.Commands`
**API:** `FileSaveApi.bay` (`ai.file`)
**Сервис:** `FileService.bay`

---

## 1. Цель

Добавить команду **Open** в файловое дерево чата, которая при нажатии на файловый элемент открывает диалоговое окно с редактированием содержимого файла. Команда должна быть **первой** в списке команд контекстного меню.

---

## 2. Поведение

### 2.1. Доступность команды

| Элемент | isAvailable |
|---------|-------------|
| Корень дерева (root) | `false` |
| Папка | `true` |
| Файл | `true` |

### 2.2. Действия при выполнении

1. **Определить путь** к элементу через `model.getPath(item_path)`
2. **Загрузить содержимое файла** через новый API `ai.file.read`
3. **Открыть диалог** с TextArea для редактирования
4. При **нажатии Save** — сохранить через `ai.file.save`
5. При **нажатии Close** — закрыть диалог без сохранения

### 2.3. Позиция в контекстном меню

Команда Open должна быть **первой** в списке. Порядок:

1. **open** (Open)
2. create_file (Create file)
3. create_folder (Create folder)
4. rename (Rename)
5. delete (Delete)
6. copy (Copy)
7. cut (Cut)
8. paste (Paste)
9. reload (Reload)

---

## 3. Реализация

### 3.1. API метод `read` — Чтение содержимого файла

В `FileService.bay` уже существует метод `readFileByPath`:
```bay
async string readFileByPath(string path, int chat_group_id)
{
    FileItem item = await this.findFileItemByPath(path, chat_group_id);
    if (item == null) throw new ApiError(new ItemNotFound("FileItem"));
    
    if (item.get("file_id") == 0)
    {
        throw new ApiError(new RuntimeException("Cannot read content of a folder"));
    }
    
    int file_id = item.get("file_id");
    File file = await this.findFile(file_id);
    if (file == null) throw new ApiError(new ItemNotFound("File"));
    
    return file.get("content");
}
```

**Добавить в `FileSaveApi.bay`:**

```bay
/**
 * Action read - Read file content by path
 *
 * @param group_id int - required
 * @param path string - required
 */
@ApiMethod{ "name": "read" }
async void actionRead()
{
    this.filterData();
    await this.initService();

    int group_id = this.data.get("group_id");
    string path = this.data.get("path");

    /* Check if path is a folder */
    bool is_folder = await this.service.isFolder(path, group_id);
    if (is_folder)
    {
        throw new ApiError(new RuntimeException("Cannot read content of a folder"));
    }

    /* Read file content */
    string content = await this.service.readFileByPath(path, group_id);

    /* Get file item info */
    FileItem item = await this.service.findFileItemByPath(path, group_id);

    this.result.data.set("content", content);
    this.result.data.set("item", item.getData());
    this.success();
}
```

**Добавить data rule:**
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

### 3.2. Новые файлы

#### `Open/Open.bay` — UI-компонент диалога

```bay
namespace Runtime.AI.Cabinet.Components.Chat.Commands.Open;

<class name="Runtime.AI.Cabinet.Components.Chat.Commands.Open.Open">

<use name="Runtime.Widget.Dialog.Dialog" component="true" />
<use name="Runtime.Widget.TextArea" component="true" />
<use name="Runtime.Widget.Button" component="true" />

<style>
.file_editor {
    display: flex;
    flex-direction: column;
    gap: var(--space);
}
.file_editor__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.file_editor__name {
    font-weight: bold;
    color: var(--color-text);
}
.file_editor__path {
    font-size: 0.85em;
    color: var(--color-text-secondary);
}
.file_editor__textarea {
    min-height: 400px;
    font-family: monospace;
}
.file_editor__error {
    color: var(--color-danger);
    font-size: 0.9em;
}
.file_editor__buttons {
    display: flex;
    gap: var(--space);
    justify-content: flex-end;
}
</style>

<template>
    <Dialog model={{ this.model.dialog }}>
        <slot name="title">
            {{ this.model.dialog_title }}
        </slot>
        <slot name="content">
            <div class="file_editor">
                <div class="file_editor__header">
                    <span class="file_editor__name">{{ this.model.file_name }}</span>
                    <span class="file_editor__path">{{ this.model.file_path }}</span>
                </div>
                %if (this.model.error)
                {
                    <div class="file_editor__error">
                        {{ this.model.error }}
                    </div>
                }
                %if (not this.model.is_loading)
                {
                    <TextArea
                        class="file_editor__textarea"
                        value={{ this.model.content }}
                        event:valueChange="this.model.onContentChange(event.value)"
                    />
                }
            </div>
        </slot>
        <slot name="footer">
            <Button
                class="button"
                @event:click="this.model.dialog.hide()"
            >
                Close
            </Button>
            <Button
                class="button button--primary"
                @event:click="this.model.save()"
            >
                Save
            </Button>
        </slot>
    </Dialog>
</template>

</class>
```

#### `Open/OpenCommand.bay` — Команда

```bay
namespace Runtime.AI.Cabinet.Components.Chat.Commands.Open;

use Runtime.ApiResult;
use Runtime.Serializer.ObjectType;
use Runtime.Widget.Dialog.DialogMessage;
use Runtime.AI.Cabinet.Components.Chat.Commands.BaseCommand;
use Runtime.AI.Cabinet.Components.Chat.Commands.Open.Open;
use Runtime.AI.Cabinet.Components.Chat.Commands.Open.OpenDialogModel;
use Runtime.AI.Cabinet.Components.Chat.FileTreeItem;
use Runtime.AI.Cabinet.Components.Chat.FileTreeModel;


class OpenCommand extends BaseCommand
{
	string component = classof Open;
	OpenDialogModel dialog = null;
	
	
	/**
	 * Returns command name
	 */
	static string getName() => "open";
	
	
	/**
	 * Returns label
	 */
	static string getLabel() => "Open";
	
	
	/**
	 * Returns order (first in list)
	 */
	static int getOrder() => 0;
	
	
	/**
	 * Serialize object
	 */
	static void serialize(ObjectType rules)
	{
		parent(rules);
		rules.addType("dialog", new ObjectType{
			"class_name": classof OpenDialogModel,
		});
	}
	
	
	/**
	 * Init widget
	 */
	void initWidget(Map params)
	{
		parent(params);
		
		this.dialog = this.createWidget(
			classof OpenDialogModel,
			{
				"events":
				{
					"save": method this.onSave
				}
			}
		);
	}
	
	
	/**
	 * Returns true if command is available
	 */
	bool isAvailable(FileTreeItem item)
	{
		/* Available for folders and files, not for root */
		if (not item) return false;
		if (not item.item) return false;
		return true;
	}
	
	
	/**
	 * Execute
	 */
	async void execute(FileTreeItem item, Vector<int> item_path)
	{
		this.item = item;
		this.item_path = item_path;
		
		FileTreeModel model = this.getTree();
		
		/* Set file info */
		string file_name = item.item ? item.item.file_name : "";
		string file_path = model.getPath(item_path);
		
		this.dialog.file_name = file_name;
		this.dialog.file_path = file_path;
		this.dialog.content = "";
		this.dialog.is_loading = true;
		this.dialog.show();
		
		/* Load file content */
		await this.loadContent(file_path, model.group.id);
	}
	
	
	/**
	 * Load file content from API
	 */
	async void loadContent(string path, int group_id)
	{
		ApiResult result = await this.layout.sendApi({
			"api_name": "ai.file",
			"method_name": "read",
			"data":
			{
				"foreign_key":
				{
					"space_id": this.getTree().group.space_id,
				},
				"group_id": group_id,
				"path": path,
			}
		});
		
		this.dialog.is_loading = false;
		
		if (result.isSuccess())
		{
			this.dialog.content = result.data.get("content", "");
			this.dialog.original_content = this.dialog.content;
			this.dialog.file_id = result.data.get("item").get("file_id", 0);
		}
		else
		{
			this.dialog.error = result.getError();
		}
	}
	
	
	/**
	 * Save file
	 */
	async void onSave(DialogMessage message)
	{
		this.dialog.setWaitMessage();
		
		FileTreeModel model = this.getTree();
		
		ApiResult result = await this.layout.sendApi({
			"api_name": "ai.file",
			"method_name": "save",
			"data":
			{
				"foreign_key":
				{
					"space_id": model.group.space_id,
				},
				"group_id": model.group.id,
				"path": this.dialog.file_path,
				"content": this.dialog.content,
			}
		});
		
		this.dialog.setApiResult(result);
		
		if (result.isSuccess())
		{
			this.dialog.hide();
		}
	}
}
```

#### `Open/OpenDialogModel.bay` — Модель диалога

```bay
namespace Runtime.AI.Cabinet.Components.Chat.Commands.Open;

use Runtime.BaseModel;
use Runtime.Widget.Dialog.DialogModel;


class OpenDialogModel extends DialogModel
{
	string file_name = "";
	string file_path = "";
	string content = "";
	string original_content = "";
	int file_id = 0;
	string dialog_title = "Edit File";
	bool is_loading = false;
	string error = "";
	
	
	/**
	 * Check if content has changes
	 */
	bool hasChanges()
	{
		return this.content != this.original_content;
	}
	
	
	/**
	 * Content change handler
	 */
	void onContentChange(string value)
	{
		this.content = value;
	}
	
	
	/**
	 * Set wait message
	 */
	void setWaitMessage(string message = "Saving...")
	{
		this.is_loading = true;
		this.error = "";
	}
	
	
	/**
	 * Set API result
	 */
	void setApiResult(ApiResult result)
	{
		this.is_loading = false;
		
		if (result.isSuccess())
		{
			this.original_content = this.content;
		}
		else
		{
			this.error = result.getError();
		}
	}
}
```

---

### 3.3. Модифицируемые файлы

#### `FileSaveApi.bay` — Добавление метода `read`

Добавить в класс `FileSaveApi`:

```bay
/**
 * Action read - Read file content by path
 *
 * @param group_id int - required
 * @param path string - required
 */
@ApiMethod{ "name": "read" }
async void actionRead()
{
    this.filterData();
    await this.initService();

    int group_id = this.data.get("group_id");
    string path = this.data.get("path");

    /* Check if path is a folder */
    bool is_folder = await this.service.isFolder(path, group_id);
    if (is_folder)
    {
        throw new ApiError(new RuntimeException("Cannot read content of a folder"));
    }

    /* Read file content */
    string content = await this.service.readFileByPath(path, group_id);

    /* Get file item info */
    FileItem item = await this.service.findFileItemByPath(path, group_id);

    this.result.data.set("content", content);
    this.result.data.set("item", item.getData());
    this.success();
}
```

Обновить `getDataRules`:
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

#### `FileTreeModel.bay` — Регистрация команды

Добавить импорт и регистрацию:

```bay
use Runtime.AI.Cabinet.Components.Chat.Commands.Open.OpenCommand;

/* В методе registerCommands() */
void registerCommands()
{
	this.registerCommand(classof OpenCommand);  /* Первая команда */
	this.registerCommand(classof CreateFileCommand);
	this.registerCommand(classof CreateFolderCommand);
	this.registerCommand(classof DeleteCommand);
	this.registerCommand(classof RenameCommand);
	this.registerCommand(classof CopyCommand);
	this.registerCommand(classof CutCommand);
	this.registerCommand(classof PasteCommand);
	this.registerCommand(classof ReloadCommand);
}
```

---

## 4. API вызовы

### 4.1. Загрузка содержимого файла

**Запрос:**
```json
{
    "api_name": "ai.file",
    "method_name": "read",
    "data": {
        "foreign_key": { "space_id": 1 },
        "group_id": 123,
        "path": "/docs/readme.md"
    }
}
```

**Ответ:**
```json
{
    "data": {
        "content": "# Hello World\n\nThis is a test file.",
        "item": {
            "id": 456,
            "file_id": 789,
            "file_name": "readme.md",
            "file_type": "file"
        }
    }
}
```

### 4.2. Сохранение изменений

**Запрос:**
```json
{
    "api_name": "ai.file",
    "method_name": "save",
    "data": {
        "foreign_key": { "space_id": 1 },
        "group_id": 123,
        "path": "/docs/readme.md",
        "content": "# Hello World\n\nUpdated content."
    }
}
```

---

## 5. Структура файлов

```
Commands/
├── Open/
│   ├── Open.bay              # UI-компонент диалога
│   ├── OpenCommand.bay       # Команда
│   └── OpenDialogModel.bay   # Модель диалога
├── BaseCommand.bay
├── CreateFile/
├── CreateFolder/
├── Delete/
├── Rename/
├── Copy/
├── Cut/
├── Paste/
└── Reload/
```

---

## 6. CSS-классы

| Класс | Описание |
|-------|----------|
| `file_editor` | Контейнер редактора |
| `file_editor__header` | Заголовок с именем файла |
| `file_editor__name` | Имя файла |
| `file_editor__path` | Путь к файлу |
| `file_editor__textarea` | TextArea для редактирования |
| `file_editor__error` | Сообщение об ошибке |
| `file_editor__buttons` | Кнопки Save/Close |

---

## 7. Тестовые сценарии

### 7.1. Открытие файла на редактирование
1. Вызвать контекстное меню на файле
2. Нажать "Open"
3. Проверить что диалог открыт с именем файла и его содержимым

### 7.2. Редактирование и сохранение
1. Открыть файл через команду Open
2. Изменить содержимое в TextArea
3. Нажать Save
4. Проверить что API `ai.file.save` вызван с новым содержимым
5. Проверить что диалог закрыт

### 7.3. Закрытие без сохранения
1. Открыть файл через команду Open
2. Изменить содержимое
3. Нажать Close
4. Проверить что диалог закрыт без вызова API

### 7.4. Позиция в контекстном меню
1. Вызвать контекстное меню
2. Проверить что "Open" — первая команда в списке

### 7.5. Доступность для папок
1. Вызвать контекстное меню на папке
2. Проверить что команда "Open" доступна

### 7.6. Ошибка чтения папки
1. Попытаться открыть папку через команду Open
2. Проверить что отображается сообщение об ошибке

---

## 8. Зависимости

- `Runtime.Widget.Dialog.Dialog` — базовый компонент диалога
- `Runtime.Widget.TextArea` — компонент текстового поля
- `Runtime.Widget.Button` — компонент кнопки
- `Runtime.Widget.Dialog.DialogModel` — базовая модель диалога

---

## 9. Backward Compatibility

Команда Open не меняет существующий API (кроме добавления нового метода `read`) и не затрагивает другие команды. Все изменения изолированы в новой папке `Commands/Open/`.
