import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const NOTIF_ICONS = {
    info:    'info',
    success: 'check_circle',
    warn:    'warning',
    error:   'error',
}

let _uid = 0

export const useNotificationsStore = defineStore('notifications', () => {
    const all       = ref([])
    const unread    = ref(0)
    const panelOpen = ref(false)

    const toasts = computed(() => {
        if (panelOpen.value) return []
        return all.value.filter(n => !n.dismissed).slice(0, 3)
    })

    function push(type, text, title = '') {
        const visible = all.value.filter(n => !n.dismissed)
        if (visible.length >= 3) visible[visible.length - 1].dismissed = true

        const n = { id: ++_uid, type, text, title, ts: Date.now(), dismissed: false }
        all.value.unshift(n)
        unread.value++

        setTimeout(() => dismiss(n.id), 5000)
        return n.id
    }

    function dismiss(id) {
        const n = all.value.find(x => x.id === id)
        if (n) n.dismissed = true
    }

    function openPanel() {
        panelOpen.value = true
        unread.value = 0
        all.value.forEach(n => { n.dismissed = true })
    }

    function closePanel() {
        panelOpen.value = false
    }

    function togglePanel() {
        panelOpen.value ? closePanel() : openPanel()
    }

    function clear() {
        all.value = []
        unread.value = 0
    }

    return { all, toasts, unread, panelOpen, push, dismiss, openPanel, closePanel, togglePanel, clear }
})
