<script setup>
import { X } from 'lucide-vue-next'
import { useSessionsStore } from '../stores/sessions.js'
import { dirName } from '../utils.js'

const store = useSessionsStore()
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
                <span class="tb-cmd">{{ dirName(pane.path) }} ({{ pane.command }})</span>
                <button class="tb-close" @click.stop="store.closeTab(pane.id)" title="Close tab">
                    <X :size="13" :stroke-width="2" />
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

.tb-close {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 18px;
    height: 18px;
    margin-left: 4px;
    padding: 0;
    border: none;
    background: none;
    border-radius: var(--radius);
    color: var(--text-muted);
    cursor: pointer;
    transition: background 0.1s, color 0.1s;
    flex-shrink: 0;
}
.tb-close:hover {
    background: var(--danger-bg);
    color: var(--danger);
}
</style>
