# Техническое задание: Удаление и редактирование чатов в списке SelectList

## Общее описание

В проекте используется компонент `SelectList` для отображения списков чатов и групп чатов. В текущей реализации компонент `SelectList` уже поддерживает функциональность редактирования и удаления элементов через параметры `allow_edit` и `allow_delete`. Однако в компоненте `ChatPage` для списка чатов (в области чата) эти параметры не включены, в то время как для списка групп чатов (в сайдбаре) они включены.

Цель задачи — добавить возможность редактирования и удаления чатов в списке чатов (в области чата), аналогично тому, как это реализовано для групп чатов.

## Анализ текущей реализации

### 1. Компонент `SelectList`

Расположение: `src/lib/Runtime.AI/bay/Cabinet/Components/Chat/SelectList.bay`

Компонент `SelectList` уже поддерживает:
- Отображение списка элементов
- Выбор элемента
- Добавление нового элемента (через `add_message`)
- Редактирование элемента (при `allow_edit="true"`)
- Удаление элемента (при `allow_delete="true"`)

При редактировании или удалении компонент генерирует события:
- `editMessage` с данными элемента
- `deleteMessage` с данными элемента

### 2. Компонент `ChatPage`

Расположение: `src/lib/Runtime.AI/bay/Cabinet/Components/Chat/ChatPage.bay`

В компоненте `ChatPage` есть два использования `SelectList`:

#### 2.1. Список групп чатов (в сайдбаре)

```xml
<SelectList
    options={{ this.groupOptions }}
    value={{ this.model.selected_group ? this.model.selected_group.id : 0 }}
    select_message="All Groups"
    add_message="Create Group"
    direction="down"
    allow_edit="true"
    allow_delete="true"
    @event:valueChange="this.model.selectGroupById(event.value)"
    @event:addMessage="this.model.showAddGroup()"
    @event:editMessage="this.model.showEditGroup(event.data.get('item'))"
    @event:deleteMessage="this.model.showDeleteGroup(event.data.get('item'))"
/>
```

Здесь параметры `allow_edit` и `allow_delete` установлены в `"true"`, и обрабатываются события редактирования и удаления.

#### 2.2. Список чатов (в области чата)

```xml
<SelectList
    value={{ this.model.selected_chat ? this.model.selected_chat.id : null }}
    options={{ this.chatOptions }}
    select_message="New chat"
    @event:addMessage="this.model.selectChatById(null)"
    @event:valueChange="this.model.selectChatById(event.value)"
/>
```

Здесь параметры `allow_edit` и `allow_delete` не установлены (по умолчанию `"false"`), и события редактирования и удаления не обрабатываются.

### 3. Модель `ChatPageModel`

Расположение: `src/lib/Runtime.AI/bay/Cabinet/Components/Chat/ChatPageModel.bay`

В модели `ChatPageModel` уже реализована логика для работы с группами чатов:
- `showEditGroup(ChatGroup group)` — показ диалога редактирования группы
- `showDeleteGroup(ChatGroup group)` — показ диалога подтверждения удаления группы
- `deleteGroup()` — удаление группы через API
- `saveGroup()` — сохранение группы через API

Для чатов аналогичной логики нет.

### 4. API для работы с чатами

Расположение: `src/lib/Runtime.AI/bay/Cabinet/Api/`

В проекте существуют следующие API для работы с чатами:
- `ChatSearchApi.bay` — API для поиска и получения чатов
- `ChatApi.bay` — API для отправки сообщений в чат

Однако отсутствует `ChatSaveApi.bay` для создания и обновления чатов, а также отсутствует метод удаления чатов.

В других частях проекта (в `src/lib/Runtime.AI/bay/Api/Chat/`) существуют API `ChatSave.bay` и `ChatDelete.bay`, но они используют другую структуру и не соответствуют стандартам Cabinet API.

## Задача

Добавить возможность редактирования и удаления чатов в списке чатов (в области чата) аналогично группам чатов.

