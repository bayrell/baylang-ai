# Техническое задание: Инструменты Notebook, Filesystem, Rules для QuestionService

## 1. Введение

### 1.1. Цель
Добавить три новых инструмента (Tools) для LLM — **NotebookTool**, **FilesystemTool**, **RuleTool** — и интегрировать Rules в промпт `QuestionService` через механизм `autoload`. Это позволит LLM:
- Управлять блокнотом (заметки, категории, теги)
- Работать с файловой системой (чтение/запись файлов в чат-группе)
- Управлять правилами (загружать, просматривать, создавать новые rules)

### 1.2. Связанные задачи
- В `QuestionService.buildPrompt` добавить автоматическую загрузку правил с `is_active=autoload`
- Добавить в промпт список доступных rules (названия и описания)
- Позволить LLM загружать и создавать новые rules через Tool

---

## 2. Архитектура

### 2.1. Структура файлов

```
src/lib/Runtime.AI/bay/Tools/
├── BaseTool.bay              # Существующий — без изменений
├── MemoryTool.bay            # Существующий — без изменений
├── NotebookTool.bay          # НОВЫЙ
├── FilesystemTool.bay        # НОВЫЙ
├── RuleTool.bay              # НОВЫЙ

src/lib/Runtime.AI/bay/Services/
├── ToolRegistry.bay          # ИЗМЕНЁН — регистрация новых tools
├── QuestionService.bay       # ИЗМЕНЁН — buildPrompt + rules autoload
├── FileService.bay           # Существующий — без изменений
├── RuleService.bay           # НОВЫЙ (сервис для работы с rules)
```

### 2.2. Зависимости

```
QuestionService
  ├── ToolRegistry
  │     ├── MemoryTool
  │     ├── NotebookTool
  │     ├── FilesystemTool
  │     └── RuleTool
  ├── RuleService            # загрузка rules для промпта
  └── PromptBuilder          # (внутри buildPrompt)
```

---

## 3. Детали реализации

### 3.1. RuleService (НОВЫЙ)

**Файл:** `src/lib/Runtime.AI/bay/Services/RuleService.bay`

Сервис для работы с правилами (rules) из таблицы `ai_rules`.

```baylang
namespace Runtime.AI.Services;

use Runtime.BaseObject;
use Runtime.Exceptions.ApiError;
use Runtime.Exceptions.RuntimeException;
use Runtime.AI.Database.Rule;
use Runtime.AI.Database.AndroidRule;
use Runtime.ORM.Relation;
use Runtime.ORM.Query;

class RuleService extends BaseObject
{
    Relation ruleRelation = new Relation(classof Rule);
    Relation androidRuleRelation = new Relation(classof AndroidRule);

    int android_id = 0;
    int space_id = 0;

    /**
     * Get all rules for the current space
     */
    async Vector<Map> getRules(int space_id)
    {
        Query q = this.ruleRelation.select()
            .where("space_id", "=", space_id)
            .orderBy("name", "asc");
        return await this.ruleRelation.fetchAll(q);
    }

    /**
     * Get rules with is_active=autoload for prompt injection
     * Возвращает Vector<Map> с полями: name, description, content
     */
    async Vector<Map> getAutoloadRules(int space_id)
    {
        Query q = this.ruleRelation.select()
            .where("space_id", "=", space_id)
            .where("is_active", "=", "autoload")
            .orderBy("name", "asc");
        return await this.ruleRelation.fetchAll(q);
    }

    /**
     * Get list of all rule names for LLM context
     */
    async Vector<string> getRuleNames(int space_id)
    {
        Vector<Map> rules = await this.getRules(space_id);
        return rules.map(
            string (Map rule) => rule.get("name")
        );
    }

    /**
     * Get rule by name
     */
    async Map getRuleByName(string name, int space_id)
    {
        Query q = this.ruleRelation.select()
            .where("space_id", "=", space_id)
            .where("name", "=", name)
            .limit(1);
        return await this.ruleRelation.fetchOne(q);
    }

    /**
     * Save a rule (create or update)
     */
    async Map saveRule(
        string name, string description,
        string content, int space_id
    )
    {
        Map existing = await this.getRuleByName(name, space_id);

        Rule rule = null;
        if (existing)
        {
            rule = await this.ruleRelation.findById(
                existing.get("id")
            );
        }
        else
        {
            rule = this.ruleRelation.createRecord();
            rule.set("space_id", space_id);
            rule.set("name", name);
            rule.set("is_active", "manual");
        }

        if (description) rule.set("description", description);
        if (content) rule.set("content", content);
        await rule.save();

        return rule;
    }

    /**
     * Update is_active status for a rule
     */
    async void setRuleActive(string name, string is_active, int space_id)
    {
        Map existing = await this.getRuleByName(name, space_id);
        if (!existing)
        {
            throw new ApiError(
                new RuntimeException("Rule not found: " ~ name)
            );
        }

        Rule rule = await this.ruleRelation.findById(
            existing.get("id")
        );
        rule.set("is_active", is_active);
        await rule.save();
    }

    /**
     * Delete a rule
     */
    async void deleteRule(string name, int space_id)
    {
        Map existing = await this.getRuleByName(name, space_id);
        if (existing)
        {
            Rule rule = await this.ruleRelation.findById(
                existing.get("id")
            );
            await rule.delete();
        }
    }
}
```

