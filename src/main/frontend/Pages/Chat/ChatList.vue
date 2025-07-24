<style lang="scss" scoped>
.chat_list{
	&__title{
		padding: 10px;
		text-align: center;
		font-weight: bold;
	}
	&__item{
		display: flex;
		position: relative;
		flex-direction: row;
		align-items: stretch;
		justify-content: space-between;
		cursor: pointer;
		padding: 10px;
	}
	&__item--active{
		background-color: var(--selected-background-color);
		color: var(--selected-text-color);
	}
	.item_button{
		display: flex;
		align-items: center;
		justify-content: center;
		span{
			display: inline-block;
			width: 3px;
			height: 3px;
			margin: 0 2px;
			background-color: transparent;
			border-radius: 50%;
		}
	}
	&__item:hover .item_button span, .item_button.active span{
		background-color: #000;
	}
	.item_menu{
		display: none;
		position: absolute;
		color: black;
		background-color: white;
		border: 1px var(--border-color) solid;
		z-index: 2;
		top: 100%;
		right: 0;
		&__element{
			padding: 10px;
			cursor: pointer;
		}
	}
	.item_menu.active{
		display: block;
	}
}
.chat_list :deep(.dialog--rename_dialog){
	.dialog__content{
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
}
</style>

<template>
	<div class="chat_list" @click="hideMenu()">
		<div class="chat_list__title">
			<span>Chat</span>
		</div>
		<div class="chat_list__item"
			:class="currentItem == null ? 'chat_list__item--active' : ''"
			@click="selectItem('')">New chat</div>
		<div v-for="chat in chats" :key="chat.id"
			class="chat_list__item"
			:class="currentItem && currentItem.id == chat.id ? 'chat_list__item--active' : ''"
			@click.stop="selectItem(chat.id)"
		>
			<div class="item_title">{{ chat.title }}</div>
			<div class="item_button"
				:class="menu_chat_id == chat.id ? 'active' : ''"
				@click.stop="showMenu(chat.id)"
			>
				<span></span>
				<span></span>
				<span></span>
			</div>
			<div class="item_menu" :class="menu_chat_id == chat.id ? 'active' : ''">
				<div class="item_menu__element" @click.stop="onEdit(chat.id)">Edit</div>
				<div class="item_menu__element" @click.stop="onDelete(chat.id)">Delete</div>
			</div>
		</div>
		
		<Dialog v-model="rename_dialog" class="confirm rename_dialog">
			<template v-slot:header>
				Rename chat
			</template>
			<template v-slot:content>
				<div class="rename_dialog__content">
					Rename chat with name '{{ dialog_item ? dialog_item.title : "" }}'?
				</div>
				<Input v-model="new_chat_name" name="chat_name" />
			</template>
			<template v-slot:buttons>
				<Button class="danger" @click="renameChat()">Rename</Button>
				<Button class="default" @click="rename_dialog.hide()">Close</Button>
			</template>
		</Dialog>
		
		<Dialog v-model="confirm_dialog" class="confirm">
			<template v-slot:header>
				Delete chat
			</template>
			<template v-slot:content>
				Delete chat with name '{{ dialog_item ? dialog_item.title : "" }}'?
			</template>
			<template v-slot:buttons>
				<Button class="danger" @click="deleteChat()">Delete</Button>
				<Button class="default" @click="confirm_dialog.hide()">Close</Button>
			</template>
		</Dialog>
	</div>
</template>

<script lang="js">
import Button from "@main/Components/Button.vue";
import Input from "@main/Components/Input.vue";
import Dialog from "@main/Components/Dialog/Dialog.vue";
import DialogModel from "@main/Components/Dialog/DialogModel.js";

export default
{
	name: "ChatList",
	components: {
		Button: Button,
		Dialog: Dialog,
		Input: Input,
	},
	data()
	{
		return {
			dialog_item: null,
			new_chat_name: "",
			rename_dialog: new DialogModel(),
			confirm_dialog: new DialogModel(),
			menu_chat_id: null,
		};
	},
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
			this.hideMenu();
		},
		hideMenu()
		{
			this.menu_chat_id = null;
		},
		showMenu(chat_id)
		{
			this.menu_chat_id = chat_id;
		},
		onEdit(chat_id)
		{
			this.dialog_item = this.model.findChatById(chat_id);
			this.rename_dialog.show();
			this.hideMenu();
		},
		onDelete(chat_id)
		{
			this.dialog_item = this.model.findChatById(chat_id);
			this.confirm_dialog.show();
			this.hideMenu();
		},
		renameChat()
		{
			if (this.dialog_item)
			{
				this.model.renameChat(this.dialog_item.id, this.new_chat_name);
			}
			this.rename_dialog.hide();
		},
		deleteChat()
		{
			if (this.dialog_item)
			{
				this.model.deleteChat(this.dialog_item.id);
			}
			this.confirm_dialog.hide();
		}
	},
}
</script>