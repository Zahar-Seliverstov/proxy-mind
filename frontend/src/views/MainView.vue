<script setup>
import { ref, watch, onMounted } from 'vue'
import SessionsPanel from '../components/SessionsPanel.vue'
import NotificationPanel from '../components/NotificationPanel.vue'
import ToastStack from '../components/ToastStack.vue'
import TabBar from '../components/TabBar.vue'
import PaneWorkspace from '../components/PaneWorkspace.vue'
import GridBackground from '../components/GridBackground.vue'
import { useSessionsStore } from '../stores/sessions.js'
import { useResize } from '../composables/useResize.js'
import { useWebSocket } from '../composables/useWebSocket.js'

const store = useSessionsStore()

onMounted(() => {
    useWebSocket().start()
})

const workspaceWidth = ref(null)
const startResize = useResize(workspaceWidth, { min: 320 })

const isLoading = ref(false)
function onPaneLoading(paneId, val) {
    if (paneId === store.activeTabPaneId) isLoading.value = val
}
</script>

<template>
    <div class="layout">
        <SessionsPanel />
        <NotificationPanel />

        <div class="workspace" :style="workspaceWidth ? { width: workspaceWidth + 'px', flex: 'none' } : {}">
            <TabBar v-if="store.openedPaneIds.length" />
            <div class="workspace-body">
                <GridBackground :loading="isLoading" />
                <template v-if="store.openedPaneIds.length">
                    <PaneWorkspace
                        v-for="paneId in store.openedPaneIds"
                        :key="paneId"
                        v-show="paneId === store.activeTabPaneId"
                        :pane-id="paneId"
                        @loading="onPaneLoading(paneId, $event)"
                    />
                </template>
                <span v-else class="placeholder">select a pane</span>
            </div>
            <div class="workspace-resize" @mousedown.prevent="startResize" />
        </div>

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

.workspace-resize {
    position: absolute;
    top: 0;
    right: 0;
    width: 6px;
    height: 100%;
    cursor: col-resize;
    z-index: 10;
}
.workspace-resize:hover,
.workspace-resize:active {
    background: var(--accent-border-faint);
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

@keyframes hint-pulse {
    0%, 100% { opacity: 0.28; }
    50%       { opacity: 0.62; }
}

.placeholder {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-secondary);
    font-size: var(--size-md);
    font-family: var(--font-mono);
    letter-spacing: var(--tracking);
    animation: hint-pulse 4s ease-in-out infinite;
    user-select: none;
}
</style>