**Таблица `ai_rules` (структура — уже существует):**

| Поле | Тип | Описание |
|------|-----|----------|
| id | bigint, PK | ID |
| file_name | string | Имя файла-источника |
| name | string | Уникальное имя правила |
| description | string | Описание правила |
| class_name | string | Имя класса (для runtime rules) |
| config | json | Конфигурация правила |
| is_active | string | Статус: `autoload`, `manual`, `disabled` |
| space_id | bigint | ID пространства |
| content | text | Содержимое правила (для LLM) |

> **Примечание:** Поле `content` может отсутствовать в текущей миграции. Если нужно — добавить через патч-миграцию. Если `content` не нужен, для autoload правил используется поле `description`.

---

### 3.2. NotebookTool (НОВЫЙ)

**Файл:** `src/lib/Runtime.AI/bay/Tools/NotebookTool.bay`

Инструмент для работы с блокнотом (заметки, категории, теги).

```baylang
namespace Runtime.AI.Tools;

use Runtime.Exceptions.RuntimeException;
use Runtime.AI.Services.QuestionService;
use Runtime.AI.Services.NoteService;
use Runtime.AI.Models.ToolResponse;
use Runtime.AI.Tools.BaseTool;

class NotebookTool extends BaseTool
{
    pure string getName() => "notebook";

    pure string getDescription() =>
        "Tool for working with notebook (notes, categories, tags). "
        ~ "Actions: search, read, save, delete, list_categories, list_tags";

    pure Map getParameters() =>
    {
        "type": "object",
        "properties":
        {
            "action":
            {
                "type": "string",
                "description": "Action: search, read, save, delete, list_categories, list_tags",
                "enum": ["search", "read", "save", "delete", "list_categories", "list_tags"]
            },
            "note_id":
            {
                "type": "integer",
                "description": "Note ID (for read/delete)"
            },
            "title":
            {
                "type": "string",
                "description": "Note title (for save)"
            },
            "content":
            {
                "type": "string",
                "description": "Note content (for save)"
            },
            "category":
            {
                "type": "string",
                "description": "Category name (for save/search)"
            },
            "tags":
            {
                "type": "array",
                "items": { "type": "string" },
                "description": "Tags (for save/search)"
            },
            "query":
            {
                "type": "string",
                "description": "Search query (for search)"
            },
            "priority":
            {
                "type": "string",
                "description": "Priority: low, normal, high, critical",
                "enum": ["low", "normal", "high", "critical"]
            }
        },
        "required": ["action"]
    };

    async ToolResponse execute(QuestionService service, Map params)
    {
        ToolResponse result = new ToolResponse();

        string action = params.get("action", "");

        NoteService noteService = new NoteService();
        noteService.android_id = service.android_id;
        noteService.user_id = service.user_id;
        noteService.space_id = service.chatService.space_id;
        await noteService.initService();

        try
        {
            if (action == "list_categories")
            {
                Vector categories = await noteService.getCategories();
                result.answer = rtl::jsonEncode(categories);
            }
            else if (action == "list_tags")
            {
                Vector tags = await noteService.getTags();
                result.answer = rtl::jsonEncode(tags);
            }
            else if (action == "search")
            {
                string query = params.get("query", "");
                string category = params.get("category", "");
                Vector tags = params.get("tags", []);
                // ... search logic via NoteService
                result.answer = "Search results...";
            }
            else if (action == "read")
            {
                int note_id = params.get("note_id", 0);
                // ... read note
                result.answer = "Note content...";
            }
            else if (action == "save")
            {
                string title = params.get("title", "");
                string content = params.get("content", "");
                string category = params.get("category", "");
                Vector tags = params.get("tags", []);
                string priority = params.get("priority", "normal");
                // ... save note
                result.answer = "Note saved successfully.";
            }
            else if (action == "delete")
            {
                int note_id = params.get("note_id", 0);
                // ... delete note
                result.answer = "Note deleted.";
            }
            else
            {
                result.success = false;
                result.answer = "Unknown action: " ~ action;
            }
        }
        catch (RuntimeException e)
        {
            result.success = false;
            result.answer = "Error: " ~ e.getErrorMessage();
        }

        return result;
    }

    pure string getMessage(Map params)
    {
        string action = params.get("action", "");
        return "Notebook tool: " ~ action;
    }
}
```

