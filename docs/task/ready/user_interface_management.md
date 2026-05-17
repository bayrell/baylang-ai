# Техническое задание: Интерфейс для управления пользователями

**Назначение:** Создание интерфейса для добавления и редактирования пользователей в модуле `Runtime.Cabinet`.
**Местоположение:** `src/lib/Runtime.Cabinet/bay/Components`
**Тип:** Backend/Frontend интерфейс (используя `TableWrap` и `Manager`)

## 1. Общие требования

1.1. Интерфейс должен быть реализован в виде компонента BayLang.
1.2. Для отображения таблицы и управления данными использовать компонент `Runtime.Widget.Table.TableWrap`.
1.3. Для управления логикой (загрузка данных, обработка событий) использовать модель (Manager) на базе `Runtime.Widget.Table.TableManager`.
1.4. Интерфейс должен поддерживать:
    - Просмотр списка пользователей (таблица).
    - Добавление нового пользователя (диалог/форма).
    - Редактирование существующего пользователя (диалог/форма).
    - Удаление пользователя (с подтверждением).
1.5. Данные должны загружаться через API методы.
    - Для поиска и получения списка пользователей использовать **SearchApi**.
    - Для создания, обновления и удаления пользователей использовать **SaveApi**.

## 2. API (Backend)

### 2.1. Database Record (Сущность пользователя)

В проекте уже существует сущность пользователя в `Runtime.Cabinet` и `Runtime.Auth`.

**Файл:** `src/lib/Runtime.Cabinet/bay/Database/User.bay`

```baylang
namespace Runtime.Cabinet.Database;

use Runtime.Auth.Database.User as BaseUser;
// ... остальные use ...

class User extends BaseUser
{
    /**
     * Returns table name
     */
    pure string getTableName() => "cabinet_users";
    
    
    /**
     * Returns table schema
     */
    pure Vector<BaseObject> schema()
    {
        Vector<BaseObject> fields = parent();
        fields.appendItems([
            new StringType{ "name": "email" },
            new StringType{ "name": "name" },
        ]);
        return fields;
    }
}
```

Обратите внимание:
- Таблица: `cabinet_users`.
- Поля: `id`, `login`, `password`, `is_deleted`, `gmtime_add`, `gmtime_edit`, `email`, `name`.
- Наследуется от `Runtime.Auth.Database.User`.

### 2.2. SearchApi (Получение списка пользователей)

Файл: `src/lib/Runtime.Cabinet/bay/Api/UserSearchApi.bay`

```baylang
namespace Runtime.Cabinet.Api;

use Runtime.ORM.Query;
use Runtime.Widget.Api.SearchApi;
use Runtime.Cabinet.Database.User;

class UserSearchApi extends SearchApi
{
    /**
     * Returns api name
     */
    pure string getApiName() => "runtime.cabinet.user";
    
    
    /**
     * Returns record name
     */
    pure string getRecordName() => classof User;
    
    
    /**
     * Returns item fields
     */
    Vector<string> getItemFields(string action) =>
    [
        "id",
        "login",
        "email",
        "name",
        "gmtime_add",
    ];
    
    
    /**
     * Build Query
     */
    async void buildQuery(Query q)
    {
        // Фильтрация удаленных пользователей
        q.where("is_deleted", "=", 0);
        
        // Пример поиска по логину или email
        if (this.data.has("search"))
        {
            string search = this.data.get("search");
            q.where((Query filter) => {
                filter.where("login", "LIKE", "%" + search + "%")
                    ->orWhere("email", "LIKE", "%" + search + "%");
            });
        }
    }
    
    
    /**
     * Action search
     */
    @ApiMethod{ "name": "search" }
    async void actionSearch()
    {
        await parent();
    }
    
    
    /**
     * Action item
     */
    @ApiMethod{ "name": "item" }
    async void actionItem()
    {
        await parent();
    }
}
```

### 2.3. SaveApi (Создание/Обновление/Удаление пользователей)

Файл: `src/lib/Runtime.Cabinet/bay/Api/UserSaveApi.bay`

