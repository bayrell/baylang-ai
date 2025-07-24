<style lang="scss">
.dialog{
	display: flex;
	position: fixed;
	align-items: flex-start;
	justify-content: center;
	top: 0;
	left: 0;
	width: 100vw;
	height: 100vh;
	padding-top: 30px;
	padding-bottom: 30px;
	overflow-y: auto;
	background-color: rgba(0, 0, 0, 0.5);
	z-index: 1000;
	&__wrap{
		min-width: 500px;
		background-color: #fff;
		border-radius: 5px;
		border-bottom: 1px var(--border-color) solid;
	}
	&__header{
		display: flex;
		align-items: center;
		justify-content: space-between;
		border-bottom: 1px var(--border-color) solid;
		padding: 16px;
		flex: 1;
	}
	&__close_button{
		line-height: 0;
		cursor: pointer;
		svg{
			width: 18px;
			height: 18px;
		}
	}
	&__content{
		padding: 16px;
	}
	&__buttons{
		display: flex;
		align-items: stretch;
		justify-content: flex-end;
		padding: 16px;
		gap: 10px;
	}
}
.dialog--confirm{
	padding-top: 100px;
}
.dialog--center{
	align-items: center;
}
</style>

<template>
	<div class="dialog" :class="getClass()" v-if="modelValue.is_show">
		<div class="dialog__wrap">
			<div class="dialog__header">
				<slot name="header"></slot>
				<div class="dialog__close_button" @click.stop="modelValue.hide()">
					<svg width="32" height="32" viewBox="0 0 32 32" fill="none"
						xmlns="http://www.w3.org/2000/svg">
						<line x1="26" y1="6" x2="6" y2="26"
						stroke="black" stroke-width="2" stroke-linecap="round"/>
						<line x1="6" y1="6" x2="26" y2="26"
						stroke="black" stroke-width="2" stroke-linecap="round"/>
					</svg>
				</div>
			</div>
			<div class="dialog__content">
				<slot name="content"></slot>
			</div>
			<div class="dialog__buttons">
				<slot name="buttons"></slot>
			</div>
		</div>
	</div>
</template>

<script>
import DialogModel from "./DialogModel.js";

export default {
	name: "Dialog",
	props: {
		class: {
			type: String,
			default: "",
		},
		modelValue: {
			type: DialogModel,
			required: true,
		},
	},
	updated()
	{
		if (this.modelValue.is_show)
		{
			document.body.style.overflow = "hidden";
		}
		else
		{
			document.body.style.overflow = "auto";
		}
	},
	methods:
	{
		getClass()
		{
			var arr = this.class.split(" ");
			arr = arr.map((item)=>{ return "dialog--" + item });
			return arr.join(" ");
		},
	},
}
</script>