<script setup>
import { ref, reactive, onMounted, onUnmounted, watchEffect } from 'vue'
import {
    RefreshCw, Bell, Plus, X, ExternalLink, FolderOpen, Settings,
} from 'lucide-vue-next'
import PulseDot from './PulseDot.vue'
import { useSessionsStore, isPaneAvailable } from '../stores/sessions.js'
import { useNotificationsStore } from '../stores/notifications.js'
import * as sessionsApi from '../api/tmux/sessions.js'
import { fmtPath } from '../utils.js'
import FilePicker from './FilePicker.vue'
import { getSettings, updateSettings } from '../api/settings.js'
import { useResize } from '../composables/useResize.js'

const TITLE  = 'ProxyMind'
const store  = useSessionsStore()
const nStore = useNotificationsStore()

const newSession = reactive({ name: '', path: '', visible: false })
const settings   = reactive({
    ollamaUrl: '',        initialOllamaUrl: '',
    telegramBotToken: '', initialTelegramBotToken: '',
    telegramChatId: '',   initialTelegramChatId: '',
    visible: false, loading: false, saving: false, error: null,
})
const expanded  = reactive({})
const refreshing = ref(false)
const showPicker = ref(false)
const width      = ref(300)
let poll = null

onMounted(() => { poll = store.startPolling(5000) })
onUnmounted(() => clearInterval(poll))

watchEffect(() => {
    document.documentElement.style.setProperty('--sidebar-width', width.value + 'px')
})

function toggle(id) {
    expanded[id] = !expanded[id]
}

async function submitNewSession() {
    await store.createSession(newSession.name.trim(), newSession.path.trim())
    newSession.name    = ''
    newSession.path    = ''
    newSession.visible = false
    showPicker.value   = false
}

function closeNewSession() {
    newSession.visible = false
    showPicker.value   = false
}

async function openSettings() {
    settings.visible = true
    settings.error   = null
    settings.loading = true
    try {
        const data = await getSettings()
        settings.ollamaUrl               = data.ollama_base_url ?? ''
        settings.initialOllamaUrl        = settings.ollamaUrl
        settings.telegramBotToken        = data.telegram_bot_token ?? ''
        settings.initialTelegramBotToken = settings.telegramBotToken
        settings.telegramChatId          = data.telegram_chat_id ?? ''
        settings.initialTelegramChatId   = settings.telegramChatId
    } catch (e) {
        settings.error = String(e)
    } finally {
        settings.loading = false
    }
}

function closeSettings() {
    settings.visible = false
    settings.error   = null
}

async function submitSettings() {
    const ollama = settings.ollamaUrl.trim()
    const token  = settings.telegramBotToken.trim()
    const chat   = settings.telegramChatId.trim()
    if (!ollama) return

    // Only send changed fields. null clears a field, an absent key keeps it:
    // emptying a prefilled token/chat therefore erases it.
    const patch = {}
    if (ollama !== settings.initialOllamaUrl)         patch.ollama_base_url    = ollama
    if (token  !== settings.initialTelegramBotToken)  patch.telegram_bot_token = token || null
    if (chat   !== settings.initialTelegramChatId)    patch.telegram_chat_id   = chat  || null

    if (Object.keys(patch).length === 0) { closeSettings(); return }

    settings.saving = true
    settings.error  = null
    try {
        const data = await updateSettings(patch)
        settings.ollamaUrl               = data.ollama_base_url
        settings.initialOllamaUrl        = data.ollama_base_url
        settings.telegramBotToken        = data.telegram_bot_token ?? ''
        settings.initialTelegramBotToken = settings.telegramBotToken
        settings.telegramChatId          = data.telegram_chat_id ?? ''
        settings.initialTelegramChatId   = settings.telegramChatId
        nStore.push('success', 'Settings saved')
        settings.visible = false
    } catch (e) {
        settings.error = String(e)
    } finally {
        settings.saving = false
    }
}