---

### 3.3. FilesystemTool (НОВЫЙ)

**Файл:** `src/lib/Runtime.AI/bay/Tools/FilesystemTool.bay`

Инструмент для работы с файловой системой (чтение/запись/создание файлов в чат-группе).

```baylang
namespace Runtime.AI.Tools;

use Runtime.Exceptions.RuntimeException;
use Runtime.AI.Services.QuestionService;
use Runtime.AI.Services.FileService;
use Runtime.AI.Models.ToolResponse;
use Runtime.AI.Tools.BaseTool;

class FilesystemTool extends BaseTool
{
    pure string getName() => "filesystem";

    pure string getDescription() =>
        "Tool for working with files in the chat group. "
        ~ "Actions: read, write, list, mkdir, delete, move, info";

    pure Map getParameters() =>
    {
        "type": "object",
        "properties":
        {
            "action":
            {
                "type": "string",
                "description": "Action: read, write, list, mkdir, delete, move, info",
                "enum": ["read", "write", "list", "mkdir", "delete", "move", "info"]
            },
            "path":
            {
                "type": "string",
                "description": "File/folder path, e.g. /docs/readme.md"
            },
            "content":
            {
                "type": "string",
                "description": "File content (for write)"
            },
            "target_path":
            {
                "type": "string",
                "description": "Target path (for move)"
            },
            "group_id":
            {
                "type": "integer",
                "description": "Chat group ID"
            }
        },
        "required": ["action", "path"]
    };

    async ToolResponse execute(QuestionService service, Map params)
    {
        ToolResponse result = new ToolResponse();

        string action = params.get("action", "");
        string path = params.get("path", "");
        int group_id = params.get("group_id", 0);

        FileService fileService = new FileService();
        fileService.space_id = service.chatService.space_id;
        fileService.android_id = service.android_id;

        try
        {
            if (action == "read")
            {
                string content = await fileService.readFileByPath(
                    path, group_id
                );
                result.answer = content;
            }
            else if (action == "write")
            {
                string content = params.get("content", "");
                Map saved = await fileService.saveFileByPath(
                    path, content, group_id
                );
                string action_type = saved.get("action", "saved");
                result.answer = "File " ~ action_type ~ " successfully: " ~ path;
            }
            else if (action == "list")
            {
                FileItem item = await fileService.findFileItemByPath(
                    path, group_id
                );
                int item_id = item ? item.get("id") : 0;
                Vector items = await fileService.listDirByItemId(
                    item_id, false, 0, group_id
                );
                result.answer = rtl::jsonEncode(items);
            }
            else if (action == "mkdir")
            {
                Map created = await fileService.mkdirByPath(path, group_id);
                result.answer = "Folder created: " ~ path;
            }
            else if (action == "delete")
            {
                await fileService.deleteFileByPath(path, group_id);
                result.answer = "Deleted: " ~ path;
            }
            else if (action == "move")
            {
                string target = params.get("target_path", "");
                await fileService.moveItemByPath(path, target, group_id);
                result.answer = "Moved " ~ path ~ " to " ~ target;
            }
            else if (action == "info")
            {
                FileItem item = await fileService.findFileItemByPath(
                    path, group_id
                );
                if (item)
                {
                    Map info = await fileService.getItemInfo(item.get("id"));
                    result.answer = rtl::jsonEncode(info);
                }
                else
                {
                    result.success = false;
                    result.answer = "File not found: " ~ path;
                }
            }
            else
            {
                result.success = false;
                result.answer = "Unknown action: " ~ action;
            }
        }
        catch (RuntimeException e)
        {
            result.success = false;
            result.answer = "Error: " ~ e.getErrorMessage();
        }

        return result;
    }

    pure string getMessage(Map params)
    {
        string action = params.get("action", "");
        string path = params.get("path", "");
        return "Filesystem tool: " ~ action ~ " " ~ path;
    }
}
```