## Требования

### 1. Создать `ChatSaveApi.bay` для Cabinet API

Создать новый файл `src/lib/Runtime.AI/bay/Cabinet/Api/ChatSaveApi.bay` со следующим содержимым:

```bay
/*!
 *  BayLang AI
 *
 *  (c) Copyright 2026 "Ildar Bikmamatov" <support@bayrell.org>
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *      https://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */

namespace Runtime.AI.Cabinet.Api;

use Runtime.AI.Database.Chat;
use Runtime.Auth.Models.UserData;
use Runtime.Cabinet.CabinetMiddleware;
use Runtime.Web.Annotations.ApiMethod;
use Runtime.Widget.Api.SaveApi;
use Runtime.Web.Middleware;
use Runtime.ORM.Query;
use Runtime.Serializer.IntegerType;
use Runtime.Serializer.Required;
use Runtime.Serializer.MapType;
use Runtime.Serializer.StringType;


class ChatSaveApi extends SaveApi
{
	int user_id = 0;
	
	
	/**
	 * Returns api name
	 */
	pure string getApiName() => "cabinet.ai.chat";
	
	
	/**
	 * Returns record name
	 */
	pure string getRecordName() => classof Chat;
	
	
	/**
	 * Returns middleware
	 */
	Vector<Middleware> getMiddleware() =>
	[
		new CabinetMiddleware(),
	];
	
	
	/**
	 * Set user data
	 */
	void setUser(UserData user_data)
	{
		this.user_id = this.user_data.user.get("id");
	}
	
	
	/**
	 * Returns data rules
	 */
	void getDataRules(MapType rules)
	{
	}
	
	
	/**
	 * Returns item rules
	 */
	void getItemRules(MapType rules)
	{
		rules.addType("title", new Required());
		rules.addType("title", new StringType());
		rules.addType("group_id", new IntegerType());
	}
	
	
	/**
	 * Returns item fields
	 */
	Vector<string> getItemFields(string action) =>
	[
		"id",
		"user_id",
		"group_id",
		"title",
		"gmtime_add",
		"gmtime_edit",
	];
	
	
	/**
	 * Build query
	 */
	async void buildQuery(Query q)
	{
		await parent(q);
	}
	
	
	/**
	 * Save before
	 */
	async void onSaveBefore()
	{
		await parent();
		
		/* Add user id */
		if (this.item.isNew())
		{
			this.item.set("user_id", this.user_id);
		}
	}
	
	
	/**
	 * Action save
	 */
	@ApiMethod{ "name": "save" }
	async void actionSave()
	{
		await parent();
	}
	
	
	/**
	 * Action delete
	 */
	@ApiMethod{ "name": "delete" }
	async void actionDelete()
	{
		await parent();
	}
}
```

### 2. Изменения в компоненте `ChatPage`

#### 2.1. Добавить параметры `allow_edit` и `allow_delete` в `SelectList` для чатов

В шаблоне `renderChatArea` изменить использование `SelectList` для чатов:

```xml
<SelectList
    value={{ this.model.selected_chat ? this.model.selected_chat.id : null }}
    options={{ this.chatOptions }}
    select_message="New chat"
    allow_edit="true"
    allow_delete="true"
    @event:addMessage="this.model.selectChatById(null)"
    @event:valueChange="this.model.selectChatById(event.value)"
    @event:editMessage="this.model.showEditChat(event.data.get('item'))"
    @event:deleteMessage="this.model.showDeleteChat(event.data.get('item'))"
/>
```

### 3. Изменения в модели `ChatPageModel`

#### 3.1. Добавить поля для работы с диалогами редактирования и удаления чатов

Добавить следующие поля в класс `ChatPageModel`:

```bay
/* Chat management fields */
DialogModel chat_dialog = null;
ConfirmDialogModel chat_delete_dialog = null;
FormModel chat_form = null;
string chat_dialog_title = "";
Chat selected_chat_for_deletion = null;
```