async function manualRefresh() {
    refreshing.value = true
    const ok = await store.load()
    refreshing.value = false
    if (ok) nStore.push('info', 'Sessions reloaded')
}

async function attach(sessionName, windowId, paneId) {
    try {
        await sessionsApi.attach(sessionName, windowId, paneId)
    } catch (e) {
        nStore.push('error', String(e))
    }
}

function selectPane(p) {
    if (!isPaneAvailable(p)) {
        nStore.push('warn', `Pane is running '${p.command}'. Open claude or a python script to use it.`, 'Pane unavailable')
        return
    }
    store.openTab(p.id)
}

const startResize = useResize(width, { min: 300, max: 520 })
</script>

<template>
    <aside :style="{ width: width + 'px' }">
        <header>
            <span class="title" :class="{ 'title--offline': !store.serverOnline }" aria-label="ProxyMind">
                <span v-for="(ch, i) in TITLE" :key="i" class="tc">{{ ch }}</span>
            </span>
            <div class="header-btns">
                <button
                    class="hbtn hbtn-reload"
                    @click="manualRefresh"
                    :disabled="refreshing"
                    title="Refresh"
                >
                    <RefreshCw :size="16" :stroke-width="1.5" :class="{ spin: refreshing }" />
                    <span class="hbtn-label">reload</span>
                </button>
                <button
                    class="hbtn hbtn-bell"
                    :class="{ 'hbtn-bell--active': nStore.panelOpen }"
                    @click="nStore.togglePanel()"
                    title="Notifications"
                >
                    <Bell :size="16" :stroke-width="1.5" />
                    <span v-if="nStore.unread > 0" class="bell-badge">
                        {{ nStore.unread > 99 ? '99+' : nStore.unread }}
                    </span>
                </button>
            </div>
        </header>

        <div v-if="store.loading && !store.sessions.length" class="msg">loading...</div>
        <div v-else-if="!store.sessions.length" class="msg">no sessions</div>

        <ul v-else>
            <li v-for="s in store.sessions" :key="s.id">
                <div class="srow" @click="toggle(s.id)">
                    <PulseDot
                        :active="s.attached" :size="7"
                        color="var(--ok)"
                    />
                    <span class="sname">{{ s.name }}</span>
                    <button class="act" @click.stop="store.createWindow(s.name)" title="Add window">
                        <Plus :size="14" :stroke-width="1.5" />
                        <span class="act-label">window</span>
                    </button>
                    <button class="act del" @click.stop="store.removeSession(s.name)" title="Remove">
                        <X :size="14" :stroke-width="1.5" />
                        <span class="act-label">kill</span>
                    </button>
                </div>

                <div v-if="expanded[s.id]" class="tree">
                    <div
                        v-for="(w, wi) in s.windows"
                        :key="w.id"
                        class="wnode"
                        :class="{ last: wi === s.windows.length - 1 }"
                    >
                        <div class="wrow">
                            <span class="wname">{{ w.name }}</span>
                            <button
                                class="act"
                                @click="store.createPane(w.id, false, w.panes[0]?.path ?? s.path)"
                                title="Split pane"
                            >
                                <Plus :size="14" :stroke-width="1.5" />
                                <span class="act-label">pane</span>
                            </button>
                            <button class="act open" @click="attach(s.name, w.id, null)" title="Open in terminal">
                                <ExternalLink :size="14" :stroke-width="1.5" />
                                <span class="act-label">open</span>
                            </button>
                            <button class="act del" @click="store.removeWindow(w.id)" title="Remove">
                                <X :size="14" :stroke-width="1.5" />
                                <span class="act-label">kill</span>
                            </button>
                        </div>

                        <div class="ptree">
                            <div
                                v-for="(p, pi) in w.panes"
                                :key="p.id"
                                class="pnode"
                                :class="{
                                    last: pi === w.panes.length - 1,
                                    tabbed: store.openedPaneIds.includes(p.id) && store.activeTabPaneId !== p.id,
                                    active: store.activeTabPaneId === p.id,
                                    unavailable: !isPaneAvailable(p),
                                }"
                                @click.stop="selectPane(p)"
                            >
                                <span class="pid">{{ p.id }}</span>
                                <span class="cmd">{{ p.command }}</span>
                                <span class="path" :title="fmtPath(p.path)">{{ fmtPath(p.path) }}</span>
                                <button class="act del" @click.stop="store.removePane(p.id)" title="Remove">
                                    <X :size="14" :stroke-width="1.5" />
                                    <span class="act-label">kill</span>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </li>
        </ul>

        <div class="bottom">
            <template v-if="newSession.visible">
                <form class="new-form" @submit.prevent="submitNewSession">
                    <input v-model="newSession.name" placeholder="name (auto if empty)" autofocus />
                    <div v-if="!showPicker" class="path-row">
                        <input v-model="newSession.path" placeholder="path" />
                        <button
                            type="button"
                            class="btn-pick-dir"
                            @click="showPicker = true"
                            title="Browse"
                        >
                            <FolderOpen :size="14" :stroke-width="1.5" />
                        </button>
                    </div>
                    <FilePicker
                        v-if="showPicker"
                        v-model="newSession.path"
                        @close="showPicker = false"
                    />
                    <div class="new-form-actions">
                        <button type="button" class="btn btn--ghost" @click="closeNewSession">cancel</button>
                        <button type="submit" class="btn btn--accent">create</button>
                    </div>
                </form>
            </template>
            <template v-else-if="settings.visible">
                <form class="new-form" @submit.prevent="submitSettings">
                    <label class="form-label" for="settings-ollama-url">ollama base url</label>
                    <input
                        id="settings-ollama-url"
                        v-model="settings.ollamaUrl"
                        :disabled="settings.loading"
                        :placeholder="settings.loading ? 'loading…' : 'http://localhost:11434'"
                        spellcheck="false"
                        autocomplete="off"
                        autofocus
                    />
                    <label class="form-label" for="settings-tg-token">telegram bot token</label>
                    <textarea
                        id="settings-tg-token"
                        v-model="settings.telegramBotToken"
                        :disabled="settings.loading"
                        :placeholder="settings.loading ? 'loading…' : '123456:ABC-DEF…'"
                        spellcheck="false"
                        autocomplete="off"
                        rows="3"
                    />
                    <label class="form-label" for="settings-tg-chat">telegram chat id</label>
                    <input
                        id="settings-tg-chat"
                        v-model="settings.telegramChatId"
                        :disabled="settings.loading"
                        :placeholder="settings.loading ? 'loading…' : '123456789'"
                        spellcheck="false"
                        autocomplete="off"
                    />
                    <p v-if="settings.error" class="form-error">{{ settings.error }}</p>
                    <div class="new-form-actions">
                        <button type="button" class="btn btn--ghost" @click="closeSettings">cancel</button>
                        <button
                            type="submit"
                            class="btn btn--accent"
                            :disabled="settings.saving || settings.loading || !settings.ollamaUrl.trim()"
                        >{{ settings.saving ? 'saving…' : 'save' }}</button>
                    </div>
                </form>
            </template>
            <template v-else>
                <button class="hbtn hbtn-new" @click="newSession.visible = true" title="New session">
                    <Plus :size="16" :stroke-width="1.5" />
                    <span class="hbtn-label">new session</span>
                </button>
                <button class="hbtn" title="Settings" @click="openSettings">
                    <Settings :size="16" :stroke-width="1.5" />
                    <span class="hbtn-label">settings</span>
                </button>
            </template>
        </div>

        <div class="resize-handle" @mousedown.prevent="startResize" />
    </aside>

