<script setup>
import { X } from 'lucide-vue-next'
import { NOTIF_ICONS, NOTIF_ICON_FALLBACK } from '../stores/notifications.js'

defineProps({ notification: Object })
defineEmits(['dismiss'])
</script>

<template>
    <div class="n-toast" :class="`n-toast--${notification.type}`">
        <component
            :is="NOTIF_ICONS[notification.type] ?? NOTIF_ICON_FALLBACK"
            :size="16"
            :stroke-width="1.5"
            class="n-icon"
        />
        <div class="n-body">
            <p v-if="notification.title" class="n-title">{{ notification.title }}</p>
            <p class="n-text">{{ notification.text }}</p>
        </div>
        <button class="n-close" @click="$emit('dismiss')" title="Dismiss">
            <X :size="14" :stroke-width="1.5" />
        </button>
    </div>
</template>

<style scoped>
.n-toast {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    min-width: 280px;
    max-width: 400px;
    padding: 10px 10px 10px 14px;
    border-radius: var(--radius);
    background: var(--bg-panel);
    border: 1px solid var(--border-dim);
    border-left-width: 3px;
    box-shadow: var(--shadow-toast);
    font-family: var(--font-mono);
    font-size: var(--size-base);
    pointer-events: all;
}

.n-toast--info    { border-left-color: var(--info); }
.n-toast--success { border-left-color: var(--ok); }
.n-toast--warn    { border-left-color: var(--warn); }
.n-toast--error   { border-left-color: var(--danger); }

.n-icon {
    flex-shrink: 0;
    margin-top: 1px;
}
.n-toast--info    .n-icon { color: var(--info); }
.n-toast--success .n-icon { color: var(--ok); }
.n-toast--warn    .n-icon { color: var(--warn); }
.n-toast--error   .n-icon { color: var(--danger); }

.n-body {
    flex: 1;
    min-width: 0;
}
.n-title {
    margin: 0 0 2px;
    color: var(--text-primary);
    font-size: var(--size-base);
    font-weight: 600;
}
.n-text {
    margin: 0;
    color: var(--text-secondary);
    font-size: var(--size-sm);
    line-height: 1.4;
}

.n-close {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--text-dim);
    display: flex;
    align-items: center;
    padding: 2px;
    border-radius: var(--radius);
    transition: var(--transition);
    flex-shrink: 0;
}
.n-close:hover {
    color: var(--text-secondary);
    background: var(--bg-row-hover);
}
</style>