---

### 3.4. RuleTool (НОВЫЙ)

**Файл:** `src/lib/Runtime.AI/bay/Tools/RuleTool.bay`

Инструмент для работы с правилами (rules) — просмотр, создание, загрузка.

```baylang
namespace Runtime.AI.Tools;

use Runtime.Exceptions.RuntimeException;
use Runtime.AI.Services.QuestionService;
use Runtime.AI.Services.RuleService;
use Runtime.AI.Models.ToolResponse;
use Runtime.AI.Tools.BaseTool;

class RuleTool extends BaseTool
{
    pure string getName() => "rules";

    pure string getDescription() =>
        "Tool for managing AI rules (prompts, instructions). "
        ~ "Actions: list, read, save, set_autoload, delete. "
        ~ "Rules with is_active='autoload' are automatically loaded into the prompt.";

    pure Map getParameters() =>
    {
        "type": "object",
        "properties":
        {
            "action":
            {
                "type": "string",
                "description": "Action: list, read, save, set_autoload, delete",
                "enum": ["list", "read", "save", "set_autoload", "delete"]
            },
            "name":
            {
                "type": "string",
                "description": "Rule name (unique identifier)"
            },
            "description_rule":
            {
                "type": "string",
                "description": "Rule description"
            },
            "content":
            {
                "type": "string",
                "description": "Rule content/prompt text (for save)"
            }
        },
        "required": ["action"]
    };

    async ToolResponse execute(QuestionService service, Map params)
    {
        ToolResponse result = new ToolResponse();

        string action = params.get("action", "");
        int space_id = service.chatService.space_id;

        RuleService ruleService = new RuleService();
        ruleService.android_id = service.android_id;
        ruleService.space_id = space_id;

        try
        {
            if (action == "list")
            {
                Vector rules = await ruleService.getRules(space_id);
                Vector names = rules.map(
                    string (Map r) =>
                        r.get("name")
                        ~ " (" ~ r.get("is_active", "manual") ~ ")"
                        ~ (r.get("description", "") != ""
                            ? " — " ~ r.get("description", "")
                            : "")
                );
                result.answer = "Available rules:\n"
                    ~ rs::join("\n", names);
            }
            else if (action == "read")
            {
                string name = params.get("name", "");
                Map rule = await ruleService.getRuleByName(name, space_id);
                if (rule)
                {
                    result.answer = "Rule: " ~ rule.get("name")
                        ~ "\nDescription: " ~ rule.get("description", "")
                        ~ "\nStatus: " ~ rule.get("is_active", "manual")
                        ~ "\nContent:\n" ~ rule.get("content", "");
                }
                else
                {
                    result.success = false;
                    result.answer = "Rule not found: " ~ name;
                }
            }
            else if (action == "save")
            {
                string name = params.get("name", "");
                string description = params.get("description_rule", "");
                string content = params.get("content", "");

                if (name == "")
                {
                    result.success = false;
                    result.answer = "Rule name is required.";
                    return result;
                }

                await ruleService.saveRule(
                    name, description, content, space_id
                );
                result.answer = "Rule saved successfully: " ~ name;
            }
            else if (action == "set_autoload")
            {
                string name = params.get("name", "");
                if (name == "")
                {
                    result.success = false;
                    result.answer = "Rule name is required.";
                    return result;
                }

                await ruleService.setRuleActive(
                    name, "autoload", space_id
                );
                result.answer = "Rule '" ~ name ~ "' set to autoload. "
                    ~ "It will be loaded into the prompt on next message.";
            }
            else if (action == "delete")
            {
                string name = params.get("name", "");
                if (name == "")
                {
                    result.success = false;
                    result.answer = "Rule name is required.";
                    return result;
                }

                await ruleService.deleteRule(name, space_id);
                result.answer = "Rule deleted: " ~ name;
            }
            else
            {
                result.success = false;
                result.answer = "Unknown action: " ~ action;
            }
        }
        catch (RuntimeException e)
        {
            result.success = false;
            result.answer = "Error: " ~ e.getErrorMessage();
        }

        return result;
    }

    pure string getMessage(Map params)
    {
        string action = params.get("action", "");
        return "Rules tool: " ~ action;
    }
}
```

