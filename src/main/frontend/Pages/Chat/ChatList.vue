<style lang="scss" scoped>
.chat_list{
	&__item{
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: space-between;
	}
}
</style>

<template>
	<div class="chat_list">
		<div class="chat_list__item" v-for="chat in chats" :key="chat.id">
			<div class="chat_list__title">{{ chat.title }}</div>
		</div>
	</div>
</template>

<script lang="js">
export default
{
	name: "ChatList",
	computed:
	{
		chats()
		{
			return this.layout.chat_page.chats;
		},
	},
}
</script>