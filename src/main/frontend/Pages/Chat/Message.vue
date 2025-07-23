<style lang="scss" scoped>
.chat_main__message{
    line-height: 1.35;
    p{
        margin-bottom: 15px;
    }
}
.chat_main__message--human{
    text-align: right;
}
</style>

<template>
    <div class="chat_main__message" :class="getClassMessage()">
        <p v-for="line in message.getLines()" :key="line">
			{{ line }}
		</p>
    </div>
</template>

<script lang="js">
export default {
    name: "Message",
    props: {
        message: {
			type: Object,
		}
    },
    updated: function()
	{
		this.$emit("update");
	},
    methods:
    {
        getClassMessage()
        {
            if (this.message.sender == "assistant") return "chat_main__message--assistant";
			else if (this.message.sender == "human") return "chat_main__message--human";
            return "";
        }
    },
}
</script>