</template>

<style scoped>
aside {
    position: relative;
    z-index: var(--z-sidebar);
    height: 100vh;
    min-width: 300px;
    background: var(--bg-panel);
    border-right: 1px solid var(--border);
    font-family: var(--font-mono);
    font-size: var(--size-md);
    overflow-y: auto;
    overflow-x: hidden;
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
}

/* ── resize handle ── */
.resize-handle {
    position: absolute;
    top: 0;
    right: 0;
    width: 6px;
    height: 100%;
    cursor: col-resize;
    z-index: 10;
}
.resize-handle:hover,
.resize-handle:active {
    background: var(--accent-border-faint);
}

/* ── header ── */
header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
}
@keyframes neon-flicker-rare {
    /* стабильное свечение большую часть цикла */
    0%    { color: var(--char-color); text-shadow: 0 0 6px var(--char-color), 0 0 18px var(--char-glow); transform: none; }
    50%   { color: var(--char-color); text-shadow: 0 0 6px var(--char-color), 0 0 18px var(--char-glow); }
    /* одиночная быстрая искра */
    50.3% { color: var(--text-subdued); text-shadow: none; transform: translateX(0.4px); }
    50.6% { color: var(--char-color); text-shadow: 0 0 12px var(--char-color), 0 0 32px var(--char-glow); transform: none; }
    51%   { color: var(--char-color); text-shadow: 0 0 6px var(--char-color), 0 0 18px var(--char-glow); }
    100%  { color: var(--char-color); text-shadow: 0 0 6px var(--char-color), 0 0 18px var(--char-glow); transform: none; }
}