#### 3.2. Инициализировать диалоги в методе `initWidget`

В методе `initWidget` добавить инициализацию диалогов для чатов:

```bay
/* Initialize chat dialog */
this.chat_dialog = this.createWidget(
    classof DialogModel,
    {
        "content_width": 400,
    }
);

/* Initialize chat delete dialog */
this.chat_delete_dialog = this.createWidget(
    classof ConfirmDialogModel,
    {
        "content_width": 400,
    }
);

/* Initialize chat form */
this.chat_form = this.createWidget(
    classof FormModel,
    {
        "primary_rules": new MapType
        {
            "id": new IntegerType(),
        },
        "fields": [
            {
                "name": "title",
                "label": "Title",
                "required": true,
                "component": "Runtime.Widget.Input",
            },
        ],
    }
);
```

#### 3.3. Добавить методы для работы с чатами

Добавить следующие методы в класс `ChatPageModel`:

```bay
/**
 * Show add chat dialog
 */
void showAddChat()
{
    this.chat_dialog_title = "Create Chat";
    
    if (this.chat_form) this.chat_form.clear();
    if (this.chat_dialog)
    {
        this.chat_dialog.show();
    }
}

/**
 * Show edit chat dialog
 */
void showEditChat(Chat chat)
{
    if (not chat) return;
    
    this.chat_dialog_title = "Edit Chat";
    
    if (this.chat_form)
    {
        this.chat_form.clear();
        this.chat_form.setPrimaryKey({"id": chat.id});
        this.chat_form.setItem({
            "id": chat.id,
            "title": chat.title,
        });
    }
    
    if (this.chat_dialog)
    {
        this.chat_dialog.show();
    }
}

/**
 * Show delete chat dialog
 */
async void showDeleteChat(Chat chat)
{
    if (not chat) return;
    
    this.selected_chat_for_deletion = chat;
    
    if (this.chat_delete_dialog)
    {
        this.chat_delete_dialog.show();
    }
}

/**
 * Delete chat
 */
async void deleteChat()
{
    if (not this.selected_chat_for_deletion) return;
    
    this.chat_delete_dialog.setWaitMessage("Deleting...");
    
    ApiResult result = await this.layout.sendApi({
        "api_name": "cabinet.ai.chat",
        "method_name": "delete",
        "data": {
            "pk": {
                "id": this.selected_chat_for_deletion.id,
            }
        },
    });
    
    this.chat_delete_dialog.setApiResult(result);
    
    if (result.isSuccess())
    {
        if (this.chat_delete_dialog) this.chat_delete_dialog.hide();
        await this.loadChats();
    }
}

/**
 * Save chat
 */
async void saveChat()
{
    if (not this.chat_form) return;
    
    this.chat_form.setWaitMessage("Saving...");
    
    Map values = this.chat_form.item;
    
    ApiResult result = await this.layout.sendApi({
        "api_name": "cabinet.ai.chat",
        "method_name": "save",
        "data": {
            "pk": this.chat_form.pk,
            "item": values,
        },
    });
    
    this.chat_form.setApiResult(result);
    
    if (result.isSuccess())
    {
        if (this.chat_dialog) this.chat_dialog.hide();
        await this.loadChats();
    }
}
```

### 4. Изменения в шаблоне `ChatPage`

#### 4.1. Добавить диалоги для чатов

Добавить в компонент `ChatPage` шаблоны для диалогов редактирования и удаления чатов (аналогично группам):

