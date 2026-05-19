<script setup>
import { ref } from 'vue'

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
            <span class="material-symbols-outlined ms-chevron">expand_more</span>
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
.ms {
    position: relative;
    outline: none;
}

.ms-trigger {
    display: flex;
    align-items: center;
    gap: 4px;
    background: none;
    border: 1px solid var(--border-dim);
    border-radius: var(--radius);
    cursor: pointer;
    font-family: var(--font-mono);
    font-size: var(--size-sm);
    color: var(--text-secondary);
    padding: 2px 6px;
    transition: border-color 0.1s, color 0.1s;
}
.ms-trigger:hover,
.ms-trigger--open {
    border-color: var(--border);
    color: var(--text-primary);
}

.ms-chevron {
    font-size: 14px;
    line-height: 1;
    color: var(--text-faint);
    transition: transform 0.15s;
}
.ms-trigger--open .ms-chevron {
    transform: rotate(180deg);
}

.ms-list {
    position: absolute;
    top: calc(100% + 4px);
    left: 0;
    min-width: 100%;
    list-style: none;
    margin: 0;
    padding: 4px 0;
    background: var(--bg-panel);
    border: 1px solid var(--border-dim);
    border-radius: var(--radius);
    z-index: 100;
    white-space: nowrap;
}

.ms-item {
    padding: 5px 12px;
    font-family: var(--font-mono);
    font-size: var(--size-sm);
    color: var(--text-secondary);
    cursor: pointer;
    transition: background 0.1s, color 0.1s;
}
.ms-item:hover {
    background: var(--bg-row-hover);
    color: var(--text-primary);
}
.ms-item--active {
    color: var(--accent);
}
</style>
