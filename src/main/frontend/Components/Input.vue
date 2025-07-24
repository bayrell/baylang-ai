<style lang="scss" scoped>
.input{
	padding: 8px;
	border: 1px solid var(--border-color);
	border-radius: 5px;
	outline: 0;
}
</style>

<template>
	<input
		v-if="type == 'input'"
		:id="name"
		:name="name"
		:value="modelValue"
		:class="getInputClass()"
		@input="$emit('update:modelValue', $event.target.value)"
	>
	<textarea
		v-if="type == 'textarea'"
		:id="name"
		:name="name"
		:value="modelValue"
		:class="getInputClass()"
		@input="$emit('update:modelValue', $event.target.value)"
	></textarea>
</template>

<script lang="js">
export default {
	name: "Input",
	props: {
		type: {
			type: String,
			default: "input",
		},
		name: {
			type: String,
			required: true,
		},
		modelValue: {
			type: [String, Number],
			default: "",
		},
	},
	emits: ["update:modelValue"],
	methods:
	{
		getInputClass()
		{
			return "input";
		}
	}
}
</script>