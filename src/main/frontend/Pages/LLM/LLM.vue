<style lang="scss" scoped>
.llm_settings{
	max-width: 500px;
	margin: 0 auto;
	&__buttons{
		margin-bottom: 10px;
	}
	.llm_item{
		&__button{
			display: flex;
			gap: 10px;
			span{
				cursor: pointer;
			}
		}
	}
}
</style>

<template>
	<div class="llm_settings">
		<h1>LLM List</h1>
		<div class="llm_settings__buttons">
			<Button @click="showAdd">Add</Button>
		</div>
		<table class="table table--border">
			<tbody>
				<tr class="table__header">
					<th></th>
					<th>Name</th>
					<th></th>
				</tr>
				<tr class="table__row" v-for="item, index in items" :key="item.id">
					<td>{{ index + 1 }}</td>
					<td class="llm_item__title">{{ item.name }}</td>
					<td class="llm_item__button">
						<span @click="showEdit(item.id)">[Edit]</span>
						<span @click="showDelete(item.id)">[Delete]</span>
					</td>
				</tr>
			</tbody>
		</table>
		<Dialog v-model="dialog">
			<template v-slot:header>
				Add LLM
			</template>
			<template v-slot:content>
				<Field
					name="type"
					:error="model.form.getFieldError('item.type')"
				>
					<label for="name">Type</label>
					<Input
						type="select"
						name="type"
						v-if="model.form.pk == null"
						v-model="model.form.item.type"
						:options="getTypes()"
					/>
					<div v-else>{{ getType(model.form.item.type) }}</div>
				</Field>
				<Field name="name" :error="model.form.getFieldError('item.name')">
					<label for="name">Name</label>
					<Input name="name" v-model="model.form.item.name" />
				</Field>
				<FieldContent />
				<Result v-model="model.form.result" />
			</template>
			<template v-slot:buttons>
				<Button class="primary" @click="saveItem" v-if="model.form.pk == null">Add</Button>
				<Button class="success" @click="saveItem" v-if="model.form.pk != null">Save</Button>
				<Button class="default" @click="dialog.hide()">Close</Button>
			</template>
		</Dialog>
		<Dialog v-model="remove_dialog">
			<template v-slot:header>
				Remove item
			</template>
			<template v-slot:content>
				Do you realy want to delete item '{{ remove_dialog.data.name }}'?
				<Result v-model="remove_dialog.result" />
			</template>
			<template v-slot:buttons>
				<Button class="danger" @click="deleteItem">Delete</Button>
				<Button class="default" @click="remove_dialog.hide()">Close</Button>
			</template>
		</Dialog>
	</div>
</template>

<script lang="js">
import Button from "@main/Components/Button.vue";
import Input from "@main/Components/Input.vue";
import Dialog from "@main/Components/Dialog/Dialog.vue";
import DialogModel from "@main/Components/Dialog/DialogModel.js";
import Field from "@main/Components/Form/Field.vue";
import Result from "@main/Components/Form/Result.vue";
import FieldContent from "./FieldContent.vue";

export default
{
	name: "LLM",
	components: {
		Button,
		Field,
		FieldContent,
		Input,
		Dialog,
		Result,
	},
	data: function(){
		return {
			dialog: new DialogModel(),
			remove_dialog: new DialogModel(),
		};
	},
	computed:
	{
		model: function()
		{
			return this.layout.llm_page;
		},
		items: function()
		{
			return this.model.items;
		}
	},
	mounted()
	{
		this.model.load();
	},
	methods:
	{
		getTypes()
		{
			return [
				{"key": "ollama", "value": "Ollama"},
				//{"key": "openai", "value": "Open AI"},
			];
		},
		getType(key)
		{
			var arr = this.getTypes();
			var item = arr.find((item) => item.key == key);
			return item.value;
		},
		showAdd()
		{
			this.model.form.clear();
			this.model.form.setItem({
				"type": "",
				"name": "",
				"content": {},
			});
			this.dialog.show();
		},
		showEdit(id)
		{
			/* Find item */
			var item = this.model.findItemById(id);
			if (!item) return;
			
			/* Set item */
			this.model.form.clear();
			this.model.form.setPrimaryKey({
				"id": item.id,
			})
			this.model.form.setItem(item);
			
			/* Show dialog */
			this.dialog.show();
		},
		showDelete(id)
		{
			/* Find item */
			var item = this.model.findItemById(id);
			if (!item) return;
			
			/* Set item */
			this.remove_dialog.setData(item);
			
			/* Remove dialog */
			this.remove_dialog.show();
		},
		async saveItem()
		{
			this.model.form.result.setWaitMessage();
			
			/* Save model */
			var result = await this.model.save(this.model.form.pk, this.model.form.item);
			
			/* Set result */
			this.model.form.setApiResult(result);
			if (result.isSuccess())
			{
				this.dialog.hide();
				this.model.load();
			}
		},
		async deleteItem()
		{
			this.remove_dialog.result.setWaitMessage();
			var result = await this.model.delete(this.remove_dialog.data.id);
			this.remove_dialog.setApiResult(result);
			if (result.isSuccess())
			{
				this.remove_dialog.hide();
				this.model.load();
			}
		},
	}
}
</script>