```baylang
namespace Runtime.Cabinet.Api;

use Runtime.Widget.Api.SaveApi;
use Runtime.Widget.Api.Rules.UniqueRule;
use Runtime.Cabinet.Database.User;
use Runtime.Crypt.Password;

class UserSaveApi extends SaveApi
{
    /**
     * Returns api name
     */
    pure string getApiName() => "runtime.cabinet.user";
    
    
    /**
     * Returns record name
     */
    pure string getRecordName() => classof User;
    
    
    /**
     * Returns save rules
     */
    Vector<BaseRule> rules() =>
    [
        new UniqueRule{"field_name": "login"},
        new UniqueRule{"field_name": "email"},
    ];
    
    
    /**
     * Returns item rules
     */
    void getItemRules(MapType rules)
    {
        rules.addType("id", new IntegerType());
        rules.addType("login", new Required());
        rules.addType("login", new StringType());
        rules.addType("email", new Required());
        rules.addType("email", new EmailType());
        rules.addType("name", new StringType());
    }
    
    
    /**
     * Returns item fields
     */
    Vector<string> getItemFields(string action) =>
    [
        "id",
        "login",
        "email",
        "name",
        "gmtime_add",
        "gmtime_edit",
    ];
    
    
    /**
     * Returns save fields
     */
    Vector<string> getSaveFields() =>
    [
        "login",
        "email",
        "password",
        "name",
    ];
    
    
    /**
     * Save before
     */
    async void onSaveBefore()
    {
        await parent();
        
        // Хеширование пароля при создании или изменении
        if (this.item.isNew() || this.update_data.has("password"))
        {
            string password = this.update_data.get("password");
            string hashed_password = await Password::createHash(password);
            this.item.set("password", hashed_password);
        }
    }
    
    
    /**
     * Delete before (Soft Delete)
     */
    async void onDeleteBefore()
    {
        await parent();
        // Вместо физического удаления помечаем как удаленное
        this.item.set("is_deleted", 1);
    }
    
    
    /**
     * Delete action
     */
    @ApiMethod{ "name": "delete" }
    async void actionDelete()
    {
        this.setAction("delete");
        this.filterData();
        
        Map pk = this.request.get("pk");
        if (pk) this.setPrimaryKey(pk);
        
        await this.findOrCreate();
        
        // Вызываем onDeleteBefore для soft delete
        await this.onDeleteBefore();
        
        // Сохраняем изменения (так как is_deleted изменился)
        await this.item.save();
        
        this.success();
    }
}
```

### 2.4. Регистрация API

Файл: `src/lib/Runtime.Cabinet/bay/ModuleDescription.bay`

Пример регистрации API через `CabinetProvider` (рекомендуемый способ) или напрямую в entities.

```baylang
namespace Runtime.Cabinet;

use Runtime.Entity.Entity;
use Runtime.Cabinet.Providers.CabinetProvider;

class ModuleDescription
{
    // ... остальные методы ...
    
    /**
     * Returns module entities
     */
    pure Vector<Entity> entities() =>
    [
        CabinetProvider::hook(),
        // Можно добавить API напрямую, если Provider не поддерживает:
        #ifdef BACKEND then
        new Api("Runtime.Cabinet.Api.UserSearchApi"),
        new Api("Runtime.Cabinet.Api.UserSaveApi"),
        #endif
    ];
}
```

## 3. Структура компонента

### 3.1. Модель (Manager)

Файл: `src/lib/Runtime.Cabinet/bay/Components/Pages/User/UserModel.bay`

```baylang
namespace Runtime.Cabinet.Components.Pages.User;

use Runtime.BaseModel;
use Runtime.Serializer.IntegerType;
use Runtime.Serializer.ObjectType;
use Runtime.Serializer.StringType;
use Runtime.Serializer.VectorType;
use Runtime.Web.RenderContainer;
use Runtime.Widget.Table.TableManager;
use Runtime.Cabinet.Components.Pages.User.User;

class UserModel extends BaseModel
{
    string component = classof User;
    TableManager manager = null;
    
    
    /**
     * Serialize object
     */
    static void serialize(ObjectType rules)
    {
        parent(rules);
        rules.addType("manager", new ObjectType());
    }
    
    
    /**
     * Init widget
     */
    void initWidget(Map params)
    {
        parent(params);
        
        this.manager = this.createWidget(classof TableManager, {
            "autoload": true,
            "api_name": "runtime.cabinet.user",
            "page_name": "p",
            "title": method this.getTableTitle,
            "primary_rules":
            {
                "id": new IntegerType(),
            },
            "item_rules":
            {
                "id": new IntegerType(),
                "login": new StringType(),
                "email": new StringType(),
                "name": new StringType(),
            },
            "form_fields":
            [
                {
                    "name": "login",
                    "label": "Login",
                    "component": "Runtime.Widget.Input",
                },
                {
                    "name": "email",
                    "label": "Email",
                    "component": "Runtime.Widget.Input",
                },
                {
                    "name": "name",
                    "label": "Name",
                    "component": "Runtime.Widget.Input",
                },
                {
                    "name": "password",
                    "label": "Password",
                    "component": "Runtime.Widget.Input",
                    "props": {
                        "type": "password"
                    }
                },
            ],
            "table_fields":
            [
                {
                    "name": "row_number",
                },
                {
                    "name": "login",
                    "label": "Login",
                },
                {
                    "name": "email",
                    "label": "Email",
                },
                {
                    "name": "name",
                    "label": "Name",
                },
                {
                    "name": "buttons",
                    "slot": "row_buttons",
                }
            ],
        });
    }
    
    
    /**
     * Returns table title
     */
    string getTableTitle(string action, Map item)
    {
        if (action == "add") return "Add User";
        else if (action == "edit") return "Edit User";
        else if (action == "delete") return "Delete User";
        else if (action == "delete_message") return "Are you sure you want to delete this user?";
        return "Users";
    }
    
    
    /**
     * Build page title
     */
    void buildTitle(RenderContainer container)
    {
        this.layout.setPageTitle("Users");
    }
}
```

