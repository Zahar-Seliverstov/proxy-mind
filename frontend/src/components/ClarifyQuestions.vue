<script setup>
import { ref, watch, nextTick } from 'vue'
import { ChevronLeft, ArrowRight, ChevronsRight } from 'lucide-vue-next'
import TopBar from './TopBar.vue'
import ModelSelect from './ModelSelect.vue'

const props = defineProps({
    question: { type: Object, required: true },
    model:    { type: String, default: '' },
    models:   { type: Array,  default: () => [] },
})
const emit = defineEmits(['next', 'back', 'update:model'])

const answer  = ref('')
const inputEl = ref(null)

function resizeInput() {
    const el = inputEl.value
    if (!el) return
    el.style.height = 'auto'
    el.style.height = el.scrollHeight + 'px'
}

watch(answer, () => nextTick(resizeInput))

function onNext() {
    emit('next', answer.value.trim())
    answer.value = ''
}
</script>

<template>
    <div class="cq">
        <TopBar title="clarify">
            <button class="btn btn--ghost" @click="$emit('back')">
                <ChevronLeft :size="14" :stroke-width="1.5" />
                cancel
            </button>
            <template #end>
                <div v-if="models.length" class="cq-model">
                    <span class="cq-model-label">model</span>
                    <ModelSelect :model-value="model" :options="models" @update:model-value="emit('update:model', $event)" />
                </div>
            </template>
        </TopBar>
        <div class="cq-body">
            <div class="cq-qtext">{{ question.text }}</div>
            <div class="cq-options">
                <button
                    v-for="opt in question.options"
                    :key="opt"
                    class="cq-opt"
                    :class="{ 'cq-opt--active': answer === opt }"
                    @click="answer = opt"
                >{{ opt }}</button>
            </div>
            <textarea
                ref="inputEl"
                v-model="answer"
                class="cq-input"
                placeholder="свой вариант…"
                spellcheck="false"
            />
            <div class="cq-next-row">
                <button class="btn btn--warn" @click="onNext">
                    skip
                    <ChevronsRight :size="14" :stroke-width="1.5" />
                </button>
                <button v-if="answer.trim()" class="btn btn--accent" @click="onNext">
                    next
                    <ArrowRight :size="14" :stroke-width="1.5" />
                </button>
            </div>
        </div>
    </div>
</template>

<style scoped>
.cq-next-row {
    display: flex;
    gap: 8px;
}

.cq-model {
    display: flex;
    align-items: center;
    gap: 7px;
    flex-shrink: 0;
}
.cq-model-label {
    color: var(--text-faint);
    font-size: var(--size-sm);
    letter-spacing: var(--tracking);
}

.cq {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    font-family: var(--font-mono);
    font-size: var(--size-base);
}

.cq-body {
    flex: 1;
    overflow-y: auto;
    padding: 20px 16px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    scrollbar-width: thin;
}

.cq-qtext {
    color: var(--text-primary);
    font-size: var(--size-md);
    line-height: 1.55;
}

.cq-options {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}

.cq-opt {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text-faint);
    cursor: pointer;
    font-family: var(--font-mono);
    font-size: var(--size-sm);
    padding: 4px 12px;
    transition: border-color 0.1s, color 0.1s, background 0.1s;
}
.cq-opt:hover {
    border-color: var(--accent-border);
    color: var(--text-primary);
    background: var(--accent-bg-subtle);
}
.cq-opt--active {
    background: var(--accent-bg-rest);
    border-color: var(--accent-border);
    color: var(--accent);
}
.cq-opt--active:hover {
    background: var(--accent-bg-hover);
    border-color: var(--accent-border-strong);
    color: var(--accent-hover);
}

.cq-input {
    resize: none;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text-primary);
    font-family: var(--font-mono);
    font-size: var(--size-sm);
    line-height: 1.5;
    outline: none;
    padding: 8px 12px;
    overflow: hidden;
    min-height: 36px;
    width: 100%;
    transition: border-color 0.1s;
}
.cq-input:focus  { border-color: var(--accent-border); }
.cq-input::placeholder { color: var(--text-muted); }
</style>
