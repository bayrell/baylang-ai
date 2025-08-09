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
.field_error, .field_success, .field_message{
	margin-top: 5px;
}
.field_error{
	color: var(--danger-color);
}
.field_success{
	color: var(--success-color);
}
</style>

<template>
	<div class="field">
		<slot></slot>
		<div :class="getClass()" v-if="!isEmpty()">{{ getError() }}</div>
	</div>
</template>

<script lang="js">
import { isString } from "@main/lib.js";

export default {
	name: "Field",
	props: {
		name: {
			type: String,
			required: true,
		},
		error: {
			type: [String, Array, Object],
		}
	},
	methods: {
		isEmpty()
		{
			if (Array.isArray(this.error)) return this.error.length == 0;
			if (isString(this.error)) return this.error == "";
			return this.error.message == "";
		},
		getClass()
		{
			if (Array.isArray(this.error)) return "field_error";
			if (isString(this.error)) return "field_error";
			if (this.error.code < 0) return "field_error";
			if (this.error.code > 0) return "field_success";
			return "field_message";
		},
		getError()
		{
			if (Array.isArray(this.error)) return this.error.join("\n");
			if (isString(this.error)) return this.error;
			return this.error.message;
		}
	},
};
</script>