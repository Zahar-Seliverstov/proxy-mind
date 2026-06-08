<script setup>
import { ref, computed } from 'vue'
import { Plus, X, GripVertical, Play, RefreshCw } from 'lucide-vue-next'

const props = defineProps({
    steps:           { type: Array,   required: true },
    showRegenerate:  { type: Boolean, default: false },
})
const emit = defineEmits(['update:steps', 'run', 'regenerate'])

const dragIndex = ref(null)
const overGap   = ref(null)
const isDragging = computed(() => dragIndex.value !== null)
const hasContent = computed(() => props.steps.some(s => s.trim()))

function mutate(fn) {
    const arr = [...props.steps]
    fn(arr)
    emit('update:steps', arr)
}

const updateStep = (i, v) => mutate(a => { a[i] = v })
const removeStep = i      => mutate(a => a.splice(i, 1))
const insertStep = i      => mutate(a => a.splice(i, 0, ''))

function onCardMouseDown(e) {
    e.currentTarget.draggable = !!e.target.closest('.pr-handle')
}
function onDragStart(i, e) { dragIndex.value = i; e.dataTransfer.effectAllowed = 'move' }
function onDragOver(i, e) {
    e.preventDefault()

    const r = e.currentTarget.getBoundingClientRect()
    overGap.value = e.clientY > r.top + r.height / 2 ? i + 1 : i
}
function onDrop() {
    const from = dragIndex.value
    let to = overGap.value
    if (from === null || to === null) return
    if (to > from) to -= 1
    if (to === from) return
    const arr = [...props.steps]
    const [item] = arr.splice(from, 1)
    arr.splice(to, 0, item)
    emit('update:steps', arr)
}
function onDragEnd() { dragIndex.value = null; overGap.value = null }

function dropEdge(i) {
    if (dragIndex.value === null || overGap.value === null) return null
    if (overGap.value === dragIndex.value || overGap.value === dragIndex.value + 1) return null
    if (overGap.value === i)     return 'before'
    if (overGap.value === i + 1) return 'after'
    return null
}

</script>

<template>
    <div class="pr">
        <div class="pr-list" :class="{ 'pr-list--dragging': isDragging }">

            <div v-if="!steps.length" class="pr-empty">
                <button class="pr-empty-add" @click="insertStep(0)">
                    <Plus :size="14" :stroke-width="1.5" />
                    add step
                </button>
            </div>

            <template v-else>
                <div class="pr-insert" @click="insertStep(0)">
                    <span class="pr-insert-line" />
                    <button class="pr-insert-btn" tabindex="-1">
                        <Plus :size="12" :stroke-width="1.5" />
                    </button>
                </div>

                <template v-for="(step, i) in steps" :key="i">
                    <div
                        class="pr-card"
                        :class="{
                            'pr-card--dragging':    dragIndex === i,
                            'pr-card--drop-before': dropEdge(i) === 'before',
                            'pr-card--drop-after':  dropEdge(i) === 'after',
                        }"
                        @mousedown="onCardMouseDown"
                        @dragstart="onDragStart(i, $event)"
                        @dragover="onDragOver(i, $event)"
                        @drop.prevent="onDrop()"
                        @dragend="onDragEnd"
                    >
                        <GripVertical :size="14" :stroke-width="1.5" class="pr-handle" />
                        <span class="pr-num">{{ String(i + 1).padStart(2, '0') }}</span>
                        <textarea
                            class="pr-text"
                            :value="step"
                            spellcheck="false"
                            @input="e => updateStep(i, e.target.value)"
                        />
                        <button class="pr-del" title="Remove" @click="removeStep(i)">
                            <X :size="14" :stroke-width="1.5" />
                        </button>
                    </div>

                    <div class="pr-insert" @click="insertStep(i + 1)">
                        <span class="pr-insert-line" />
                        <button class="pr-insert-btn" tabindex="-1">
                            <Plus :size="12" :stroke-width="1.5" />
                        </button>
                    </div>
                </template>

                <div v-if="hasContent" class="pr-run-zone">
                    <button v-if="showRegenerate" class="btn btn--warn" @click="emit('regenerate')">
                        <RefreshCw :size="14" :stroke-width="1.5" />
                        regenerate
                    </button>
                    <button class="btn btn--accent" @click="emit('run')">
                        <Play :size="14" :stroke-width="1.5" />
                        run
                    </button>
                </div>
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

.pr-list--dragging .pr-handle,
.pr-list--dragging .pr-num,
.pr-list--dragging .pr-text,
.pr-list--dragging .pr-del,
.pr-list--dragging .pr-insert {
    pointer-events: none;
}

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

.pr-card {
    position: relative;
    z-index: 1;
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

.pr-card--drop-before { box-shadow: inset 0 2px 0 var(--accent); }
.pr-card--drop-after  { box-shadow: inset 0 -2px 0 var(--accent); }

.pr-handle {
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
    min-height: 22px;
    word-break: break-word;
}

.pr-del {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--text-muted);
    padding: 2px 3px;
    display: flex;
    align-items: center;
    flex-shrink: 0;
    margin-top: 1px;
    border-radius: var(--radius);
    transition: color 0.1s, background 0.1s;
}
.pr-del:hover {
    color: var(--danger);
    background: var(--danger-bg);
}

.pr-run-zone {
    padding: 10px 0 6px;
    flex-shrink: 0;
    display: flex;
    gap: 8px;
}

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
</style>
