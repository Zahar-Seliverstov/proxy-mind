<script setup>
import { ref, reactive, onMounted, watchEffect } from 'vue'
import {
    RefreshCw, Bell, Plus, X, ExternalLink, Settings, BookText,
} from 'lucide-vue-next'
import PulseDot from './PulseDot.vue'
import { dirName } from '../utils.js'
import { useSessionsStore, isPaneAvailable } from '../stores/sessions.js'
import { useNotificationsStore } from '../stores/notifications.js'
import * as sessionsApi from '../api/tmux/sessions.js'
import { useResize } from '../composables/useResize.js'
import NewSessionModal from './NewSessionModal.vue'
import SettingsModal from './SettingsModal.vue'
import PromptsModal from './PromptsModal.vue'

const TITLE  = 'ProxyMind'
const store  = useSessionsStore()
const nStore = useNotificationsStore()

const expanded   = reactive({})
const refreshing = ref(false)
const width      = ref(300)

onMounted(() => { store.start() })

watchEffect(() => {
    document.documentElement.style.setProperty('--sidebar-width', width.value + 'px')
})

function toggle(id) {
    expanded[id] = !expanded[id]
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
        await store.load()
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

const newSessionVisible = ref(false)
const promptsVisible    = ref(false)
const settingsVisible   = ref(false)
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
                                <span class="cmd" :title="p.path">{{ dirName(p.path) }}</span>
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
            <button class="hbtn hbtn-new" @click="newSessionVisible = true" title="New session">
                <Plus :size="16" :stroke-width="1.5" />
                <span class="hbtn-label">new session</span>
            </button>
            <button class="hbtn" title="Instructions" @click="promptsVisible = true">
                <BookText :size="16" :stroke-width="1.5" />
                <span class="hbtn-label">instructions</span>
            </button>
            <button class="hbtn" title="Settings" @click="settingsVisible = true">
                <Settings :size="16" :stroke-width="1.5" />
                <span class="hbtn-label">settings</span>
            </button>
        </div>

        <div class="resize-handle" @mousedown.prevent="startResize" />
    </aside>

    <NewSessionModal :visible="newSessionVisible" @close="newSessionVisible = false" />
    <PromptsModal    :visible="promptsVisible"    @close="promptsVisible = false" />
    <SettingsModal   :visible="settingsVisible"   @close="settingsVisible = false" />

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

header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
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
}

.tc { color: var(--accent); }

.title--offline .tc {
    color: var(--text-trace);
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
.pnode.unavailable {
    cursor: default;
}
.pnode.unavailable:hover {
    background: transparent;
}
.pnode.unavailable .pid,
.pnode.unavailable .cmd {
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
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

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
