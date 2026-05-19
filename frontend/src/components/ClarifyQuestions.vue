<script setup>
import { ref } from 'vue'
import TopBar from './TopBar.vue'

defineProps({
    question: { type: Object, required: true },
})
const emit = defineEmits(['next', 'back'])

const answer = ref('')

function onNext() {
    emit('next', answer.value.trim())
    answer.value = ''
}
</script>

<template>
    <div class="cq">
        <TopBar title="clarify">
            <button class="btn btn--ghost" @click="$emit('back')">
                <span class="material-symbols-outlined">keyboard_arrow_left</span>
                cancel
            </button>
            <template #end>
                <button class="btn btn--accent" @click="onNext">
                    {{ answer.trim() ? 'next' : 'skip' }}
                    <span class="material-symbols-outlined">{{ answer.trim() ? 'arrow_forward' : 'skip_next' }}</span>
                </button>
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
                v-model="answer"
                class="cq-input"
                placeholder="свой вариант…"
                spellcheck="false"
            />
        </div>
    </div>
</template>

<style scoped>
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
    color: var(--text-secondary);
    font-size: var(--size-sm);
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
    border-color: var(--border-strong);
    color: var(--text-secondary);
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
    field-sizing: content;
    min-height: 36px;
    width: 100%;
    transition: border-color 0.1s;
}
.cq-input:focus  { border-color: var(--accent-border); }
.cq-input::placeholder { color: var(--text-muted); }
</style>
