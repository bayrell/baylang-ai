<style lang="scss" scoped>
.index_page{
	&__item{
		margin-bottom: 1rem;
	}
}
</style>

<template>
	<div class="index_page">
		<div class="index_page__item">
			<Link href="/">Main page</Link>
		</div>
		<div class="index_page__item">
			<Link href="/settings/llm">LLM page</Link>
		</div>
		<div class="index_page__item">
			<Link href="/chat">Chat page</Link>
		</div>
	</div>
</template>

<script lang="js">
import Link from "@main/Components/Link.vue";

export default
{
	name: "IndexPage",
	components: {
		Link: Link,
	},
}
</script>