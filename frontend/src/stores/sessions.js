import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as sessionsApi from '../api/tmux/sessions.js'
import * as windowsApi  from '../api/tmux/windows.js'
import * as panesApi    from '../api/tmux/panes.js'
import { useNotificationsStore } from './notifications.js'

const ALLOWED_COMMANDS = ['claude', 'python', 'python3']
export const isPaneAvailable = (p) => ALLOWED_COMMANDS.includes(p?.command)

export const useSessionsStore = defineStore('sessions', () => {
    const sessions       = ref([])
    const loading        = ref(false)
    const selectedPaneId = ref(null)

    const selectedPane = computed(() => {
        if (!selectedPaneId.value) return null
        for (const s of sessions.value)
            for (const w of s.windows)
                for (const p of w.panes)
                    if (p.id === selectedPaneId.value) return p
        return null
    })

    async function load() {
        loading.value = true
        try {
            sessions.value = await sessionsApi.getAll()
            if (selectedPaneId.value && !isPaneAvailable(selectedPane.value)) {
                selectedPaneId.value = null
            }
            return true
        } catch (e) {
            useNotificationsStore().push('error', String(e))
            return false
        } finally {
            loading.value = false
        }
    }

    async function act(fn, successMsg = null) {
        try {
            await fn()
            await load()
            if (successMsg) useNotificationsStore().push('success', successMsg)
        } catch (e) {
            useNotificationsStore().push('error', String(e))
        }
    }

    function startPolling(interval = 2000) {
        load()
        return setInterval(load, interval)
    }

    return {
        sessions, loading, selectedPaneId, selectedPane, load, startPolling,
        createSession: (name, path)             => act(() => sessionsApi.create(name, path), `Session "${name}" created`),
        removeSession: (name)                   => act(() => sessionsApi.remove(name), `Session "${name}" removed`),
        createWindow:  (sessionName)            => act(() => windowsApi.create(sessionName)),
        removeWindow:  (windowId)               => act(() => windowsApi.remove(windowId)),
        createPane:    (windowId, vertical, path) => act(() => panesApi.create(windowId, vertical, path)),
        removePane:    (paneId)                 => act(() => panesApi.remove(paneId)),
    }
})
