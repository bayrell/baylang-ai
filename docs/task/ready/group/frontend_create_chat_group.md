# Техническое задание: Доработка фронтенда для групп чатов

## Статус документа
В ожидании разработки

---

## 1. Общее описание
Необходимо интегрировать систему групп чатов в интерфейс страницы `ChatPage`. Это включает добавление селектора групп в боковую панель, реализацию модального окна для создания/редактирования групп и обновление логики работы с чатами для учета групп.

## 2. Цели и задачи

### Цели
- Интегрировать группы чатов в пользовательский интерфейс.
- Упростить управление чатами через группировку.
- Обеспечить создание и редактирование групп непосредственно из интерфейса чатов.

### Задачи
1.  **Модернизация `ChatPageModel`:**
    *   Добавить поле `groups` для хранения списка групп.
    *   Добавить поле `selected_group` для отслеживания выбранной группы.
    *   Реализовать методы загрузки групп (`loadGroups`).
    *   Реализовать метод создания группы (`createGroup`).
    *   Обновить метод `loadChats` для фильтрации по выбранной группе.
    *   Добавить диалоговое окно модель для создания и редактирования группы. Использовать Runtime.Widget.Dialog.DialogModel
    *   Добавить форму модель для создания и редактирования группы, которая будет отображаться в диалоговом окне. Использовать Runtime.Wiget.Form.FormModel
    *   Реализовать метод saveGroup для сохранения группы и добавления через api
2.  **Обновление компонента `ChatPage`:**
    *   Добавить селектор групп (используя компонент `SelectList`).
    *   Добавить кнопку "Создать группу".
    *   Реализовать отображение чатов, принадлежащих выбранной группе.
    *   Реализовать отдельный template для отображения диалогового окна с формой редактирования группы
3.  **Обновление `SelectList`:**
    *   Добавить поддержку кнопки "Создать" (опционально, через emit или пропсы).

---

## 3. Детальное описание изменений

### 3.1. `ChatPageModel.bay`
**Расположение:** `src/lib/Runtime.AI/bay/Cabinet/Components/Chat/ChatPageModel.bay`

#### Изменения:
1.  **Добавить поля:**
    *   `Vector<ChatGroup> groups = [];`
    *   `ChatGroup selected_group = null;`
    *   `DialogModel group_dialog = null;` (для управления состоянием диалога)
    *   `FormModel group_form = null`;

Инициировать параметры group_dialog и group_form в initWidget

2.  **Обновить метод `loadData`:**
    *   Добавить вызов `await this.loadGroups();`

3.  **Создать метод `loadGroups`:**
    *   Вызов API `cabinet.ai.chat.group` (метод `search`).
    *   Обновление поля `groups`.

4.  **Создать метод `selectGroup`:**
    *   Установка `selected_group`.
    *   Фильтрация списка чатов в компоненте по group_id

5.  **Создать методы управления диалогом:**
    *   `showAddGroup` - открытие диалога редактирования группы
    *   `showEditGroup` - редактирования группы
    *   `showDeleteGroup` - удаление группы
    *   `saveGroup` - отправка данных на API `ChatGroupSaveApi`.


**Пример (псевдокод):**
```bay
/* Поля */
Vector<ChatGroup> groups = [];
ChatGroup selected_group = null;
DialogModel group_dialog = null;

/* Метод загрузки групп */
async void loadGroups()
{
    ApiResult result = await this.layout.sendApi({
        "api_name": "cabinet.ai.chat.group",
        "method_name": "search",
        "data": {},
    });
    
    if (result.isSuccess())
    {
        this.setValue("groups", result.data.get("items"));
    }
}

/* Метод выбора группы */
async void selectGroup(ChatGroup group)
{
    this.selected_group = group;
}
```

### 3.2. `ChatPage.bay`
**Расположение:** `src/lib/Runtime.AI/bay/Cabinet/Components/Chat/ChatPage.bay`

#### Изменения:
1.  **Обновить шаблон `renderSideBar`:**
    *   Добавить блок для выбора группы (используя `SelectList`).
    *   Добавить кнопку "Создать группу" (иконка плюса).
    *   Обновить список чатов для отображения только чатов выбранной группы (опционально, фильтрация на фронтенде по selected_group.id).

