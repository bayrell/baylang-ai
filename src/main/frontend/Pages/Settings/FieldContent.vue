<style lang="scss" scoped>
</style>

<template>
	<div class="field_content">
		<Field name="url" :error="model.form.getFieldError('item.content.url')">
			<label for="url">URL</label>
			<Input name="url" v-model="item.content.url" />
		</Field>
		<Field name="key" :error="model.form.getFieldError('item.content.key')">
			<label for="url">API Key</label>
			<Input name="key" v-model="item.content.key" />
		</Field>
	</div>
</template>

<script lang="js">
import Field from "@main/Components/Field.vue";
import Input from "@main/Components/Input.vue";

export default {
	name: "FieldContent",
	components: {
		Field,
		Input,
	},
	computed: {
		model()
		{
			return this.layout.llm;
		},
		item()
		{
			return this.model.form.item;
		}
	},
};
</script>