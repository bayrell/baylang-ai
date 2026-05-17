# Model Description

Добавить описание модели после Select. Сделать изменения в ModelPageModel.bay.

Нужно сделать отдельный компонент в Blocks ChooseModel.bay. Который будет принимать model это SelectModel с выбором модели.

Компонент ChooseModel.bay должен содержать Select и описание модели. При изменении значения в Select нужно отправлять событие valueChange. В SelectModel в options есть item, который является ModelInfo и там есть description.

# ModelInfo

В modelNames в ModelPageModel нужно добавить item. Нужно создать ModelInfo dto в Models, который будет хранить item.

Свойства item: id, name, description, context_length

В Model/Provider.bay dto модели есть Vector models, нужно будет сделать Vector<ModelInfo>

## Описание файла ModelInfo.bay

Создать файл src/lib/Runtime.AI/bay/Models/ModelInfo.bay с описанием модели:

```bay
namespace Runtime.AI.Models;

use Runtime.BaseDTO;
use Runtime.Serializer.IntegerType;
use Runtime.Serializer.ObjectType;
use Runtime.Serializer.StringType;


class ModelInfo extends BaseDTO
{
	int id = 0;
	string name = "";
	string description = "";
	int context_length = 0;
	
	/**
	 * Serialize object
	 */
	static void serialize(ObjectType rules)
	{
		parent(rules);
		rules.addType("id", new IntegerType());
		rules.addType("name", new StringType());
		rules.addType("description", new StringType());
		rules.addType("context_length", new IntegerType());
	}
}
```

## Описание файла ChooseModel.bay

Создать файл src/lib/Runtime.AI/bay/Cabinet/Components/Blocks/ChooseModel.bay с компонентом выбора модели:

use Runtime.Widget.Select;
use Runtime.Widget.SelectModel;
use Runtime.Widget.Messages.ValueChangeMessage;
use Runtime.AI.Models.ModelInfo;

```bay
<class name="Runtime.AI.Cabinet.Components.Blocks.ChooseModel">

<template>
	<div class="choose_model">
		<Select
			model={{ this.model }}
			value={{ this.value }}
			@event:valueChange="this.onValueChange(event)"
		/>
		<div class="model_description">
			{{ this.description }}
		</div>
	</div>
</template>

<script>

props SelectModel model = null;

computed string description()
{
	Map option = this.model.getOption(this.value);
	if (option == null or not option.has("item")) return "";
	
	var item = option.get("item");
	if (not (item instanceof ModelInfo)) return "";
	
	return item.description;
}

void onValueChange(ValueChangeMessage message)
{
	this.emit(message);
}

</script>

</class>
```

## Изменения в ModelPageModel.bay

В файле src/lib/Runtime.AI/bay/Cabinet/Components/Models/ModelPageModel.bay нужно:

1. В методе initWidget изменить создание modelNames с параметром item:

```bay
// В initWidget добавить создание modelNames с item
this.modelNames = this.createWidget(classof SelectModel, {
	"options_type":
	{
		"item": new ObjectType{
			"class_name": classof ModelInfo,
		}
	}
});
```

2. В методе loadModelNamesOptions добавить item с ModelInfo:

```bay
// В loadModelNamesOptions добавить ModelInfo
void loadModelNamesOptions(Vector<Map> items = [])
{
	Vector<Map> options = [];
	
	if (items != null && items.count() > 0)
	{
		for (Map item in items)
		{
			ModelInfo modelInfo = ModelInfo::create({
				"id": item.get("id"),
				"name": item.get("name"),
				"description": item.get("description", ""),
				"context_length": item.get("context_length", 0),
			});
			
			options.push({
				"key": item.get("id"),
				"value": item.get("id"),
				"item": modelInfo,
			});
		}
	}
	
	/* Sort options by name */
	options.sort(int (Map a, Map b) => a.get("value").localeCompare(b.get("value")));
	
	this.modelNames.setOptions(options);
}
```

3. В методе initWidget изменить поле model_name в form_fields на использование ChooseModel:

```bay
// В form_fields изменить поле model_name:
{
	"name": "model_name",
	"label": "Имя модели",
	"component": "Runtime.AI.Cabinet.Components.Blocks.ChooseModel",
	"props":
	{
		"model": this.modelNames,
	}
},
```

## Изменения в Provider.bay

В файле src/lib/Runtime.AI/bay/Models/Provider.bay нужно изменить тип models с Vector на Vector<ModelInfo>:

```bay
// Было:
Vector models = [];

// Стало:
Vector<ModelInfo> models = [];

// В serialize изменить rules.addType:
rules.addType("models", new VectorType(new ObjectType{
	"class_name": classof ModelInfo,
}));
```

## Пример использования ChooseModel

```bay
// В компоненте:
SelectModel modelNames = null;

// В initWidget:
this.modelNames = this.createWidget(classof SelectModel, {
	"options_type":
	{
		"item": new ObjectType{
			"class_name": classof ModelInfo,
		}
	}
});

// В обработчике:
void onModelChange(ValueChangeMessage message)
{
	// Обработка изменения модели
}
```

## Задачи

1. Создать файл ModelInfo.bay с описанием модели
2. Создать файл ChooseModel.bay с компонентом выбором модели
3. Изменить ModelPageModel.bay для использования ChooseModel
4. Изменить Provider.bay для использования Vector<ModelInfo>
5. Протестировать работу компонента
