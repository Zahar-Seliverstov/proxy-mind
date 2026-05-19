<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
    steps: { type: Array, required: true },
})
const emit = defineEmits(['update:steps'])

const dragIndex = ref(null)
const overIndex = ref(null)
const isDragging = computed(() => dragIndex.value !== null)

function mutate(fn) {
    const arr = [...props.steps]
    fn(arr)
    emit('update:steps', arr)
}

const updateStep = (i, v) => mutate(a => { a[i] = v })
const removeStep = i      => mutate(a => a.splice(i, 1))
const insertStep = i      => mutate(a => a.splice(i, 0, ''))

function onDragStart(i, e) {
    dragIndex.value = i
    e.dataTransfer.effectAllowed = 'move'
}

function onDragOver(i, e) {
    e.preventDefault()
    overIndex.value = i
}

function onDrop(i) {
    if (dragIndex.value === null || dragIndex.value === i) return
    const arr = [...props.steps]
    const [item] = arr.splice(dragIndex.value, 1)
    arr.splice(i, 0, item)
    emit('update:steps', arr)
}

function onDragEnd() {
    dragIndex.value = null
    overIndex.value = null
}
</script>

<template>
    <div class="pr">
        <div class="pr-list" :class="{ 'pr-list--dragging': isDragging }">

            <div v-if="!steps.length" class="pr-empty">
                <button class="pr-empty-add" @click="insertStep(0)">
                    <span class="material-symbols-outlined">add</span>
                    add step
                </button>
            </div>

            <template v-else>
                <div class="pr-insert" @click="insertStep(0)">
                    <span class="pr-insert-line" />
                    <button class="pr-insert-btn" tabindex="-1">
                        <span class="material-symbols-outlined">add</span>
                    </button>
                </div>

                <template v-for="(step, i) in steps" :key="i">
                    <div
                        class="pr-card"
                        :class="{
                            'pr-card--dragging': dragIndex === i,
                            'pr-card--over':     overIndex === i && dragIndex !== i,
                        }"
                        draggable="true"
                        @dragstart="onDragStart(i, $event)"
                        @dragover="onDragOver(i, $event)"
                        @drop.prevent="onDrop(i)"
                        @dragend="onDragEnd"
                    >
                        <span class="material-symbols-outlined pr-handle">drag_indicator</span>
                        <span class="pr-num">{{ String(i + 1).padStart(2, '0') }}</span>
                        <textarea
                            class="pr-text"
                            :value="step"
                            spellcheck="false"
                            @input="e => updateStep(i, e.target.value)"
                        />
                        <button class="pr-del" title="Remove" @click="removeStep(i)">
                            <span class="material-symbols-outlined">close</span>
                        </button>
                    </div>

                    <div class="pr-insert" @click="insertStep(i + 1)">
                        <span class="pr-insert-line" />
                        <button class="pr-insert-btn" tabindex="-1">
                            <span class="material-symbols-outlined">add</span>
                        </button>
                    </div>
                </template>
            </template>

        </div>
    </div>
</template>

<style scoped>
.pr {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    font-family: var(--font-mono);
    font-size: var(--size-base);
}

.pr-list {
    flex: 1;
    overflow-y: auto;
    padding: 8px 16px;
    display: flex;
    flex-direction: column;
    scrollbar-width: thin;
}

/* disable pointer events on card children and insert zones while dragging */
.pr-list--dragging .pr-handle,
.pr-list--dragging .pr-num,
.pr-list--dragging .pr-text,
.pr-list--dragging .pr-del,
.pr-list--dragging .pr-insert {
    pointer-events: none;
}

/* ── insert zone ── */
.pr-insert {
    position: relative;
    height: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    flex-shrink: 0;
}
.pr-insert-line {
    position: absolute;
    left: 0; right: 0;
    height: 1px;
    background: var(--accent-border);
    opacity: 0;
    transition: opacity 0.15s;
    pointer-events: none;
}
.pr-insert-btn {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-panel);
    border: 1px solid var(--accent-border);
    border-radius: var(--radius);
    color: var(--accent);
    cursor: pointer;
    width: 20px;
    height: 20px;
    padding: 0;
    opacity: 0;
    transition: opacity 0.15s, background 0.1s;
}
.pr-insert:hover .pr-insert-line,
.pr-insert:hover .pr-insert-btn { opacity: 1; }
.pr-insert-btn:hover { background: var(--accent-bg-hover); }
.pr-insert-btn .material-symbols-outlined { font-size: 14px; line-height: 1; }

/* ── card ── */
.pr-card {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 8px 10px;
    transition: border-color 0.1s, opacity 0.1s, background 0.1s;
    flex-shrink: 0;
}
.pr-card--dragging { opacity: 0.35; }
.pr-card--over     { border-color: var(--accent-border); background: var(--accent-bg-subtle); }

.pr-handle {
    font-size: var(--size-icon);
    color: var(--text-muted);
    cursor: grab;
    flex-shrink: 0;
    margin-top: 2px;
    user-select: none;
}
.pr-handle:active { cursor: grabbing; }

.pr-num {
    font-size: var(--size-xs);
    color: var(--text-faint);
    flex-shrink: 0;
    margin-top: 3px;
    min-width: 16px;
    letter-spacing: var(--tracking);
}

.pr-text {
    flex: 1;
    min-width: 0;
    background: none;
    border: none;
    outline: none;
    color: var(--text-primary);
    font-family: var(--font-mono);
    font-size: var(--size-base);
    line-height: 1.55;
    resize: none;
    padding: 0;
    field-sizing: content;
    min-height: 1lh;
    word-break: break-word;
}

.pr-del {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--text-muted);
    padding: 0;
    display: flex;
    align-items: center;
    flex-shrink: 0;
    margin-top: 1px;
    transition: color 0.1s;
}
.pr-del:hover { color: var(--danger); }
.pr-del .material-symbols-outlined { font-size: var(--size-icon); line-height: 1; }

/* ── empty state ── */
.pr-empty {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
}
.pr-empty-add {
    display: flex;
    align-items: center;
    gap: 4px;
    background: none;
    border: 1px solid var(--border-dim);
    border-radius: var(--radius);
    cursor: pointer;
    color: var(--text-faint);
    font-family: var(--font-mono);
    font-size: var(--size-sm);
    padding: 5px 12px;
    letter-spacing: var(--tracking);
    transition: color 0.1s, border-color 0.1s;
}
.pr-empty-add:hover { color: var(--text-secondary); border-color: var(--border); }
.pr-empty-add .material-symbols-outlined { font-size: var(--size-icon); line-height: 1; }
</style>
