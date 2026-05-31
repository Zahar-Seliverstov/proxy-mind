import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { Info, CheckCircle, TriangleAlert, CircleX } from 'lucide-vue-next'

export const NOTIF_ICONS = {
    info:    Info,
    success: CheckCircle,
    warn:    TriangleAlert,
    error:   CircleX,
}

export const NOTIF_ICON_FALLBACK = Info

let _uid = 0

export const useNotificationsStore = defineStore('notifications', () => {
    const all       = ref([])
    const unread    = ref(0)
    const panelOpen = ref(false)
    const _timers   = new Map()

    const toasts = computed(() => {
        if (panelOpen.value) return []
        return all.value.filter(n => !n.dismissed).slice(0, 3)
    })

    function dismiss(id) {
        const timer = _timers.get(id)
        if (timer) { clearTimeout(timer); _timers.delete(id) }
        const n = all.value.find(x => x.id === id)
        if (n) n.dismissed = true
    }

    function push(type, text, title = '') {
        const visible = all.value.filter(n => !n.dismissed)
        if (visible.length >= 3) dismiss(visible[visible.length - 1].id)

        const n = { id: ++_uid, type, text, title, ts: Date.now(), dismissed: false }
        all.value.unshift(n)

        if (!panelOpen.value) unread.value++

        _timers.set(n.id, setTimeout(() => dismiss(n.id), 5000))
        return n.id
    }

    function openPanel() {
        panelOpen.value = true
        unread.value = 0
        _timers.forEach(t => clearTimeout(t))
        _timers.clear()
        all.value.forEach(n => { n.dismissed = true })
    }

    function closePanel() {
        panelOpen.value = false
    }

    function togglePanel() {
        panelOpen.value ? closePanel() : openPanel()
    }

    function clear() {
        _timers.forEach(t => clearTimeout(t))
        _timers.clear()
        all.value = []
        unread.value = 0
    }

    return { all, toasts, unread, panelOpen, push, dismiss, openPanel, closePanel, togglePanel, clear }
})
