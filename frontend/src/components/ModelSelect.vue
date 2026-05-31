<script setup>
import { ref } from 'vue'
import { ChevronDown } from 'lucide-vue-next'

const props = defineProps({
    modelValue: String,
    options: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:modelValue'])

const open = ref(false)

function select(value) {
    emit('update:modelValue', value)
    open.value = false
}

function onFocusOut(e) {
    if (!e.currentTarget.contains(e.relatedTarget)) open.value = false
}
</script>

<template>
    <div class="ms" @focusout="onFocusOut" tabindex="-1">
        <button class="ms-trigger" :class="{ 'ms-trigger--open': open }" @click="open = !open">
            <span class="ms-value">{{ modelValue }}</span>
            <ChevronDown :size="14" :stroke-width="1.5" class="ms-chevron" />
        </button>

        <ul v-if="open" class="ms-list">
            <li
                v-for="opt in options"
                :key="opt"
                class="ms-item"
                :class="{ 'ms-item--active': opt === modelValue }"
                @mousedown.prevent="select(opt)"
            >{{ opt }}</li>
        </ul>
    </div>
</template>

<style scoped>
.ms-list { min-width: 100%; }

.ms-item {
    padding: 5px 12px;
    font-family: var(--font-mono);
    font-size: var(--size-sm);
    color: var(--text-secondary);
    cursor: pointer;
    transition: background 0.1s, color 0.1s;
}
.ms-item:hover { background: var(--bg-row-hover); color: var(--text-primary); }
.ms-item--active { color: var(--accent); }
</style>
