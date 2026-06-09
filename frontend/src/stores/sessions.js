import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as sessionsApi from '../api/tmux/sessions.js'
import * as windowsApi  from '../api/tmux/windows.js'
import * as panesApi    from '../api/tmux/panes.js'
import { useNotificationsStore } from './notifications.js'
import { useWebSocket } from '../composables/useWebSocket.js'

const ALLOWED_COMMANDS = ['claude', 'python', 'python3']
export const isPaneAvailable = (p) => ALLOWED_COMMANDS.includes(p?.command)

export const useSessionsStore = defineStore('sessions', () => {
    const sessions        = ref([])
    const loading         = ref(false)
    const serverOnline    = ref(false)
    const openedPaneIds   = ref([])
    const activeTabPaneId = ref(null)
    const panePhases      = ref({})

    function findPane(id) {
        for (const s of sessions.value)
            for (const w of s.windows)
                for (const p of w.panes)
                    if (p.id === id) return p
        return null
    }

    const openedPanes   = computed(() => openedPaneIds.value.map(findPane).filter(Boolean))
    const activeTabPane = computed(() => activeTabPaneId.value ? findPane(activeTabPaneId.value) : null)

    function openTab(paneId) {
        if (!openedPaneIds.value.includes(paneId))
            openedPaneIds.value.push(paneId)
        activeTabPaneId.value = paneId
    }

    function closeTab(paneId) {
        const idx = openedPaneIds.value.indexOf(paneId)
        if (idx === -1) return
        openedPaneIds.value.splice(idx, 1)
        if (activeTabPaneId.value === paneId)
            activeTabPaneId.value = openedPaneIds.value[Math.max(0, idx - 1)] ?? null
    }

    function _applyTree(newSessions) {
        sessions.value = newSessions
        const valid = new Set(
            newSessions.flatMap(s => s.windows).flatMap(w => w.panes)
                .filter(isPaneAvailable).map(p => p.id)
        )
        openedPaneIds.value = openedPaneIds.value.filter(id => valid.has(id))
        if (activeTabPaneId.value && !valid.has(activeTabPaneId.value))
            activeTabPaneId.value = openedPaneIds.value.at(-1) ?? null
        serverOnline.value = true
    }

    async function load() {
        loading.value = true
        try {
            const tree = await sessionsApi.getAll()
            _applyTree(tree)
            return true
        } catch {
            serverOnline.value = false
            return false
        } finally {
            loading.value = false
        }
    }

    async function act(fn, successMsg = null) {
        try {
            await fn()

            await new Promise(r => setTimeout(r, 200))
            await load()
            if (successMsg) useNotificationsStore().push('success', successMsg)
        } catch (e) {
            useNotificationsStore().push('error', String(e))
        }
    }

    let _offWsInit = null
    let _offWsTree = null
    let _onVisible = null

    function start() {

        _offWsInit?.(); _offWsTree?.()
        if (_onVisible) {
            window.removeEventListener('focus', _onVisible)
            document.removeEventListener('visibilitychange', _onVisible)
        }
        const ws = useWebSocket()
        _offWsInit = ws.on('init',      (msg) => { if (msg.sessions) _applyTree(msg.sessions) })
        _offWsTree = ws.on('tmux:tree', (msg) => { _applyTree(msg.sessions) })

        _onVisible = () => { if (!document.hidden) load() }
        window.addEventListener('focus', _onVisible)
        document.addEventListener('visibilitychange', _onVisible)

        load()
    }

    function setPanePhase(paneId, phase) {
        if (phase == null) {
            const copy = { ...panePhases.value }
            delete copy[paneId]
            panePhases.value = copy
        } else {
            panePhases.value = { ...panePhases.value, [paneId]: phase }
        }
    }

    return {
        sessions, loading, serverOnline,
        openedPaneIds, openedPanes, activeTabPaneId, activeTabPane,
        panePhases, setPanePhase,
        findPane, openTab, closeTab, load, start,
        createSession: (name, path)               => act(() => sessionsApi.create(name, path), `Session "${name}" created`),
        removeSession: (name)                     => act(() => sessionsApi.remove(name),        `Session "${name}" removed`),
        createWindow:  (sessionName)              => act(() => windowsApi.create(sessionName)),
        removeWindow:  (windowId)                 => act(() => windowsApi.remove(windowId)),
        createPane:    (windowId, vertical, path) => act(() => panesApi.create(windowId, vertical, path)),
        removePane:    (paneId)                   => act(() => panesApi.remove(paneId)),
    }
})
