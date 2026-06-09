<script setup>
import { onMounted } from 'vue'
import SessionsPanel from '../components/SessionsPanel.vue'
import NotificationPanel from '../components/NotificationPanel.vue'
import ToastStack from '../components/ToastStack.vue'
import TabBar from '../components/TabBar.vue'
import PaneWorkspace from '../components/PaneWorkspace.vue'
import GridBackground from '../components/GridBackground.vue'
import { useSessionsStore } from '../stores/sessions.js'
import { useWebSocket } from '../composables/useWebSocket.js'

const store = useSessionsStore()

onMounted(() => {
    useWebSocket().start()
})
</script>

<template>
    <div class="layout">
        <SessionsPanel />

        <div class="workspace">
            <TabBar v-if="store.openedPaneIds.length" />
            <div class="workspace-body">
                <GridBackground />
                <template v-if="store.openedPaneIds.length">
                    <PaneWorkspace
                        v-for="paneId in store.openedPaneIds"
                        :key="paneId"
                        v-show="paneId === store.activeTabPaneId"
                        :pane-id="paneId"
                    />
                </template>
                <div v-else class="placeholder">
                    <span class="placeholder-text">select a pane</span>
                </div>
            </div>
        </div>

        <NotificationPanel />

        <ToastStack />
    </div>
</template>

<style scoped>
.layout {
    display: flex;
    height: 100vh;
}

.workspace {
    position: relative;
    flex: 1;
    min-width: 320px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}

.workspace-body {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    position: relative;
    isolation: isolate;
}

.placeholder {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    user-select: none;
}
.placeholder-text {
    font-family: var(--font-mono);
    font-size: var(--size-md);
    letter-spacing: var(--tracking);
    color: var(--text-muted);
}
</style>
