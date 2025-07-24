<style lang="scss" scoped>
.chat_main{
	padding-top: 20px;
	padding-bottom: 20px;
	margin-left: auto;
	margin-right: auto;
	max-width: 900px;
	display: flex;
	flex-direction: column;
	&__history{
		flex: 1;
		overflow-y: auto;
		padding-right: 10px;
	}
	&__send_message{
		display: flex;
		height: 75px;
	}
	&__send_message :deep(.button){
		width: 150px;
		border-top-left-radius: 0px;
		border-bottom-left-radius: 0px;
	}
	&__send_message :deep(.input){
		flex: 1;
		border-right-width: 0;
		border-top-right-radius: 0px;
		border-bottom-right-radius: 0px;
	}
}
.chat_main :deep(.chat_typing){
	margin-bottom: 15px;
}
</style>

<template>
	<div class="chat_main">
		<div class="chat_main__history" ref="history">
			<Message
				v-for="message in getMessages()"
				:key="message.id"
				:message="message"
				@update="scrollHistory"
			/>
			<ChatTyping v-if="currentItem && currentItem.isTyping()" />
		</div>
		<div class="chat_main__send_message">
			<Input type="textarea" name="message" v-model="message" />
			<Button @click="sendMessage">Send</Button>
		</div>
	</div>
</template>

<script lang="js">
import Button from "@main/Components/Button.vue";
import Input from "@main/Components/Input.vue";
import ChatTyping from "./ChatTyping.vue";
import Message from "./Message.vue";

export default {
	name: "ChatMain",
	components:
	{
		Button: Button,
		Input: Input,
		ChatTyping: ChatTyping,
		Message: Message,
	},
	data()
	{
		return {
			message: "",
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
	},
	updated: function()
	{
		this.scrollHistory();
	},
	methods:
	{
		scrollHistory()
		{
			this.$nextTick(() => {
				var history = this.$refs["history"];
				if (this.currentItem && this.currentItem.is_typing)
				{
					history.scrollTop = history.scrollHeight + 25;
				}
				else
				{
					history.scrollTop = history.scrollHeight;
				}
			});
		},
		getMessages()
		{
			if (!this.currentItem) return [];
			return this.currentItem.messages;
		},
		sendMessage()
		{
			this.model.sendMessage(this.model.current_chat_id, this.message);
			this.message = "";
		},
	},
}
</script>