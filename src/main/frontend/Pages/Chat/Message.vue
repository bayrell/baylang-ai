<style lang="scss" scoped>
.chat_message{
    line-height: 1.35;
    &__line{
        margin-bottom: 15px;
    }
    pre{
        margin: 0;
        padding: 10px;
        background-color: var(--hover-color);
        border-radius: 5px;
        overflow-x: auto;
    }
}
.chat_main__message--human{
    text-align: right;
}
</style>

<template>
    <div class="chat_message" :class="getClassMessage()">
        <div v-for="line in message.getLines()" :key="line" class="chat_message__line">
            <pre v-if="line.block == 'code'"><code>{{ getCodeContent(line.content) }}</code></pre>
            <div v-else class="text">
			    {{ line.content }}
            </div>
		</div>
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
        },
        getCodeContent(line)
        {
            var arr = line.split("\n");
            if (arr.length == 0) return 0;
            if (arr[0].substring(0, 3) == "```") arr.splice(0, 1);
            if (arr[arr.length - 1].substring(0, 3) == "```") arr.splice(arr.length - 1, 1);
            return arr.join("\n");
        }
    },
}
</script>