```xml
<template name="renderChatDialog">
    <Dialog class="chat_dialog"
        model={{ this.model.chat_dialog }}
    >
        <slot name="title">
            {{ this.model.chat_dialog_title }}
        </slot>
        <slot name="content">
            <Form
                model={{ this.model.chat_form }}
                fields={{ this.model.chat_form.fields }}
            />
        </slot>
        <slot name="footer">
            <RowButtons>
                <Button
                    class="button button--primary"
                    @event:click="this.model.saveChat()"
                >
                    Save
                </Button>
                <Button
                    class="button"
                    @event:click="this.model.chat_dialog.hide()"
                >
                    Hide
                </Button>
            </RowButtons>
        </slot>
    </Dialog>
</template>

<template name="renderChatDeleteDialog">
    <Dialog class="chat_delete_dialog"
        model={{ this.model.chat_delete_dialog }}
    >
        <slot name="title">
            Delete Chat
        </slot>
        <slot name="content">
            <p>Are you sure you want to delete the chat "{{ this.model.selected_chat_for_deletion ? this.model.selected_chat_for_deletion.title : "" }}"?</p>
            %render this.renderWidget(this.model.chat_delete_dialog.result);
        </slot>
        <slot name="footer">
            <RowButtons>
                <Button
                    class="button button--danger"
                    @event:click="this.model.deleteChat()"
                >
                    Delete
                </Button>
                <Button
                    class="button"
                    @event:click="this.model.chat_delete_dialog.hide()"
                >
                    Cancel
                </Button>
            </RowButtons>
        </slot>
    </Dialog>
</template>
```

#### 4.2. Включить диалоги в основной шаблон

Изменить основной шаблон компонента `ChatPage`:

```xml
<template>
    <div class="chat_page">
        %render this.renderSideBar();
        %render this.renderChatArea();
        %render this.renderGroupDialog();
        %render this.renderGroupDeleteDialog();
        %render this.renderChatDialog();
        %render this.renderChatDeleteDialog();
    </div>
</template>
```

### 5. Включить кнопку добавления чата

В шаблоне `renderChatArea` в `SelectList` для чатов добавить параметр `add_message` и обработчик события `addMessage`:

```xml
<SelectList
    value={{ this.model.selected_chat ? this.model.selected_chat.id : null }}
    options={{ this.chatOptions }}
    select_message="New chat"
    add_message="Create Chat"
    allow_edit="true"
    allow_delete="true"
    @event:addMessage="this.model.showAddChat()"
    @event:valueChange="this.model.selectChatById(event.value)"
    @event:editMessage="this.model.showEditChat(event.data.get('item'))"
    @event:deleteMessage="this.model.showDeleteChat(event.data.get('item'))"
/>
```

## План реализации

1. **Создать API `ChatSaveApi.bay`**
   - Создать файл `src/lib/Runtime.AI/bay/Cabinet/Api/ChatSaveApi.bay`
   - Реализовать методы `save` и `delete` для работы с чатами

2. **Изменить компонент `ChatPage`**
   - Добавить параметры `allow_edit` и `allow_delete` в `SelectList` для чатов
   - Добавить параметр `add_message` и обработчик `addMessage`
   - Добавить обработку событий `editMessage` и `deleteMessage`
   - Добавить шаблоны диалогов для чатов
   - Включить диалоги в основной шаблон

3. **Изменить модель `ChatPageModel`**
   - Добавить поля для диалогов и форм чатов
   - Инициализировать диалоги в `initWidget`
   - Добавить методы для работы с чатами (`showAddChat`, `showEditChat`, `showDeleteChat`, `deleteChat`, `saveChat`)

4. **Протестировать функциональность**
   - Проверить отображение иконок редактирования и удаления в списке чатов
   - Проверить открытие диалогов редактирования и удаления
   - Проверить сохранение и удаление чатов через API
   - Проверить обновление списка чатов после операций

## Примечания

- Логика работы с чатами должна быть аналогична логике работы с группами чатов
- При редактировании чата можно изменить только название (поле `title`)
- При удалении чата должно быть диалоговое окно подтверждения
- После успешного сохранения или удаления чата список чатов должен обновляться
- API `ChatSaveApi.bay` должен использовать те же методы и структуру, что и `ChatGroupSaveApi.bay`
