<script setup>
import { ref, reactive, watch } from 'vue'
import { Save, X } from 'lucide-vue-next'
import { getPrompts, updatePrompt } from '../api/prompts.js'

const props = defineProps({ visible: { type: Boolean, required: true } })
const emit  = defineEmits(['close'])

const LABELS = {
    mode_plan:       'Auto Plan — system prompt',
    mode_optimize:   'Rewrite — system prompt',
    next_question:   'Clarifying questions',
    translate:       'Text translation',
    translate_array: 'Batch translation',
    validate:        'Prompt validation',
    analyze:         'Terminal state analysis',
    auto_reply:      'Automatic CLI reply',
    limit_patterns:  'CLI limit detection patterns',
}

const prompts  = ref([])
const edits    = reactive({})
const loading  = ref(false)
const saving   = reactive({})
const error    = ref(null)
const saved    = reactive({})

watch(() => props.visible, async (v) => {
    if (!v) return
    error.value  = null
    loading.value = true
    try {
        const data = await getPrompts()
        prompts.value = data
        data.forEach(p => { edits[p.name] = p.content })
    } catch (e) {
        error.value = String(e)
    } finally {
        loading.value = false
    }
})

async function save(name) {
    saving[name] = true
    error.value  = null
    try {
        await updatePrompt(name, edits[name])
        saved[name] = true
        setTimeout(() => { saved[name] = false }, 1500)
    } catch (e) {
        error.value = String(e)
    } finally {
        saving[name] = false
    }
}

function onOverlayClick(e) {
    if (e.target === e.currentTarget) emit('close')
}
</script>

<template>
    <Transition name="modal">
        <div v-if="visible" class="overlay" @click="onOverlayClick">
            <div class="modal" role="dialog" aria-modal="true">
                <header class="modal-header">
                    <span class="modal-title">instructions</span>
                    <button class="close-btn" @click="emit('close')" title="Close">
                        <X :size="16" :stroke-width="1.5" />
                    </button>
                </header>

                <div class="modal-body">
                    <p v-if="loading" class="status-msg">loading…</p>
                    <p v-else-if="error" class="error-msg">{{ error }}</p>
                    <template v-else>
                        <div
                            v-for="p in prompts"
                            :key="p.name"
                            class="prompt-block"
                        >
                            <div class="prompt-header">
                                <label :for="`p-${p.name}`" class="prompt-label">
                                    {{ LABELS[p.name] ?? p.name }}
                                </label>
                                <span class="prompt-key">{{ p.name }}</span>
                                <button
                                    class="save-btn"
                                    :class="{ 'save-btn--saved': saved[p.name] }"
                                    :disabled="saving[p.name] || (edits[p.name] === p.content && !saved[p.name])"
                                    @click="save(p.name)"
                                >
                                    <Save :size="13" :stroke-width="1.5" />
                                    {{ saved[p.name] ? 'saved' : saving[p.name] ? 'saving…' : 'save' }}
                                </button>
                            </div>
                            <textarea
                                :id="`p-${p.name}`"
                                v-model="edits[p.name]"
                                class="prompt-textarea"
                                spellcheck="false"
                                autocomplete="off"
                            />
                        </div>
                    </template>
                </div>
            </div>
        </div>
    </Transition>
</template>

<style scoped>
.overlay {
    position: fixed;
    inset: 0;
    z-index: var(--z-modal);
    background: rgba(0, 0, 0, 0.6);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
}

.modal {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: calc(var(--radius) * 2);
    width: 100%;
    max-width: 720px;
    max-height: 90vh;
    display: flex;
    flex-direction: column;
    font-family: var(--font-mono);
    font-size: var(--size-base);
}

.modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 18px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
}
.modal-title {
    font-size: var(--size-md);
    letter-spacing: var(--tracking);
    color: var(--text-bright);
}
.close-btn {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--text-faint);
    padding: 3px;
    border-radius: var(--radius);
    display: flex;
    align-items: center;
    transition: color 0.1s, background 0.1s;
}
.close-btn:hover {
    color: var(--text-primary);
    background: var(--border);
}

.modal-body {
    flex: 1;
    overflow-y: auto;
    padding: 16px 18px;
    display: flex;
    flex-direction: column;
    gap: 20px;
    scrollbar-width: thin;
}

.status-msg {
    color: var(--text-dim);
    margin: 0;
}
.error-msg {
    margin: 0;
    padding: 8px 10px;
    color: var(--danger);
    background: var(--danger-bg);
    border: 1px solid var(--danger);
    border-radius: var(--radius);
    font-size: var(--size-sm);
}

.prompt-block {
    display: flex;
    flex-direction: column;
    gap: 6px;
}
.prompt-header {
    display: flex;
    align-items: center;
    gap: 8px;
}
.prompt-label {
    flex: 1;
    font-size: var(--size-sm);
    color: var(--text-secondary);
    letter-spacing: var(--tracking);
}
.prompt-key {
    color: var(--text-faint);
    font-size: var(--size-xs);
}
.save-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    background: none;
    border: 1px solid var(--border-dim);
    border-radius: var(--radius);
    color: var(--text-dim);
    cursor: pointer;
    font-family: inherit;
    font-size: var(--size-sm);
    padding: 2px 8px;
    letter-spacing: var(--tracking);
    transition: color 0.1s, border-color 0.1s, background 0.1s;
    flex-shrink: 0;
}
.save-btn:not(:disabled):hover {
    color: var(--accent);
    border-color: var(--accent-border-faint);
    background: var(--accent-bg-rest);
}
.save-btn--saved {
    color: var(--ok) !important;
    border-color: var(--ok) !important;
}
.save-btn:disabled {
    opacity: 0.35;
    cursor: default;
}

.prompt-textarea {
    resize: vertical;
    min-height: 120px;
    background: var(--bg-input);
    border: 1px solid var(--border-dim);
    border-radius: var(--radius);
    color: var(--text-primary);
    font-family: var(--font-mono);
    font-size: var(--size-sm);
    line-height: 1.55;
    padding: 10px 12px;
    outline: none;
    width: 100%;
    box-sizing: border-box;
    transition: border-color 0.15s;
    scrollbar-width: thin;
}
.prompt-textarea:focus {
    border-color: var(--accent-border-focus);
}


.modal-enter-active { transition: opacity 0.15s; }
.modal-leave-active { transition: opacity 0.12s; }
.modal-enter-from,
.modal-leave-to     { opacity: 0; }
.modal-enter-active .modal,
.modal-leave-active .modal { transition: transform 0.15s; }
.modal-enter-from   .modal { transform: scale(0.96) translateY(8px); }
.modal-leave-to     .modal { transform: scale(0.96) translateY(8px); }
</style>
