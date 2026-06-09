<script setup>
import { reactive, watch } from 'vue'
import { X } from 'lucide-vue-next'
import { getSettings, updateSettings } from '../api/settings.js'
import { useNotificationsStore } from '../stores/notifications.js'

const props = defineProps({ visible: { type: Boolean, required: true } })
const emit  = defineEmits(['close'])

const nStore = useNotificationsStore()

const form = reactive({
    ollamaUrl: '',        initialOllamaUrl: '',
    telegramBotToken: '', initialTelegramBotToken: '',
    telegramChatId: '',   initialTelegramChatId: '',
    loading: false, saving: false, error: null,
})

watch(() => props.visible, async (v) => {
    if (!v) return
    form.error   = null
    form.loading = true
    try {
        const data = await getSettings()
        form.ollamaUrl               = data.ollama_base_url ?? ''
        form.initialOllamaUrl        = form.ollamaUrl
        form.telegramBotToken        = data.telegram_bot_token ?? ''
        form.initialTelegramBotToken = form.telegramBotToken
        form.telegramChatId          = data.telegram_chat_id ?? ''
        form.initialTelegramChatId   = form.telegramChatId
    } catch (e) {
        form.error = String(e)
    } finally {
        form.loading = false
    }
})

async function submit() {
    const ollama = form.ollamaUrl.trim()
    const token  = form.telegramBotToken.trim()
    const chat   = form.telegramChatId.trim()
    if (!ollama) return

    const patch = {}
    if (ollama !== form.initialOllamaUrl)         patch.ollama_base_url    = ollama
    if (token  !== form.initialTelegramBotToken)  patch.telegram_bot_token = token || null
    if (chat   !== form.initialTelegramChatId)    patch.telegram_chat_id   = chat  || null

    if (Object.keys(patch).length === 0) { emit('close'); return }

    form.saving = true
    form.error  = null
    try {
        const data = await updateSettings(patch)
        form.ollamaUrl               = data.ollama_base_url
        form.initialOllamaUrl        = data.ollama_base_url
        form.telegramBotToken        = data.telegram_bot_token ?? ''
        form.initialTelegramBotToken = form.telegramBotToken
        form.telegramChatId          = data.telegram_chat_id ?? ''
        form.initialTelegramChatId   = form.telegramChatId
        nStore.push('success', 'Settings saved')
        emit('close')
    } catch (e) {
        form.error = String(e)
    } finally {
        form.saving = false
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
                    <span class="modal-title">settings</span>
                    <button class="close-btn" @click="emit('close')" title="Close">
                        <X :size="16" :stroke-width="1.5" />
                    </button>
                </header>

                <form class="modal-body" @submit.prevent="submit">
                    <p v-if="form.error" class="error-msg">{{ form.error }}</p>

                    <label class="field-label" for="s-ollama-url">ollama base url</label>
                    <input
                        id="s-ollama-url"
                        v-model="form.ollamaUrl"
                        :disabled="form.loading"
                        :placeholder="form.loading ? 'loading…' : 'http://localhost:11434'"
                        spellcheck="false"
                        autocomplete="off"
                        autofocus
                    />

                    <label class="field-label" for="s-tg-token">telegram bot token</label>
                    <textarea
                        id="s-tg-token"
                        v-model="form.telegramBotToken"
                        :disabled="form.loading"
                        :placeholder="form.loading ? 'loading…' : '123456:ABC-DEF…'"
                        spellcheck="false"
                        autocomplete="off"
                        rows="3"
                    />

                    <label class="field-label" for="s-tg-chat">telegram chat id</label>
                    <input
                        id="s-tg-chat"
                        v-model="form.telegramChatId"
                        :disabled="form.loading"
                        :placeholder="form.loading ? 'loading…' : '123456789'"
                        spellcheck="false"
                        autocomplete="off"
                    />

                    <div class="actions">
                        <button type="button" class="btn btn--ghost" @click="emit('close')">cancel</button>
                        <button
                            type="submit"
                            class="btn btn--accent"
                            :disabled="form.saving || form.loading || !form.ollamaUrl.trim()"
                        >{{ form.saving ? 'saving…' : 'save' }}</button>
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
    max-width: 420px;
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
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 18px;
}
.field-label {
    color: var(--text-faint);
    font-size: var(--size-sm);
    letter-spacing: var(--tracking);
}
input, textarea {
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
textarea { resize: vertical; min-height: 2rem; }
input:focus, textarea:focus { border-color: var(--accent-border-focus); }
input:disabled, textarea:disabled { opacity: 0.5; cursor: not-allowed; }
.error-msg {
    margin: 0;
    padding: 6px 8px;
    color: var(--danger);
    background: var(--danger-bg);
    border: 1px solid var(--danger);
    border-radius: var(--radius);
    font-size: var(--size-sm);
    word-break: break-word;
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