### 3.2. Компонент (View)

Файл: `src/lib/Runtime.Cabinet/bay/Components/Pages/User/User.bay`

```baylang
<class name="Runtime.Cabinet.Components.Pages.User.User">

<use name="Runtime.Widget.Button" component="true" />
<use name="Runtime.Widget.RowButtons" component="true" />
<use name="Runtime.Widget.Table.TableWrap" component="true" />

<style lang="scss">
.user_page{
    padding-top: 20px;
    
    &__table{
        width: 100%;
    }
    
    &__button{
        margin-right: 5px;
    }
}
</style>

<template>
    <div class="page user_page">
        <TableWrap model={{ this.model.manager }}>
            <slot name="top_buttons">
                <RowButtons>
                    <Button class="button--success user_page__button"
                        @event:click="this.model.manager.showAddDialog()"
                    >Add User</Button>
           </RowButtons>
            </slot>
            <slot name="row_buttons" args="Map item, Map field, int row_number">
                <RowButtons>
                    <Button class="button--small user_page__button"
                        @event:click="this.model.manager.showEditDialog(item.copy())"
                    >Edit</Button>
                    <Button class="button--small button--danger user_page__button"
                        @event:click="this.model.manager.showDeleteDialog(item.copy())"
                    >Delete</Button>
                </RowButtons>
            </slot>
        </TableWrap>
    </div>
</template>

</class>
```

## 4. Требования к стилям

-   Использовать CSS переменные (если применимо).
-   Адаптивность: интерфейс должен выглядеть корректно на мобильных устройствах и планшетах.
-   Современный и чистый дизайн.
-   Использовать БЭМ-нотацию для классов (например, `user_page`, `user_page__table`, `user_page__button`).

## 5. Проверка

-   [ ] Компонент `User` корректно отображает таблицу пользователей.
-   [ ] Кнопка "Add User" открывает диалог добавления пользователя.
-   [ ] Кнопка "Edit" открывает диалог редактирования пользователя.
-   [ ] Кнопка "Delete" открывает диалог подтверждения удаления.
-   [ ] Данные загружаются через SearchApi.
-   [ ] Данные сохраняются/удаляются через SaveApi.
-   [ ] Стили соответствуют БЭМ-нотации.
-   [ ] Интерфейс адаптивен.

## 6. Примерная структура файлов

```
src/lib/Runtime.Cabinet/bay/
├── Api/
│   ├── UserSearchApi.bay
│   └── UserSaveApi.bay
├── Components/
│   └── Pages/
│       └── User/
│           ├── User.bay (Компонент)
│           └── UserModel.bay (Модель)
├── Database/
│   └── User.bay (Существует)
└── ModuleDescription.bay (Существует)
```

## 7. Примечания

-   В компоненте использовать `use name="Runtime.Widget.Table.TableWrap" component="true"`.
-   В модели использовать `use name="Runtime.Widget.Table.TableManager"`.
-   Для диалогов используйте встроенные возможности `TableManager` (showAddDialog, showEditDialog, showDeleteDialog).
-   Для работы с паролями в `onSaveBefore` методе `UserSaveApi` используется `Runtime.Crypt.Password::createHash`.
-   Используется **Soft Delete** (логическое удаление) через поле `is_deleted` вместо физического удаления записи.
