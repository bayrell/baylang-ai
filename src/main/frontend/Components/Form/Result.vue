<style lang="scss" scoped>
.result{
    text-align: center;
    margin-top: 16px;
    &--success{
        color: var(--success-color);
    }
    &--danger{
        color: var(--danger-color);
    }
}
</style>

<template>
    <div class="result" :class="getClass()">
        {{ getMessage() }}
    </div>
</template>

<script lang="js">
import ResultModel from "./ResultModel.js";

export default {
    name: "Result",
    props: {
        modelValue: {
            type: ResultModel,
            required: true,
        },
    },
    methods: {
        getClass()
        {
            var arr = [];
            if (this.modelValue.code < 0) arr.push("result--danger");
            else if (this.modelValue.code > 0) arr.push("result--success");
            return arr.join(" ");
        },
        getMessage()
        {
            return this.modelValue.message;
        }
    },
}
</script>