<template>
    <a :href="href" @click="onClick">
        <slot></slot>
    </a>
</template>

<script lang="js">
export default
{
    name: "Link",
    props: {
        href: {
            type: String
        }
    },
    methods: {
        onClick(e)
        {
            e.preventDefault();
            this.layout.router.push(this.href);
        }
    },
}
</script>