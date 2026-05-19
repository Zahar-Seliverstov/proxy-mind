<script setup>
import { ref } from 'vue'
import { useNotificationsStore, NOTIF_ICONS } from '../stores/notifications.js'

const store = useNotificationsStore()
const panel = ref(null)

function fmt(ts) {
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function startResize(e) {
    const startX = e.clientX
    const startW = parseInt(panel.value?.style.width) || 280

    const onMove = (e) => {
        const w = Math.max(200, Math.min(600, startW + e.clientX - startX))
        panel.value.style.width = w + 'px'
    }
    const onUp = () => {
        window.removeEventListener('mousemove', onMove)
        window.removeEventListener('mouseup', onUp)
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
}
</script>

<template>
    <Teleport to="body">
        <Transition name="np">
            <div v-if="store.panelOpen" class="np" ref="panel">
                <div class="np-header">
                    <span class="np-title">Notifications</span>
                    <div class="np-actions">
                        <button
                            v-if="store.all.length"
                            class="np-clear"
                            @click="store.clear()"
                            title="Clear all"
                        >
                            <span class="material-symbols-outlined">close</span>
                            clear all
                        </button>
                    </div>
                </div>

                <div v-if="!store.all.length" class="np-empty">
                    <span class="material-symbols-outlined np-empty-icon">notifications_none</span>
                    <span>no notifications</span>
                </div>

                <ul v-else class="np-list">
                    <li
                        v-for="n in store.all"
                        :key="n.id"
                        class="np-item"
                        :class="`np-item--${n.type}`"
                    >
                        <span class="material-symbols-outlined np-item-icon">
                            {{ NOTIF_ICONS[n.type] ?? 'info' }}
                        </span>
                        <div class="np-item-body">
                            <p v-if="n.title" class="np-item-title">{{ n.title }}</p>
                            <p class="np-item-text">{{ n.text }}</p>
                        </div>
                        <span class="np-item-time">{{ fmt(n.ts) }}</span>
                    </li>
                </ul>

                <div class="np-resize" @mousedown.prevent="startResize" />
            </div>
        </Transition>
    </Teleport>
</template>

<style scoped>
.np {
    position: fixed;
    top: 0;
    bottom: 0;
    left: var(--sidebar-width, 260px);
    width: 280px;
    background: var(--bg-panel);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    z-index: 5;
    font-family: var(--font-mono);
    font-size: var(--size-base);
}

.np-resize {
    position: absolute;
    top: 0;
    right: 0;
    width: 4px;
    height: 100%;
    cursor: col-resize;
    z-index: 1;
    transition: background 0.1s;
}
.np-resize:hover,
.np-resize:active {
    background: var(--accent-border-faint);
}

.np-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.8rem 1rem;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
}
.np-title {
    color: var(--text-secondary);
    font-size: var(--size-md);
}
.np-actions {
    display: flex;
    align-items: center;
    gap: 4px;
}
.np-clear {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--text-faint);
    font-family: inherit;
    font-size: var(--size-sm);
    padding: 2px 4px 2px 2px;
    border-radius: var(--radius);
    transition: var(--transition);
    display: flex;
    align-items: center;
    gap: 3px;
}
.np-clear:hover {
    color: var(--danger);
    background: var(--danger-bg);
}
.np-clear .material-symbols-outlined {
    font-size: var(--size-icon);
    line-height: 1;
}

.np-empty {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    color: var(--text-muted);
    font-size: var(--size-sm);
}
.np-empty-icon {
    font-size: 2rem;
    line-height: 1;
}

.np-list {
    list-style: none;
    margin: 0;
    padding: 4px 0;
    overflow-y: auto;
    scrollbar-width: thin;
    flex: 1;
}
.np-item {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 8px 12px 8px 14px;
    border-bottom: 1px solid var(--border-faint);
    position: relative;
}
.np-item::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 2px;
}
.np-item--info::before    { background: var(--accent); }
.np-item--success::before { background: var(--ok); }
.np-item--warn::before    { background: var(--warn); }
.np-item--error::before   { background: var(--danger); }

.np-item-icon {
    font-size: var(--size-icon);
    line-height: 1;
    flex-shrink: 0;
    margin-top: 2px;
}
.np-item--info    .np-item-icon { color: var(--accent); }
.np-item--success .np-item-icon { color: var(--ok); }
.np-item--warn    .np-item-icon { color: var(--warn); }
.np-item--error   .np-item-icon { color: var(--danger); }

.np-item-body {
    flex: 1;
    min-width: 0;
}
.np-item-title {
    margin: 0 0 2px;
    color: var(--text-primary);
    font-size: var(--size-base);
}
.np-item-text {
    margin: 0;
    color: var(--text-secondary);
    font-size: var(--size-sm);
    line-height: 1.4;
    word-break: break-word;
}
.np-item-time {
    color: var(--text-faint);
    font-size: var(--size-xs);
    flex-shrink: 0;
    padding-top: 2px;
}
</style>

<style>
.np-enter-active,
.np-leave-active {
    transition: transform 0.22s cubic-bezier(0.4, 0, 0.2, 1),
                opacity 0.22s ease;
}
.np-enter-from,
.np-leave-to {
    transform: translateX(-12px);
    opacity: 0;
}
</style>