@keyframes neon-flicker {
    /* ── stable burn: двухслойное свечение, медленный пульс ── */
    0%    { color: var(--char-color); text-shadow: 0 0 6px var(--char-color), 0 0 18px var(--char-glow); transform: none; }
    3%    { color: var(--char-color); text-shadow: 0 0 8px var(--char-color), 0 0 26px var(--char-glow); }
    7%    { color: var(--char-color); text-shadow: 0 0 5px var(--char-color), 0 0 14px var(--char-glow); }
    12%   { color: var(--char-color); text-shadow: 0 0 6px var(--char-color), 0 0 18px var(--char-glow); }

    /* ── событие 1: одиночная искра ── */
    20%   { color: var(--char-color); text-shadow: 0 0 6px var(--char-color), 0 0 18px var(--char-glow); }
    20.3% { color: var(--text-subdued); text-shadow: none; transform: translateX(0.4px); }
    20.6% { color: var(--char-color); text-shadow: 0 0 10px var(--char-color), 0 0 30px var(--char-glow); transform: none; }
    21%   { color: var(--char-color); text-shadow: 0 0 6px var(--char-color), 0 0 18px var(--char-glow); }

    /* ── стабильно ── */
    35%   { color: var(--char-color); text-shadow: 0 0 6px var(--char-color), 0 0 18px var(--char-glow); }
    37%   { color: var(--char-color); text-shadow: 0 0 4px var(--char-glow); }
    39%   { color: var(--char-color); text-shadow: 0 0 6px var(--char-color), 0 0 18px var(--char-glow); }

    /* ── событие 2: долгое отключение, борьба за запуск ── */
    49%   { color: var(--char-color); text-shadow: 0 0 6px var(--char-color), 0 0 18px var(--char-glow); }
    49.5% { color: var(--text-subdued); text-shadow: none; }
    50.2% { color: var(--char-color); text-shadow: 0 0 3px var(--char-glow); }
    50.6% { color: var(--text-subdued); text-shadow: none; transform: translateX(-0.4px); }
    51%   { color: var(--char-color); text-shadow: 0 0 3px var(--char-glow); transform: none; }
    51.4% { color: var(--text-subdued); text-shadow: none; transform: translateX(0.3px); }
    /* напряжение восстановилось — белый выброс ── */
    51.9% { color: #fff; text-shadow: 0 0 4px #fff, 0 0 12px var(--char-color), 0 0 32px var(--char-glow); transform: none; }
    52.4% { color: var(--char-color); text-shadow: 0 0 6px var(--char-color), 0 0 18px var(--char-glow); }

    /* ── стабильно ── */
    66%   { color: var(--char-color); text-shadow: 0 0 6px var(--char-color), 0 0 18px var(--char-glow); }

    /* ── событие 3: двойной моргок ── */
    66.3% { color: var(--text-subdued); text-shadow: none; transform: translateX(0.3px); }
    66.6% { color: var(--char-color); text-shadow: 0 0 9px var(--char-color), 0 0 24px var(--char-glow); transform: none; }
    66.9% { color: var(--text-subdued); text-shadow: none; }
    67.2% { color: var(--char-color); text-shadow: 0 0 6px var(--char-color), 0 0 18px var(--char-glow); }

    /* ── медленный пульс к концу ── */
    82%   { color: var(--char-color); text-shadow: 0 0 6px var(--char-color), 0 0 18px var(--char-glow); }
    86%   { color: var(--char-color); text-shadow: 0 0 9px var(--char-color), 0 0 28px var(--char-glow); }
    92%   { color: var(--char-color); text-shadow: 0 0 5px var(--char-color), 0 0 14px var(--char-glow); }
    100%  { color: var(--char-color); text-shadow: 0 0 6px var(--char-color), 0 0 18px var(--char-glow); transform: none; }
}

.title {
    flex: 1;
    font-size: var(--size-md);
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}

.tc {
    display: inline-block;
    color: var(--char-color);
    text-shadow: 0 0 6px var(--char-color), 0 0 18px var(--char-glow);
}

/* P */
.tc:nth-child(1) { --char-color: #ff2244; --char-glow: rgba(255, 34,  68,.9); animation: neon-flicker-rare linear infinite; animation-duration: 28s; animation-delay: -4.0s; }
/* R */
.tc:nth-child(2) { --char-color: #ff6600; --char-glow: rgba(255,102,   0,.9); }
/* O */
.tc:nth-child(3) { --char-color: #ffcc00; --char-glow: rgba(255,204,   0,.9); }
/* X */
.tc:nth-child(4) { --char-color: #88ee00; --char-glow: rgba(136,238,   0,.9); animation: neon-flicker-rare linear infinite; animation-duration: 32s; animation-delay:-14.8s; }
/* Y */
.tc:nth-child(5) { --char-color: #00ff88; --char-glow: rgba(  0,255, 136,.9); }
/* M */
.tc:nth-child(6) { --char-color: #00ddff; --char-glow: rgba(  0,221, 255,.9); }
/* I */
.tc:nth-child(7) { --char-color: #4488ff; --char-glow: rgba( 68,136, 255,.9); }
/* N */
.tc:nth-child(8) { --char-color: #8844ff; --char-glow: rgba(136, 68, 255,.9); }
/* D */
.tc:nth-child(9) { --char-color: #dd44ff; --char-glow: rgba(221, 68, 255,.9); animation: neon-flicker-rare linear infinite; animation-duration: 24s; animation-delay: -6.5s; }

/* ── offline: трубки погашены ── */
@keyframes neon-dead {
    /* большую часть времени полностью мертва */
    0%,   60% { color: var(--text-trace); text-shadow: none; }
    /* редкая попытка зажечься — не хватает напряжения */
    61%        { color: var(--text-subdued); text-shadow: none; }
    61.4%      { color: var(--text-trace);   text-shadow: none; }
    61.7%      { color: var(--text-muted);   text-shadow: none; }
    62%        { color: var(--text-trace);   text-shadow: none; }
    /* снова мертва */
    62%, 100%  { color: var(--text-trace); text-shadow: none; }
}
.title--offline .tc {
    animation: neon-dead linear infinite;
}
.title--offline .tc:nth-child(1) { animation-duration: 11s; animation-delay: -1.2s; }
.title--offline .tc:nth-child(2) { animation-duration: 17s; animation-delay: -5.8s; }
.title--offline .tc:nth-child(3) { animation-duration:  9s; animation-delay: -3.1s; }
.title--offline .tc:nth-child(4) { animation-duration: 14s; animation-delay: -7.4s; }
.title--offline .tc:nth-child(5) { animation-duration: 12s; animation-delay: -0.9s; }
.title--offline .tc:nth-child(6) { animation-duration: 19s; animation-delay: -4.5s; }
.title--offline .tc:nth-child(7) { animation-duration:  8s; animation-delay: -2.3s; }
.title--offline .tc:nth-child(8) { animation-duration: 16s; animation-delay: -6.1s; }
.title--offline .tc:nth-child(9) { animation-duration: 10s; animation-delay: -8.7s; }

.header-btns {
    display: flex;
    align-items: center;
    gap: 2px;
}

.hbtn-bell {
    position: relative;
}
.hbtn-bell--active {
    color: var(--text-primary);
    background: var(--border);
}

.bell-badge {
    position: absolute;
    top: -3px;
    right: -3px;
    min-width: 14px;
    height: 14px;
    padding: 0 3px;
    background: var(--danger);
    color: #fff;
    font-size: 9px;
    font-family: var(--font-mono);
    line-height: 14px;
    border-radius: 7px;
    text-align: center;
    pointer-events: none;
}

/* ── header button ── */
.hbtn {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--text-subdued);
    display: flex;
    align-items: center;
    padding: 4px;
    border-radius: var(--radius);
    transition: var(--transition);
}
.hbtn:hover {
    color: var(--text-primary);
    background: var(--border);
}
.hbtn:disabled {
    opacity: 0.35;
    cursor: default;
}
.hbtn-new {
    gap: 4px;
    color: var(--accent);
}
.hbtn-new:hover {
    color: var(--accent-hover);
    background: var(--accent-bg-rest);
}
.hbtn-reload {
    gap: 4px;
}
.hbtn-label {
    font-size: var(--size-sm);
    letter-spacing: var(--tracking);
    line-height: 1;
}

/* ── bottom bar ── */
.bottom {
    margin-top: auto;
    border-top: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
}
.bottom .hbtn {
    gap: 8px;
    width: 100%;
    justify-content: flex-start;
    padding: 10px 16px;
    border-radius: 0;
    font-family: inherit;
    font-size: var(--size-base);
    letter-spacing: var(--tracking);
}
.bottom .hbtn .hbtn-label {
    font-size: var(--size-base);
}

/* ── new session / settings form ── */
.new-form {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 12px;
}
.new-form input,
.new-form textarea {
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
}
.new-form textarea {
    resize: vertical;
    min-height: 2rem;
}
.new-form input:focus,
.new-form textarea:focus {
    border-color: var(--accent-border-focus);
}
.new-form input:disabled,
.new-form textarea:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}
.path-row {
    display: flex;
    gap: 4px;
}
.path-row input {
    flex: 1;
}
.btn-pick-dir {
    background: none;
    border: 1px solid var(--border-dim);
    border-radius: var(--radius);
    color: var(--text-dim);
    cursor: pointer;
    padding: 0 6px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    transition: color 0.1s, border-color 0.1s;
}
.btn-pick-dir:hover {
    color: var(--text-primary);
    border-color: var(--text-dim);
}
.new-form-actions {
    display: flex;
    gap: 6px;
    justify-content: flex-end;
}
.form-label {
    color: var(--text-faint);
    font-size: var(--size-sm);
    letter-spacing: var(--tracking);
}
.form-error {
    margin: 0;
    padding: 6px 8px;
    color: var(--danger);
    background: var(--danger-bg);
    border: 1px solid var(--danger);
    border-radius: var(--radius);
    font-size: var(--size-sm);
    word-break: break-word;
}

/* ── status message ── */
.msg {
    padding: 10px 16px;
    color: var(--text-dim);
    font-size: var(--size-base);
}

ul {
    list-style: none;
    margin: 0;
    padding: 4px 0;
}
li {
    border-bottom: 1px solid var(--border-faint);
}
li:last-child {
    border-bottom: none;
}

/* ── session row ── */
.srow {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 7px 8px 7px 16px;
    cursor: pointer;
    user-select: none;
    transition: background 0.1s;
}
.srow:hover {
    background: var(--bg-row-hover);
}
.srow .act {
    opacity: 0;
    margin-left: auto;
}
.srow:hover .act {
    opacity: 1;
}

.sname {
    flex: 1;
    color: var(--text-bright);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

/* ── tree ── */
.tree {
    margin-left: 20px;
    border-left: 1px solid var(--border-dim);
    padding: 2px 0 6px;
}
.wnode {
    position: relative;
}
.wnode::before {
    content: "";
    position: absolute;
    left: 0;
    top: 12px;
    width: 10px;
    height: 1px;
    background: var(--border-dim);
}
.wnode.last::after {
    content: "";
    position: absolute;
    left: -1px;
    top: 12px;
    bottom: -8px;
    width: 1px;
    background: var(--bg-panel);
}

.wrow {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 3px 8px 3px 12px;
    transition: background 0.1s;
}
.wrow:hover {
    background: var(--bg-row-hover);
}
.wname {
    font-size: var(--size-sm);
    color: var(--text-dim);
    flex: 1;
}
.wrow .act {
    opacity: 0;
}
.wrow:hover .act {
    opacity: 1;
}

/* ── pane sub-tree ── */
.ptree {
    cursor: pointer;
    margin-left: 12px;
    border-left: 1px solid var(--border);
    margin-bottom: 2px;
}
.pnode {
    position: relative;
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 3px 8px 3px 12px;
    transition: background 0.1s;
}
.pnode:hover {
    background: var(--bg-row-hover);
}
.pnode.tabbed {
    background: var(--accent-bg-subtle);
}
.pnode.tabbed .pid {
    color: var(--accent-text-dim);
}
.pnode.active {
    background: var(--accent-bg-rest);
}
.pnode.active .pid {
    color: var(--accent);
}
.pnode.active .path {
    color: var(--accent-text-dim);
}
.pnode.unavailable {
    cursor: default;
}
.pnode.unavailable:hover {
    background: transparent;
}
.pnode.unavailable .pid,
.pnode.unavailable .cmd,
.pnode.unavailable .path {
    opacity: 0.35;
}
.pnode::before {
    content: "";
    position: absolute;
    left: 0;
    top: 50%;
    width: 10px;
    height: 1px;
    background: var(--border);
}
.pnode.last::after {
    content: "";
    position: absolute;
    left: -1px;
    top: 50%;
    bottom: -4px;
    width: 1px;
    background: var(--bg-panel);
}
.pnode .act {
    opacity: 0;
}
.pnode:hover .act {
    opacity: 1;
}

.pid {
    color: var(--text-primary);
    font-size: var(--size-sm);
    flex-shrink: 0;
}
.cmd {
    color: var(--text-secondary);
    font-size: var(--size-base);
    flex-shrink: 0;
}
.path {
    color: var(--text-faint);
    font-size: var(--size-sm);
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

/* ── action buttons ── */
.act {
    background: none;
    border: none;
    cursor: pointer;
    padding: 2px 3px;
    border-radius: var(--radius);
    color: var(--text-dim);
    display: flex;
    align-items: center;
    flex-shrink: 0;
    transition: var(--transition);
}
.act:hover {
    color: var(--accent);
    background: var(--accent-bg-rest);
}
.act.open:hover {
    color: var(--warn);
    background: var(--warn-bg);
}
.act.del:hover {
    color: var(--danger);
    background: var(--danger-bg);
}
.act-label {
    font-size: var(--size-xs);
    letter-spacing: var(--tracking);
    white-space: nowrap;
    max-width: 0;
    overflow: hidden;
    opacity: 0;
    transition: max-width 0.15s ease, opacity 0.1s, padding-left 0.15s;
}
.act:hover .act-label {
    max-width: 48px;
    opacity: 1;
    padding-left: 2px;
}
</style>
