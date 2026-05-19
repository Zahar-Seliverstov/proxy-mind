<script setup>
import { useNotificationsStore } from '../stores/notifications.js'
import Notification from './Notification.vue'

const store = useNotificationsStore()
</script>

<template>
    <Teleport to="body">
        <div class="ts-wrap" aria-live="polite" aria-atomic="false">
            <TransitionGroup name="toast" tag="div" class="ts-list">
                <Notification
                    v-for="n in store.toasts"
                    :key="n.id"
                    :notification="n"
                    @dismiss="store.dismiss(n.id)"
                />
            </TransitionGroup>
        </div>
    </Teleport>
</template>

<style scoped>
.ts-wrap {
    position: fixed;
    top: 16px;
    left: calc(var(--sidebar-width, 260px) + 12px);
    z-index: 9000;
    pointer-events: none;
}

.ts-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    align-items: flex-start;
}
</style>

<style>
.toast-enter-active {
    animation: toast-in 0.24s cubic-bezier(0.34, 1.4, 0.64, 1);
}
.toast-leave-active {
    transition: opacity 0.18s ease, transform 0.18s ease;
}
.toast-leave-to {
    opacity: 0;
    transform: translateY(-8px) scale(0.95);
}
.toast-move {
    transition: transform 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes toast-in {
    from {
        opacity: 0;
        transform: translateY(-16px) scale(0.95);
    }
    to {
        opacity: 1;
        transform: translateY(0) scale(1);
    }
}
</style>
