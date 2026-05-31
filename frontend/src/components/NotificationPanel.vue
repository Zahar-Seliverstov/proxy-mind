<script setup>
import { ref } from 'vue'
import { Bell, X } from 'lucide-vue-next'
import { useNotificationsStore, NOTIF_ICONS, NOTIF_ICON_FALLBACK } from '../stores/notifications.js'
import { useResize } from '../composables/useResize.js'

const store = useNotificationsStore()
const panelWidth = ref(280)

function fmt(ts) {
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const startResize = useResize(panelWidth, { min: 200, max: 600 })
</script>

<template>
    <Transition name="np">
        <div v-if="store.panelOpen" class="np" :style="{ width: panelWidth + 'px' }">
            <div class="np-inner">
                <div class="np-header">
                    <span class="np-title">Notifications</span>
                    <div class="np-actions">
                        <button
                            v-if="store.all.length"
                            class="np-clear"
                            @click="store.clear()"
                            title="Clear all"
                        >
                            <X :size="14" :stroke-width="1.5" />
                            clear all
                        </button>
                    </div>
                </div>

                <div v-if="!store.all.length" class="np-empty">
                    <Bell :size="32" :stroke-width="1" class="np-empty-icon" />
                    <span>no notifications</span>
                </div>

                <ul v-else class="np-list">
                    <li
                        v-for="n in store.all"
                        :key="n.id"
                        class="np-item"
                        :class="`np-item--${n.type}`"
                    >
                        <component
                            :is="NOTIF_ICONS[n.type] ?? NOTIF_ICON_FALLBACK"
                            :size="14"
                            :stroke-width="1.5"
                            class="np-item-icon"
                        />
                        <div class="np-item-body">
                            <p v-if="n.title" class="np-item-title">{{ n.title }}</p>
                            <p class="np-item-text">{{ n.text }}</p>
                        </div>
                        <span class="np-item-time">{{ fmt(n.ts) }}</span>
                    </li>
                </ul>
            </div>

            <div class="np-resize" @mousedown.prevent="startResize" />
        </div>
    </Transition>
</template>

<style scoped>
.np {
    width: 280px;
    flex-shrink: 0;
    height: 100vh;
    background: var(--bg-panel);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    font-family: var(--font-mono);
    font-size: var(--size-base);
    position: relative;
    overflow: hidden;
}

.np-inner {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
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
    padding: 0 16px;
    height: 46px;
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
    color: var(--text-muted);
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
.np-item:last-child {
    border-bottom: none;
}
.np-item::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 2px;
}
.np-item--info::before    { background: var(--info); }
.np-item--success::before { background: var(--ok); }
.np-item--warn::before    { background: var(--warn); }
.np-item--error::before   { background: var(--danger); }

.np-item-icon {
    flex-shrink: 0;
    margin-top: 1px;
}
.np-item--info    .np-item-icon { color: var(--info); }
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
    font-weight: 600;
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
    transition: width 0.22s cubic-bezier(0.4, 0, 0.2, 1),
                opacity 0.18s ease;
    overflow: hidden;
}
.np-enter-from,
.np-leave-to {
    width: 0 !important;
    opacity: 0;
}

/* Inner content fades in after width opens, hides instantly on close */
.np-enter-from .np-inner { opacity: 0; }
.np-enter-active .np-inner { transition: opacity 0.18s ease 0.15s; }
.np-leave-active .np-inner { opacity: 0; }
</style>
