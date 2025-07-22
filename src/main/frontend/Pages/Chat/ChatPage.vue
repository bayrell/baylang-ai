<style lang="scss" scoped>
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