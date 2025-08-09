<style lang="scss" scoped>
</style>

<template>
	<div class="field_content">
		<Field name="url" :error="model.form.getFieldError('item.content.url')"
			v-if="isAvailable('url')"
		>
			<label for="url">URL</label>
			<Input name="url" v-model="item.content.url" />
		</Field>
		<Field name="key" :error="model.form.getFieldError('item.content.key')"
			v-if="isAvailable('key')"
		>
			<label for="url">API Key</label>
			<Input name="key" v-model="item.content.key" />
		</Field>
		<Field name="model" :error="model.form.getFieldError('item.content.model')"
			v-if="isAvailable('model')"
		>
			<label for="url">Model</label>
			<FieldGroup>
				<Input name="model" v-model="item.content.model" type="select"
					:options="getModels()" />
				<Button @click="reloadModels">Reload</Button>
			</FieldGroup>
		</Field>
		<Field name="temperature" :error="model.form.getFieldError('item.content.temperature')"
			v-if="isAvailable('temperature')"
		>
			<label for="temperature">Temperature</label>
			<Input name="temperature" v-model="item.content.temperature" />
		</Field>
	</div>
</template>

<script lang="js">
import { ApiResult } from "@main/lib.js";
import Button from "@main/Components/Button.vue";
import Input from "@main/Components/Input.vue";
import Field from "@main/Components/Form/Field.vue";
import FieldGroup from "@main/Components/Form/FieldGroup.vue";

export default {
	name: "FieldContent",
	components: {
		Button,
		Field,
		FieldGroup,
		Input,
	},
	computed: {
		model()
		{
			return this.layout.llm_page;
		},
		item()
		{
			return this.model.form.item;
		}
	},
	methods: {
		isAvailable(key)
		{
			var arr = [];
			if (this.item.type == "openai") arr = ["key", "model", "temperature"];
			else if (this.item.type == "ollama") arr = ["url", "model", "temperature"];
			return arr.indexOf(key) >=0;
		},
		getModels()
		{
			return this.item.content.models.map(
				(item) => {
					return {
						"key": item,
						"value": item,
					};
				}
			);
		},
		async reloadModels()
		{
			this.model.form.errors = {};
			this.model.form.result.clear();
			this.model.form.setFieldError("item.content.model", {
				"code": 0,
				"message": "Reload models",
			});
			var result = await this.model.reloadModels();
			this.model.form.setFieldError("item.content.model", result);
			if (!result.isSuccess() && result.response.form != undefined)
			{
				var form_result = new ApiResult();
				form_result.assign(result.response.form);
				this.model.form.setApiResult(form_result);
			}
		}
	},
};
</script>