2.  **Использовать компонент `SelectList`:**
    *   Передать `options` (список групп в формате `{"key": id, "value": name}`).
    *   Обработать событие `ValueChangeMessage` для вызова `selectGroup`.

3.  **Добавить диалог создания группы:**
    *   Использовать компонент `Runtime.Widget.Dialog.Dialog`
    *   Внутри диалога разместить форму (поля: Название, Описание).

**Пример (псевдокод шаблона):**
```html
<div class="chat_sidebar">
    <!-- Блок выбора группы -->
    <div class="chat_group_selector">
        <SelectList
            options={{ this.groupOptions }}
            value={{ this.model.selected_group ? this.model.selected_group.id : 0 }}
            select_message="Все группы"
            add_message="Добавить новую группу"
            @event:addClick="this.model.showAddGroupDialog()"
            @event:valueChange="this.model.selectGroupById(event.value)"
        />
    </div>

    <!-- Список чатов -->
    <div class="chat_sidebar__list">
        <!-- ... existing chat list logic ... -->
    </div>
</div>

%render this.renderGroupDialog()

<script>
computed Vector groupOptions()
{
    return this.model.groups.map(Map (ChatGroup g) => {"key": g.id, "value": g.name});
}
</script>
```

### 3.3. `SelectList.bay` (Опционально)
**Расположение:** `src/lib/Runtime.AI/bay/Cabinet/Components/Chat/SelectList.bay`

#### Изменения:
*   Если в проекте нет поддержки кнопки "Создать" внутри селекта, можно добавить пропс `add_message` и обработчик события `add`.
*   При нажатии на элемент "Добавить" (если `add_message` задано) компонент должен эмитить событие `addClick`.

Использовать Runtime.AI.Cabinet.Components.Blocks.Icon для иконки plus

**Пример изменений:**

Использовать Runtime.Message

```html
<!-- В шаблоне SelectList -->
<div class="select_list_items" ... >
    <!-- ... existing items ... -->
    %if (this.add_message)
    {
        <div class="select_list_item add_item"
            @event:click="this.add()"
        >
            {{ this.add_message }}
        </div>
    }
</div>
```

```bay
// В скрипте SelectList
props string add_message = "";
// ...
void add()
{
    this.emit(new Message{
        "name": "addMessage"
    });
    this.is_open = false;
}
```

---

## 4. План тестирования

1.  **Загрузка групп:**
    *   Проверить, что список групп загружается при открытии страницы.
2.  **Выбор группы:**
    *   Проверить, что при выборе группы обновляется список чатов (фильтрация).
3.  **Создание группы:**
    *   Открыть диалог создания группы.
    *   Заполнить поля (Название, Описание).
    *   Сохранить. Проверить, что группа появилась в списке.
4.  **Редактирование группы:**
    *   Открыть диалог редактирования существующей группы.
    *   Изменить данные.
    *   Сохранить. Проверить обновление данных в списке.
5.  **Удаление группы:**
    *   (Если реализовано в API) Попробовать удалить группу. Проверить реакцию интерфейса.

---

## 5. Зависимости

1.  **Backend API:**
    *   `cabinet.ai.chat.group` (search, save) - должно быть готово и протестировано.
2.  **Компоненты UI:**
    *   `SelectList` - должен поддерживать пропсы `options`, `value`, `select_message` и событие `value_change`.
    *   `Runtime.Widget.Dialog.Dialog` - для отображения модального окна
3.  **Модели данных:**
    *   `ChatGroup` (DTO) - должен содержать поля `id`, `name`, `description`.


---

## 7. Примечания

*   Для удобства пользователя можно добавить иконки к кнопкам (создание, редактирование, удаление).
*   При создании группы через селектор (кнопка "+") можно сразу открывать диалог создания.
*   Убедитесь, что стили диалога соответствуют общему дизайну приложения.
*   Если в проекте уже есть компонент `Dialog`, используйте его вместо создания собственного `ChatGroupDialog`.