<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
    modelValue: String,
    modes: { type: Array, default: () => [] }, // [{ key, label, description }]
})
const emit = defineEmits(['update:modelValue'])

const open     = ref(false)
const selected = computed(() => props.modes.find(m => m.key === props.modelValue))

function select(key) {
    emit('update:modelValue', key)
    open.value = false
}

function onFocusOut(e) {
    if (!e.currentTarget.contains(e.relatedTarget)) open.value = false
}
</script>

<template>
    <div class="ms" @focusout="onFocusOut" tabindex="-1">
        <button class="ms-trigger" :class="{ 'ms-trigger--open': open }" @click="open = !open">
            <span class="ms-value">{{ selected?.label ?? modelValue }}</span>
            <span class="material-symbols-outlined ms-chevron">expand_more</span>
        </button>

        <ul v-if="open" class="ms-list">
            <li
                v-for="mode in modes"
                :key="mode.key"
                class="ms-item"
                :class="{ 'ms-item--active': mode.key === modelValue }"
                @mousedown.prevent="select(mode.key)"
            >
                <span class="ms-item-label">{{ mode.label }}</span>
                <span v-if="mode.description" class="ms-item-desc">{{ mode.description }}</span>
            </li>
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
    min-width: 180px;
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
    display: flex;
    flex-direction: column;
    gap: 1px;
    padding: 6px 12px;
    cursor: pointer;
    transition: background 0.1s;
}
.ms-item:hover {
    background: var(--bg-row-hover);
}
.ms-item:hover .ms-item-label {
    color: var(--text-primary);
}
.ms-item:hover .ms-item-desc {
    color: var(--text-secondary);
}

.ms-item-label {
    font-family: var(--font-mono);
    font-size: var(--size-sm);
    color: var(--text-secondary);
    transition: color 0.1s;
}
.ms-item--active .ms-item-label {
    color: var(--accent);
}

.ms-item-desc {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text-faint);
    white-space: normal;
    max-width: 260px;
    line-height: 1.3;
    transition: color 0.1s;
}
</style>
