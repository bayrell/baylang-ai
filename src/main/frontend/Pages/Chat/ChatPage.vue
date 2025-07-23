<style lang="scss" scoped>
.chat_page{
	display: flex;
	height: 100vh;
}
.chat_page :deep(.chat_list){
	width: 200px;
	border-right: 1px var(--border-color) solid;
	overflow-y: auto;
}
.chat_page :deep(.chat_main){
	flex: 1;
}
</style>

<template>
	<div class="chat_page">
		<ChatList />
		<ChatMain />
	</div>
</template>

<script lang="js">
import ChatList from "./ChatList.vue";
import ChatMain from "./ChatMain.vue";

export default
{
	name: "ChatPage",
	components:
	{
		ChatList: ChatList,
		ChatMain: ChatMain,
	},
	computed:
	{
		model()
		{
			return this.layout.chat_page;
		}
	},
	mounted()
	{
		this.model.load();
	},
}
</script>