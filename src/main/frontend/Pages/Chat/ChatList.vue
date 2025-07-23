<style lang="scss" scoped>
.chat_list{
	&__title{
		padding: 10px;
		text-align: center;
		font-weight: bold;
	}
	&__item{
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: space-between;
		cursor: pointer;
		padding: 10px;
	}
	&__item--active{
		background-color: var(--selected-background-color);
		color: var(--selected-text-color);
	}
}
</style>

<template>
	<div class="chat_list">
		<div class="chat_list__title">
			<span>Chat</span>
		</div>
		<div class="chat_list__item"
			:class="currentItem == null ? 'chat_list__item--active' : ''"
			@click="selectItem('')">New chat</div>
		<div v-for="chat in chats" :key="chat.id"
			class="chat_list__item"
			:class="currentItem && currentItem.id == chat.id ? 'chat_list__item--active' : ''"
			@click="selectItem(chat.id)"
		>
			<div class="chat_list__item_title">{{ chat.title }}</div>
		</div>
	</div>
</template>

<script lang="js">
export default
{
	name: "ChatList",
	computed:
	{
		model()
		{
			return this.layout.chat_page;
		},
		currentItem()
		{
			return this.model.getCurrentItem();
		},
		chats()
		{
			return this.model.chats;
		},
	},
	methods:
	{
		selectItem(chat_id)
		{
			this.model.selectItem(chat_id);
		}
	},
}
</script>