<style lang="scss">
</style>

<template>
	<component :is="getCurrentComponent()"></component>
</template>

<script lang="js">
export default
{
	name: "Layout",
	methods: {
		getCurrentComponent()
		{
			var component = this.layout.router.currentRoute.component;
			return component;
		}
	},
}
</script>