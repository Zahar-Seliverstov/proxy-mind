<script setup>
import { ref, computed } from 'vue'
import { ChevronDown } from 'lucide-vue-next'

const props = defineProps({
    modelValue: String,
    modes: { type: Array, default: () => [] },
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
            <ChevronDown :size="14" :stroke-width="1.5" class="ms-chevron" />
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
.ms-list { min-width: 180px; }

.ms-item {
    display: flex;
    flex-direction: column;
    gap: 1px;
    padding: 6px 12px;
    cursor: pointer;
    transition: background 0.1s;
}
.ms-item:hover { background: var(--bg-row-hover); }
.ms-item:hover .ms-item-label { color: var(--text-primary); }
.ms-item:hover .ms-item-desc  { color: var(--text-secondary); }

.ms-item-label {
    font-family: var(--font-mono);
    font-size: var(--size-sm);
    color: var(--text-secondary);
    transition: color 0.1s;
}
.ms-item--active .ms-item-label { color: var(--accent); }

.ms-item-desc {
    font-family: var(--font-mono);
    font-size: var(--size-xs);
    color: var(--text-faint);
    white-space: normal;
    max-width: 260px;
    line-height: 1.3;
    transition: color 0.1s;
}
</style>
