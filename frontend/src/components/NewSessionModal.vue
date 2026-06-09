<script setup>
import { reactive, ref } from 'vue'
import { FolderOpen, X } from 'lucide-vue-next'
import { useSessionsStore } from '../stores/sessions.js'
import FilePicker from './FilePicker.vue'

const props = defineProps({ visible: { type: Boolean, required: true } })
const emit  = defineEmits(['close'])

const store      = useSessionsStore()
const form       = reactive({ name: '', path: '' })
const showPicker = ref(false)

async function submit() {
    await store.createSession(form.name.trim(), form.path.trim())
    form.name    = ''
    form.path    = ''
    showPicker.value = false
    emit('close')
}

function close() {
    form.name    = ''
    form.path    = ''
    showPicker.value = false
    emit('close')
}

function onOverlayClick(e) {
    if (e.target === e.currentTarget) close()
}
</script>

<template>
    <Transition name="modal">
        <div v-if="visible" class="overlay" @click="onOverlayClick">
            <div class="modal" role="dialog" aria-modal="true">
                <header class="modal-header">
                    <span class="modal-title">new session</span>
                    <button class="close-btn" @click="close" title="Close">
                        <X :size="16" :stroke-width="1.5" />
                    </button>
                </header>

                <form class="modal-body" @submit.prevent="submit">
                    <input
                        v-model="form.name"
                        placeholder="name (auto if empty)"
                        autofocus
                        spellcheck="false"
                    />
                    <div v-if="!showPicker" class="path-row">
                        <input v-model="form.path" placeholder="path" spellcheck="false" />
                        <button
                            type="button"
                            class="btn-pick"
                            @click="showPicker = true"
                            title="Browse"
                        >
                            <FolderOpen :size="14" :stroke-width="1.5" />
                        </button>
                    </div>
                    <FilePicker
                        v-if="showPicker"
                        v-model="form.path"
                        @close="showPicker = false"
                    />
                    <div class="actions">
                        <button type="button" class="btn btn--ghost" @click="close">cancel</button>
                        <button type="submit" class="btn btn--accent">create</button>
                    </div>
                </form>
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
    max-width: 380px;
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
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 18px;
}
input {
    background: var(--bg-input);
    border: 1px solid var(--border-dim);
    border-radius: var(--radius);
    color: var(--text-bright);
    font-family: inherit;
    font-size: var(--size-base);
    padding: 6px 8px;
    outline: none;
    transition: border-color 0.15s;
    width: 100%;
    box-sizing: border-box;
}
input:focus { border-color: var(--accent-border-focus); }
.path-row {
    display: flex;
    gap: 4px;
}
.path-row input { flex: 1; }
.btn-pick {
    background: none;
    border: 1px solid var(--border-dim);
    border-radius: var(--radius);
    color: var(--text-dim);
    cursor: pointer;
    padding: 0 8px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    transition: color 0.1s, border-color 0.1s;
}
.btn-pick:hover {
    color: var(--text-primary);
    border-color: var(--text-dim);
}
.actions {
    display: flex;
    gap: 6px;
    justify-content: flex-end;
    margin-top: 14px;
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