---

### 3.5. Изменения в ToolRegistry

**Файл:** `src/lib/Runtime.AI/bay/Services/ToolRegistry.bay`

Добавить регистрацию новых инструментов:

```diff
 use Runtime.BaseProvider;
 use Runtime.AI.Tools.BaseTool;
 use Runtime.AI.Tools.MemoryTool;
+use Runtime.AI.Tools.NotebookTool;
+use Runtime.AI.Tools.FilesystemTool;
+use Runtime.AI.Tools.RuleTool;

 class ToolRegistry extends BaseProvider
 {
     async void init()
     {
         await parent();
         this.register(new MemoryTool());
+        this.register(new NotebookTool());
+        this.register(new FilesystemTool());
+        this.register(new RuleTool());
     }
```

---

### 3.6. Изменения в QuestionService.buildPrompt

**Файл:** `src/lib/Runtime.AI/bay/Services/QuestionService.bay`

Метод `buildPrompt` должен:
1. Загружать правила с `is_active=autoload`
2. Добавлять в промпт список доступных rules (названия)
3. Загружать содержимое autoload правил как системные сообщения

```diff
+use Runtime.AI.Services.RuleService;

 class QuestionService extends BaseObject
 {
+    RuleService ruleService = null;

     async void init()
     {
         /* ... существующий код ... */
+        this.ruleService = new RuleService();
     }

     /**
      * Build prompt with history
      */
     async void buildPrompt(string message)
     {
         await this.addMemory();
+        await this.addRulesPrompt();

         /* Загружаем историю чата */
         Vector<ChatMessage> history = await this.loadChatHistory(this.chat_id);

         /* Добавляем историю в промпт */
         this.prompt.appendItems(history);
     }

+    /**
+     * Add rules to prompt
+     * 1. Add list of all available rules (names + descriptions)
+     * 2. Add content of rules with is_active=autoload
+     */
+    async void addRulesPrompt()
+    {
+        int space_id = this.chatService ? this.chatService.space_id : 0;
+        if (space_id == 0) return;
+
+        this.ruleService.space_id = space_id;
+        this.ruleService.android_id = this.android_id;
+
+        /* 1. Add list of all rule names */
+        Vector<Map> allRules = await this.ruleService.getRules(space_id);
+
+        if (allRules.count() > 0)
+        {
+            Vector<string> ruleNames = allRules.map(
+                string (Map r) =>
+                    "• " ~ r.get("name")
+                    ~ (r.get("description", "") != ""
+                        ? " — " ~ r.get("description", "")
+                        : "")
+            );
+
+            ChatMessage rulesListMessage = this.createMessage(
+                ChatMessage::ROLE_SYSTEM
+            );
+            rulesListMessage.content.push(new TextMessage{
+                "text": "Available AI rules (you can use 'rules' tool to read or manage them):\n"
+                    ~ rs::join("\n", ruleNames)
+            });
+            this.prompt.push(rulesListMessage);
+        }
+
+        /* 2. Add content of autoload rules */
+        Vector<Map> autoloadRules = await this.ruleService.getAutoloadRules(space_id);
+
+        for (Map rule in autoloadRules)
+        {
+            string ruleContent = rule.get("content", "");
+            if (ruleContent == "") continue;
+
+            ChatMessage ruleMessage = this.createMessage(
+                ChatMessage::ROLE_SYSTEM
+            );
+            ruleMessage.content.push(new TextMessage{
+                "text": "Rule [" ~ rule.get("name") ~ "]:\n" ~ ruleContent
+            });
+            this.prompt.push(ruleMessage);
+        }
+    }
 }
```

