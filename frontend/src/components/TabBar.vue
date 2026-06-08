<script setup>
import { X, LoaderCircle } from 'lucide-vue-next'
import { useSessionsStore } from '../stores/sessions.js'
import { fmtPath } from '../utils.js'

const store = useSessionsStore()

const LOADING_PHASES = new Set(['validating', 'questioning', 'generating', 'running'])
const isPaneLoading = (paneId) => LOADING_PHASES.has(store.panePhases[paneId])
</script>

<template>
    <div class="tb">
        <div class="tb-scroller">
            <div
                v-for="pane in store.openedPanes"
                :key="pane.id"
                class="tb-tab"
                :class="{ 'tb-tab--active': pane.id === store.activeTabPaneId }"
                role="tab"
                :aria-selected="pane.id === store.activeTabPaneId"
                tabindex="0"
                @click="store.activeTabPaneId = pane.id"
                @keydown.enter="store.activeTabPaneId = pane.id"
                @keydown.space.prevent="store.activeTabPaneId = pane.id"
                :title="pane.path"
            >
                <LoaderCircle
                    v-if="isPaneLoading(pane.id)"
                    :size="13"
                    :stroke-width="2"
                    class="tb-spinner"
                />
                <span class="tb-cmd">{{ pane.command }}</span>
                <span class="tb-path">{{ fmtPath(pane.path) }}</span>
                <span class="tb-id">{{ pane.id }}</span>
                <button class="tb-close" @click.stop="store.closeTab(pane.id)" title="Close tab">
                    <X :size="11" :stroke-width="2" />
                </button>
            </div>
        </div>
    </div>
</template>

<style scoped>
.tb {
    flex-shrink: 0;
    height: 33px;
    background: var(--bg-panel);
    border-bottom: 1px solid var(--border);
    display: flex;
    overflow: hidden;
}

.tb-scroller {
    display: flex;
    overflow-x: auto;
    overflow-y: hidden;
    scrollbar-width: none;
    flex: 1;
}
.tb-scroller::-webkit-scrollbar { display: none; }

.tb-tab {
    display: flex;
    align-items: center;
    gap: 5px;
    height: 100%;
    padding: 0 8px 0 12px;
    border: none;
    border-right: 1px solid var(--border-faint);
    background: transparent;
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-size: var(--size-sm);
    cursor: pointer;
    white-space: nowrap;
    flex-shrink: 0;
    transition: background 0.1s, color 0.1s;
    position: relative;
}
.tb-tab::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1.5px;
    background: transparent;
    transition: background 0.12s;
}
.tb-tab:hover {
    background: var(--bg-row-hover);
    color: var(--text-secondary);
}
.tb-tab--active {
    background: var(--accent-bg-rest);
    color: var(--text-primary);
}
.tb-tab--active::before {
    background: var(--accent);
}

.tb-cmd {
    color: var(--text-secondary);
    font-size: var(--size-sm);
}
.tb-tab--active .tb-cmd {
    color: var(--text-primary);
}

.tb-path {
    font-size: var(--size-xs);
    color: var(--text-faint);
    max-width: 140px;
    overflow: hidden;
    text-overflow: ellipsis;
}
.tb-tab--active .tb-path {
    color: var(--text-secondary);
}

.tb-id {
    font-size: var(--size-xs);
    color: var(--text-muted);
    letter-spacing: var(--tracking);
}

.tb-close {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 16px;
    height: 16px;
    margin-left: 2px;
    padding: 0;
    border: none;
    background: none;
    border-radius: var(--radius);
    color: var(--text-dim);
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.1s, background 0.1s, color 0.1s;
    flex-shrink: 0;
}
.tb-tab:hover .tb-close,
.tb-tab--active .tb-close {
    opacity: 1;
}
.tb-close:hover {
    background: var(--danger-bg);
    color: var(--danger);
}

.tb-spinner {
    margin-right: 1px;
    color: var(--accent);
    flex-shrink: 0;
    animation: tb-spin 0.8s linear infinite;
}
@keyframes tb-spin {
    to { transform: rotate(360deg); }
}
</style>
