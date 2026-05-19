<script setup>
import SessionsPanel from '../components/SessionsPanel.vue'
import ToastStack from '../components/ToastStack.vue'
import PaneWorkspace from '../components/PaneWorkspace.vue'
import { useSessionsStore } from '../stores/sessions.js'

const sessionsStore = useSessionsStore()
</script>

<template>
    <div class="layout">
        <SessionsPanel />
        <main class="content">
            <PaneWorkspace v-if="sessionsStore.selectedPane" />
            <span v-else class="placeholder">select a pane</span>
        </main>
        <ToastStack />
    </div>
</template>

<style scoped>
.layout {
    display: flex;
    height: 100vh;
}

.content {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
}

.placeholder {
    color: var(--text-invisible);
    font-size: var(--size-md);
    font-family: var(--font-mono);
    letter-spacing: var(--tracking);
}
</style>