---

## 4. Миграция БД (если нужно)

### 4.1. Добавление поля `content` в таблицу `ai_rules`

Если поле `content` отсутствует в текущей схеме:

```sql
ALTER TABLE ai_rules
ADD COLUMN content TEXT DEFAULT NULL
AFTER config;
```

**Файл миграции:** `src/lib/Runtime.AI/bay/Database/Migrations/Migration_2026_Rules.bay`

```baylang
namespace Runtime.AI.Database.Migrations;

use Runtime.ORM.Annotations.Migration;
use Runtime.ORM.BaseMigration;

class Migration_2026_Rules extends BaseMigration
{
    pure int getMigrationId() => 2026_06_23_001;

    async void up()
    {
        /* Add content column to ai_rules if not exists */
        await this.execute(
            "ALTER TABLE ai_rules "
            ~ "ADD COLUMN content TEXT DEFAULT NULL "
            ~ "AFTER config"
        );
    }
}
```

### 4.2. Изменение типа `is_active` (если нужно)

Текущий тип `is_active` — `BooleanType`. Для поддержки статусов `autoload`, `manual`, `disabled` нужно изменить на `StringType`:

```sql
ALTER TABLE ai_rules
MODIFY COLUMN is_active VARCHAR(20) DEFAULT 'manual';
```

> **Важно:** Это изменение требует обновления модели `Rule.bay` (Database) и `RuleSaveApi.bay`.

---

## 5. Изменение модели Rule (Database)

**Файл:** `src/lib/Runtime.AI/bay/Database/Rule.bay`

```diff
+use Runtime.ORM.Annotations.TextType;

 class Rule extends Record
 {
     pure string getTableName() => "ai_rules";

     pure Vector<BaseObject> schema() =>
     [
         /* ... существующие поля ... */
+        new TextType{"name": "content"},
+        new StringType{"name": "is_active", "default": "manual"},
     ];
 }
```

---

## 6. Изменение RuleSaveApi

**Файл:** `src/lib/Runtime.AI/bay/Cabinet/Api/RuleSaveApi.bay`

```diff
+use Runtime.Serializer.StringType;

     void getItemRules(MapType rules)
     {
         rules.addType("id", new IntegerType());
         rules.addType("name", new Required());
         rules.addType("name", new StringType());
         rules.addType("file_name", new Required());
         rules.addType("file_name", new StringType());
         rules.addType("description", new StringType());
         rules.addType("class_name", new StringType());
-        rules.addType("is_active", new BooleanType());
+        rules.addType("is_active", new StringType());
+        rules.addType("content", new StringType());
     }

     Vector<string> getItemFields(string action) =>
     [
         "id",
         "name",
         "file_name",
         "description",
         "class_name",
         "is_active",
+        "content",
         "gmtime_add",
         "gmtime_edit",
     ];
```

