<script setup>
import { ref } from "vue";
import { browse } from "../api/fs.js";

const props = defineProps({ modelValue: String });
const emit = defineEmits(["update:modelValue", "close"]);

const current = ref(null);
const parent = ref(null);
const items = ref([]);
const error = ref(null);

async function load(path) {
    error.value = null;
    try {
        const res = await browse(path, "dir");
        current.value = res.path;
        parent.value = res.parent;
        items.value = res.items;
    } catch (e) {
        error.value = String(e);
    }
}

load(props.modelValue || null);

function select(path) {
    emit("update:modelValue", path);
    emit("close");
}
</script>

<template>
    <div class="fp">
        <div class="fp-header">
            <span class="fp-path">{{ current }}</span>
            <button class="fp-close" @click="emit('close')" title="Close">
                <span class="material-symbols-outlined">close</span>
            </button>
        </div>

        <div v-if="error" class="fp-error">{{ error }}</div>

        <ul class="fp-list">
            <li v-if="parent" class="fp-up-row" @click="load(parent)">
                <span class="material-symbols-outlined fp-icon">arrow_upward</span>
                <span class="fp-name">..</span>
            </li>
            <li v-for="item in items" :key="item.path" @click="load(item.path)">
                <span class="material-symbols-outlined fp-icon">folder</span>
                <span class="fp-name">{{ item.name }}</span>
                <button
                    class="fp-sel"
                    @click.stop="select(item.path)"
                    title="Select"
                >
                    <span class="material-symbols-outlined">check</span>
                    <span class="fp-sel-label">select</span>
                </button>
            </li>
        </ul>

        <div class="fp-footer">
            <button class="fp-btn-sel" @click="select(current)">
                select current
            </button>
        </div>
    </div>
</template>

<style scoped>
.fp {
    display: flex;
    flex-direction: column;
    background: var(--bg-input);
    border: 1px solid var(--border-dim);
    border-radius: var(--radius);
    font-family: var(--font-mono);
    font-size: var(--size-base);
}

.fp-header {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 6px 8px;
    border-bottom: 1px solid var(--border);
}
.fp-path {
    flex: 1;
    color: var(--text-faint);
    font-size: var(--size-sm);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    direction: rtl;
    text-align: left;
}
.fp-close {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--text-dim);
    display: flex;
    align-items: center;
    padding: 2px;
    border-radius: var(--radius);
    transition: var(--transition);
    flex-shrink: 0;
}
.fp-close:hover {
    color: var(--danger);
    background: var(--danger-bg);
}
.fp-close .material-symbols-outlined {
    font-size: var(--size-icon);
    line-height: 1;
}

.fp-error {
    padding: 6px 10px;
    color: var(--danger);
    font-size: var(--size-sm);
}

.fp-list {
    list-style: none;
    margin: 0;
    padding: 4px 0;
    max-height: 400px;
    overflow-y: auto;
    scrollbar-width: thin;
}
.fp-list li {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 3px 8px;
    cursor: pointer;
    transition: background 0.1s;
}
.fp-list li:hover {
    background: var(--bg-row-hover);
}
.fp-up-row .fp-icon {
    color: var(--text-muted);
}
.fp-icon {
    font-size: var(--size-md);
    line-height: 1;
    color: var(--text-dim);
    flex-shrink: 0;
}
.fp-list li:hover .fp-icon {
    color: var(--accent-icon);
}
.fp-name {
    flex: 1;
    color: var(--text-secondary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.fp-sel {
    gap: 2px;
    background: none;
    border: none;
    cursor: pointer;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    padding: 1px 4px 1px 2px;
    border-radius: var(--radius);
    opacity: 0;
    transition: var(--transition);
}
.fp-list li:hover .fp-sel {
    opacity: 1;
}
.fp-sel:hover {
    color: var(--accent);
    background: var(--accent-bg);
}
.fp-sel .material-symbols-outlined {
    font-size: var(--size-md);
    line-height: 1;
}
.fp-sel-label {
    font-size: var(--size-base);
    line-height: 1;
}

.fp-footer {
    padding: 6px 8px;
    border-top: 1px solid var(--border);
}
.fp-btn-sel {
    width: 100%;
    background: var(--accent-bg-subtle);
    border: 1px solid var(--accent-border-faint);
    border-radius: var(--radius);
    color: var(--accent-text-dim);
    cursor: pointer;
    font-family: inherit;
    font-size: var(--size-sm);
    padding: 4px;
    transition:
        background 0.1s,
        color 0.1s,
        border-color 0.1s;
}
.fp-btn-sel:hover {
    background: var(--accent-bg-rest);
    color: var(--accent);
    border-color: var(--accent-border-focus);
}
</style>
