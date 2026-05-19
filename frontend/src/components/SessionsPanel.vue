<script setup>
import { ref, reactive, onMounted, onUnmounted, watchEffect } from "vue";
import { useSessionsStore, isPaneAvailable } from "../stores/sessions.js";
import { useNotificationsStore } from "../stores/notifications.js";
import * as sessionsApi from "../api/tmux/sessions.js";
import { fmtPath } from "../utils.js";
import FilePicker from "./FilePicker.vue";
import NotificationPanel from "./NotificationPanel.vue";
import { getSettings, updateSettings } from "../api/settings.js";

const store  = useSessionsStore();
const nStore = useNotificationsStore();

const newSession  = reactive({ name: "", path: "", visible: false });
const settings    = reactive({
    ollamaUrl: "",        initialOllamaUrl: "",
    telegramBotToken: "", initialTelegramBotToken: "",
    telegramChatId: "",   initialTelegramChatId: "",
    visible: false, loading: false, saving: false, error: null,
});
const expanded    = reactive({});
const refreshing  = ref(false);
const showPicker  = ref(false);
const width       = ref(260);
let poll = null;

onMounted(() => { poll = store.startPolling(5000) });
onUnmounted(() => clearInterval(poll));

watchEffect(() => {
    document.documentElement.style.setProperty('--sidebar-width', width.value + 'px');
});

function toggle(id) {
    expanded[id] = !expanded[id];
}

async function submitNewSession() {
    await store.createSession(newSession.name.trim(), newSession.path.trim());
    newSession.name    = "";
    newSession.path    = "";
    newSession.visible = false;
}

async function openSettings() {
    settings.visible = true;
    settings.error   = null;
    settings.loading = true;
    try {
        const data = await getSettings();
        settings.ollamaUrl               = data.ollama_base_url ?? "";
        settings.initialOllamaUrl        = settings.ollamaUrl;
        settings.telegramBotToken        = data.telegram_bot_token ?? "";
        settings.initialTelegramBotToken = settings.telegramBotToken;
        settings.telegramChatId          = data.telegram_chat_id ?? "";
        settings.initialTelegramChatId   = settings.telegramChatId;
    } catch (e) {
        settings.error = String(e);
    } finally {
        settings.loading = false;
    }
}

function closeSettings() {
    settings.visible = false;
    settings.error   = null;
}

async function submitSettings() {
    const ollama = settings.ollamaUrl.trim();
    const token  = settings.telegramBotToken.trim();
    const chat   = settings.telegramChatId.trim();
    if (!ollama) return;

    const patch = {};
    if (ollama !== settings.initialOllamaUrl)          patch.ollama_base_url    = ollama;
    if (token  && token !== settings.initialTelegramBotToken) patch.telegram_bot_token = token;
    if (chat   && chat  !== settings.initialTelegramChatId)   patch.telegram_chat_id   = chat;

    if (Object.keys(patch).length === 0) {
        closeSettings();
        return;
    }

    settings.saving = true;
    settings.error  = null;
    try {
        const data = await updateSettings(patch);
        settings.ollamaUrl               = data.ollama_base_url;
        settings.initialOllamaUrl        = data.ollama_base_url;
        settings.telegramBotToken        = data.telegram_bot_token ?? "";
        settings.initialTelegramBotToken = settings.telegramBotToken;
        settings.telegramChatId          = data.telegram_chat_id ?? "";
        settings.initialTelegramChatId   = settings.telegramChatId;
        nStore.push("success", "Settings saved");
        settings.visible = false;
    } catch (e) {
        settings.error = String(e);
    } finally {
        settings.saving = false;
    }
}

async function manualRefresh() {
    refreshing.value = true;
    const ok = await store.load();
    refreshing.value = false;
    if (ok) nStore.push('info', 'Sessions reloaded');
}

async function attach(sessionName, windowId, paneId) {
    try {
        await sessionsApi.attach(sessionName, windowId, paneId);
    } catch (e) {
        nStore.push('error', String(e));
    }
}

function selectPane(p) {
    if (!isPaneAvailable(p)) {
        nStore.push('warn', `Pane is running '${p.command}'. Open claude or a python script to use it.`, 'Pane unavailable')
        return
    }
    store.selectedPaneId = store.selectedPaneId === p.id ? null : p.id
}

