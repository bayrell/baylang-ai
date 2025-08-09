<style lang="scss" scoped>
.field_group{
    display: flex;
}
.field_group :deep(.input), .field_group :deep(.button){
    border-radius: 0;
    border-right-width: 0;
}
.field_group :deep(.input:first-child), .field_group :deep(.button:first-child){
    border-top-left-radius: 5px;
    border-bottom-left-radius: 5px;
}
.field_group :deep(.input:last-child), .field_group :deep(.button:last-child){
    border-right-width: 1px;
    border-top-right-radius: 5px;
    border-bottom-right-radius: 5px;
}
</style>

<template>
    <div class="field_group">
        <slot></slot>
    </div>
</template>

<script lang="js">
export default {
    name: "FieldGroup"
}
</script>