---

## 7. Изменение Rule (DTO Model)

**Файл:** `src/lib/Runtime.AI/bay/Models/Rule.bay`

```diff
+use Runtime.Serializer.StringType;

 class Rule extends BaseDTO
 {
     int id = 0;
     string name = "";
     string file_name = "";
     string description = "";
     string class_name = "";
     int space_id = 0;
-    bool is_active = true;
+    string is_active = "manual";
+    string content = "";

     static void serialize(ObjectType rules)
     {
         parent(rules);
         rules.addType("id", new IntegerType());
         rules.addType("name", new StringType());
         rules.addType("file_name", new StringType());
         rules.addType("description", new StringType());
         rules.addType("class_name", new StringType());
         rules.addType("space_id", new IntegerType());
-        rules.addType("is_active", new BooleanType());
+        rules.addType("is_active", new StringType());
+        rules.addType("content", new StringType());
     }
 }
```

---

## 8. Список файлов

### Новые файлы:
| Файл | Описание |
|------|----------|
| `src/lib/Runtime.AI/bay/Tools/NotebookTool.bay` | Инструмент блокнота |
| `src/lib/Runtime.AI/bay/Tools/FilesystemTool.bay` | Инструмент файловой системы |
| `src/lib/Runtime.AI/bay/Tools/RuleTool.bay` | Инструмент правил |
| `src/lib/Runtime.AI/bay/Services/RuleService.bay` | Сервис для работы с rules |
| `src/lib/Runtime.AI/bay/Database/Migrations/Migration_2026_Rules.bay` | Миграция БД |

### Изменённые файлы:
| Файл | Описание изменений |
|------|-------------------|
| `src/lib/Runtime.AI/bay/Services/ToolRegistry.bay` | Регистрация новых tools |
| `src/lib/Runtime.AI/bay/Services/QuestionService.bay` | `addRulesPrompt()` в `buildPrompt` |
| `src/lib/Runtime.AI/bay/Database/Rule.bay` | Поле `content` (TextType), `is_active` (StringType) |
| `src/lib/Runtime.AI/bay/Models/Rule.bay` | Поле `content`, изменение `is_active` на string |
| `src/lib/Runtime.AI/bay/Cabinet/Api/RuleSaveApi.bay` | `is_active` как StringType, добавление `content` |

---

## 9. Flow Diagram

### 9.1. Загрузка rules при отправке сообщения

```
User sends message
    │
    ▼
QuestionService.processMessage()
    │
    ▼
QuestionService.buildPrompt()
    │
    ├──► addMemory()
    │
    ├──► addRulesPrompt()  ←── НОВЫЙ
    │       │
    │       ├──► RuleService.getRules(space_id)
    │       │       → список всех rules (names + descriptions)
    │       │       → добавляется в промпт как системное сообщение
    │       │
    │       └──► RuleService.getAutoloadRules(space_id)
    │               → правила с is_active="autoload"
    │               → содержимое добавляется в промпт
    │
    ├──► loadChatHistory()
    │
    └──► sendWithTools()
            │
            ▼
        LLM может вызвать RuleTool для:
            - list: посмотреть все правила
            - read: прочитать конкретное правило
            - save: создать/обновить правило
            - set_autoload: включить автозагрузку правила
            - delete: удалить правило
```

### 9.2. Пример использования LLM

**Пользователь:** «Создай правило для формата ответов в стиле JSON»

**LLM вызывает:** `rules` tool с action=`save`, name=`json_format`, content=`"... инструкция ..."`

**LLM затем вызывает:** `rules` tool с action=`set_autoload`, name=`json_format`

**Результат:** Правило сохранено и будет автоматически загружаться в промпт при каждом следующем сообщении.
