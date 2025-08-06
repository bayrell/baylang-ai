<style lang="scss" scoped>
.field{
	margin-bottom: 10px;
	&:last-child{
		margin-bottom: 0px;
	}
}
.field :deep(label){
	display: block;
	margin-bottom: 5px;
}
.field_error{
	color: var(--danger-color);
	margin-top: 5px;
}
</style>

<template>
	<div class="field">
		<slot></slot>
		<div class="field_error" v-if="!isEmpty()">{{ getError() }}</div>
	</div>
</template>

<script>
export default {
	name: "Field",
	props: {
		name: {
			type: String,
			required: true,
		},
		error: {
			type: [String, Array],
		}
	},
	methods: {
		isEmpty()
		{
			if (Array.isArray(this.error)) return this.error.length == 0;
			return this.error == "";
		},
		getError()
		{
			if (Array.isArray(this.error)) return this.error.join("\n");
			return this.error;
		}
	},
};
</script>