function startResize(e) {
    const startX = e.clientX;
    const startW = width.value;
    const onMove = (e) => {
        width.value = Math.max(200, Math.min(520, startW + e.clientX - startX));
    };
    const onUp = () => {
        window.removeEventListener("mousemove", onMove);
        window.removeEventListener("mouseup", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
}
</script>

<template>
    <aside :style="{ width: width + 'px' }">
        <header>
            <span class="title">ProxyMind</span>
            <div class="header-btns">
                <button
                    class="hbtn hbtn-reload"
                    @click="manualRefresh"
                    :disabled="refreshing"
                    title="Refresh"
                >
                    <span class="material-symbols-outlined" :class="{ spin: refreshing }">refresh</span>
                    <span class="hbtn-label">reload</span>
                </button>
                <button
                    class="hbtn hbtn-bell"
                    :class="{ 'hbtn-bell--active': nStore.panelOpen }"
                    @click="nStore.togglePanel()"
                    title="Notifications"
                >
                    <span class="material-symbols-outlined">notifications</span>
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
                    <span class="dot" :class="{ on: s.attached }">
                        <span v-if="s.attached" class="ping" />
                    </span>
                    <span class="sname">{{ s.name }}</span>
                    <button class="act" @click.stop="store.createWindow(s.name)" title="Add window">
                        <span class="material-symbols-outlined">add</span>
                        <span class="act-label">window</span>
                    </button>
                    <button class="act del" @click.stop="store.removeSession(s.name)" title="Remove">
                        <span class="material-symbols-outlined">close</span>
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
                                <span class="material-symbols-outlined">add</span>
                                <span class="act-label">pane</span>
                            </button>
                            <button class="act open" @click="attach(s.name, w.id, null)" title="Open in terminal">
                                <span class="material-symbols-outlined">open_in_new</span>
                                <span class="act-label">open</span>
                            </button>
                            <button class="act del" @click="store.removeWindow(w.id)" title="Remove">
                                <span class="material-symbols-outlined">close</span>
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
                                    active: store.selectedPaneId === p.id,
                                    unavailable: !isPaneAvailable(p),
                                }"
                                @click.stop="selectPane(p)"
                            >
                                <span class="pid">{{ p.id }}</span>
                                <span class="cmd">{{ p.command }}</span>
                                <span class="path" :title="fmtPath(p.path)">{{ fmtPath(p.path) }}</span>
                                <button class="act del" @click.stop="store.removePane(p.id)" title="Remove">
                                    <span class="material-symbols-outlined">close</span>
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
                            <span class="material-symbols-outlined">folder_open</span>
                        </button>
                    </div>
                    <FilePicker
                        v-if="showPicker"
                        v-model="newSession.path"
                        @close="showPicker = false"
                    />
                    <div class="new-form-actions">
                        <button type="button" class="btn btn--ghost" @click="newSession.visible = false">cancel</button>
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
                    <span class="material-symbols-outlined">add</span>
                    <span class="hbtn-label">new session</span>
                </button>
                <button class="hbtn" title="Settings" @click="openSettings">
                    <span class="material-icons-outlined">settings</span>
                    <span class="hbtn-label">settings</span>
                </button>
            </template>
        </div>

        <div class="resize-handle" @mousedown.prevent="startResize" />
    </aside>

    <NotificationPanel />
</template>

<style scoped>
aside {
    position: relative;
    z-index: 10;
    height: 100vh;
    min-width: 10rem;
    background: var(--bg-panel);
    border-right: 0.1rem solid var(--border);
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
    width: 0.4rem;
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
    padding: 0.8rem 1rem;
    border-bottom: 0.1rem solid var(--border);
    flex-shrink: 0;
}
.title {
    flex: 1;
    color: var(--accent);
    font-size: var(--size-md);
    font-weight: 600;
    letter-spacing: 0.1rem;
    text-transform: uppercase;
}

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

.spin {
    animation: spin 0.7s linear infinite;
}

/* ── header button ── */
.hbtn {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--text-subdued);
    display: flex;
    align-items: center;
    padding: 0.2rem;
    border-radius: 0.2rem;
    transition: var(--transition);
}
.hbtn:hover {
    color: var(--text-primary);
    background: var(--border);
}
.hbtn:disabled {
    opacity: 0.3;
    cursor: default;
}
.hbtn .material-symbols-outlined,
.hbtn .material-icons-outlined {
    font-size: var(--size-lg);
    vertical-align: middle;
}
.hbtn-new {
    gap: 0.3rem;
    color: var(--accent);
}
.hbtn-new:hover {
    color: var(--accent-hover);
    background: var(--accent-bg);
}
.hbtn-reload {
    gap: 0.3rem;
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

/* ── new session form ── */
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
.btn-pick-dir .material-symbols-outlined {
    font-size: var(--size-icon);
    line-height: 1;
}
.new-form-actions {
    display: flex;
    gap: 6px;
    justify-content: flex-end;
}
.new-form input:disabled,
.new-form textarea:disabled {
    opacity: 0.5;
    cursor: not-allowed;
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

/* ── status ── */
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

/* ── status dot + ping ── */
.dot {
    position: relative;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
    background: var(--border-dim);
    border: 1px solid var(--text-muted);
}
.dot.on {
    background: var(--ok);
    border: none;
}
.ping {
    position: absolute;
    inset: 0;
    border-radius: 50%;
    border: 1px solid var(--ok);
    animation: ping 2.5s ease-out infinite;
}
@keyframes ping {
    0%   { transform: scale(1);  opacity: 0.7; }
    65%  { transform: scale(2);  opacity: 0; }
    100% { transform: scale(2);  opacity: 0; }
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
    color: var(--text-muted);
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
.pnode.active {
    background: var(--accent-bg-rest);
}
.pnode.active .pid {
    color: var(--accent-hover);
}
.pnode.active .path {
    color: var(--accent-text-dim);
}
.pnode.unavailable {
    opacity: 0.35;
    cursor: default;
}
.pnode.unavailable:hover {
    background: transparent;
}
.pnode.unavailable:hover .act {
    opacity: 1;
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
    color: var(--accent);
    font-size: var(--size-sm);
    flex-shrink: 0;
}
.cmd {
    color: var(--text-secondary);
    font-size: var(--size-base);
    flex-shrink: 0;
}
.path {
    color: var(--text-trace);
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
    color: var(--text-muted);
    display: flex;
    align-items: center;
    flex-shrink: 0;
    transition: var(--transition);
}
.act:hover {
    color: var(--accent);
    background: var(--accent-bg);
}
.act.open:hover {
    color: var(--warn);
    background: var(--warn-bg);
}
.act.del:hover {
    color: var(--danger);
    background: var(--danger-bg);
}
.act .material-symbols-outlined {
    font-size: var(--size-icon);
    line-height: 1;
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
