<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import {
    ChevronLeft, Pause, Play,
    Circle, Check, LoaderCircle, X,
    CheckCircle, Flag, CircleHelp, Zap, CircleX,
} from 'lucide-vue-next'
import PulseDot from './PulseDot.vue'
import { useNotificationsStore } from '../stores/notifications.js'
import * as aiApi from '../api/ai.js'
import TopBar from './TopBar.vue'
import { useWebSocket } from '../composables/useWebSocket.js'

const nStore = useNotificationsStore()

const props = defineProps({
    paneId: { type: String, required: true },
})

const emit = defineEmits(['gone'])

const state     = ref(null)
const acting    = ref(false)
const openSteps = ref(new Set())

const ws = useWebSocket()
let _offStatus = null
let _offEvent  = null
let _offInit   = null

function _applySnapshot(snap) {
    if (!snap) {
        state.value = null
        emit('gone')
        return
    }
    state.value = snap
}

function _applyEvent(msg) {
    if (!state.value) return
    const entry = { ...msg.entry }

    const log = state.value.log ?? []

    if (entry.seq != null && log.some(e => e.seq === entry.seq)) return
    if (entry.seq == null && log.some(e => e.at === entry.at && e.step_index === entry.step_index)) return
    state.value = {
        ...state.value,
        step_index:    msg.step_index ?? state.value.step_index,
        status:        msg.status     ?? state.value.status,
        log:           [...log, entry],
        last_decision: entry,
    }
}

function subscribe() {
    unsubscribe()
    _offStatus = ws.on('run:status', (msg) => {
        if (msg.pane_id !== props.paneId) return
        _applySnapshot(msg.snapshot ?? null)
    })
    _offEvent = ws.on('run:event', (msg) => {
        if (msg.pane_id !== props.paneId) return
        _applyEvent(msg)
    })

    _offInit = ws.on('init', (msg) => {
        _applySnapshot(msg.runs?.[props.paneId] ?? null)
    })
    aiApi.getRun(props.paneId).then(_applySnapshot).catch(() => {})
}

function unsubscribe() {
    _offStatus?.(); _offStatus = null
    _offEvent?.();  _offEvent  = null
    _offInit?.();   _offInit   = null
}

onMounted(subscribe)
onUnmounted(unsubscribe)
watch(() => props.paneId, () => {
    state.value = null
    openSteps.value = new Set()
    subscribe()
})

const status       = computed(() => state.value?.status ?? 'loading')
const isRunning    = computed(() => status.value === 'running')
const isUserPaused = computed(() => status.value === 'user_paused')
const isTerminal   = computed(() => ['done', 'error', 'stopped'].includes(status.value))
const statusLabel  = computed(() => status.value === 'user_paused' ? 'paused' : status.value)

const steps = computed(() => state.value?.steps ?? [])
const error = computed(() => state.value?.error ?? null)

const log = computed(() => {
    const items = state.value?.log ?? []
    return [...items].reverse().map(e => ({
        ...e,
        meta: ACTOR_META[e.state] ?? { actor: 'cli', icon: CircleX, label: e.state },
    }))
})

const STEP_ICONS = {
    pending: Circle,
    done:    Check,
    running: LoaderCircle,
    error:   X,
    paused:  Pause,
}

const ACTOR_META = {
    working:    { actor: 'cli', icon: LoaderCircle, label: 'cli working'   },
    next_step:  { actor: 'ok',  icon: CheckCircle,  label: 'step finished' },
    done:       { actor: 'ok',  icon: Flag,         label: 'plan finished' },
    ask_user:   { actor: 'cli', icon: CircleHelp,   label: 'cli asked'     },
    auto_reply: { actor: 'ai',  icon: Zap,          label: 'ai answered'   },
    error:      { actor: 'cli', icon: CircleX,      label: 'cli error'     },
}

function stepIcon(s) {
    return STEP_ICONS[s] ?? Circle
}

function stepStatus(i) {
    const s = state.value
    if (!s) return 'pending'
    if (s.status === 'done')        return 'done'
    if (i < s.step_index)           return 'done'
    if (i > s.step_index)           return 'pending'
    if (s.status === 'error')       return 'error'
    if (s.status === 'running')     return 'running'
    if (s.status === 'user_paused') return 'paused'
    if (s.status === 'stopped')     return 'pending'
    return 'pending'
}

function toggleStep(i) {
    const next = new Set(openSteps.value)
    if (next.has(i)) next.delete(i); else next.add(i)
    openSteps.value = next
}

function oneLine(text) {
    return (text ?? '').replace(/\s+/g, ' ').trim()
}

function fmtTime(t) {
    if (!t) return ''
    const d = new Date(t * 1000)
    return d.toLocaleTimeString('en-GB', { hour12: false })
}

function logStepLabel(e) {
    return e.state === 'done' ? '' : `step ${(e.step_index ?? 0) + 1}`
}

async function onPause() {
    if (acting.value) return
    acting.value = true
    try {
        state.value = await aiApi.pauseRun(props.paneId)
    } catch (e) {
        nStore.push('error', String(e), 'Pause failed')
    } finally {
        acting.value = false
    }
}

async function onResumeUser() {
    if (acting.value) return
    acting.value = true
    try {
        state.value = await aiApi.unpauseRun(props.paneId)
    } catch (e) {
        nStore.push('error', String(e), 'Resume failed')
    } finally {
        acting.value = false
    }
}

async function onCancel() {
    if (acting.value) return
    acting.value = true
    try {
        await aiApi.stopRun(props.paneId)
    } catch (e) {
        nStore.push('error', String(e), 'Cancel failed')
    } finally {
        acting.value = false
        state.value = null
        emit('gone')
    }
}

</script>

<template>
    <div class="rm">
        <TopBar>
            <button class="btn btn--ghost" :disabled="acting" @click="onCancel">
                <ChevronLeft :size="14" :stroke-width="1.5" />
                {{ isTerminal ? 'back' : 'cancel' }}
            </button>
            <template #center>
                <PulseDot v-if="isRunning" />
                <span class="rm-status" :class="`rm-status--${status}`">{{ statusLabel }}</span>
            </template>
            <template #end>
                <button v-if="isRunning" class="btn btn--warn" :disabled="acting" @click="onPause">
                    <Pause :size="14" :stroke-width="1.5" />
                    pause
                </button>
                <button v-if="isUserPaused" class="btn btn--accent" :disabled="acting" @click="onResumeUser">
                    <Play :size="14" :stroke-width="1.5" />
                    resume
                </button>
            </template>
        </TopBar>

        <div class="rm-body">

            <div v-if="!state" class="rm-empty">loading…</div>

            <template v-else>

                <div class="rm-steps">
                    <div
                        v-for="(step, i) in steps"
                        :key="i"
                        class="rm-step"
                        :class="{ 'rm-step--open': openSteps.has(i) }"
                        @click="toggleStep(i)"
                    >
                        <component
                            :is="stepIcon(stepStatus(i))"
                            :size="16"
                            :stroke-width="1.5"
                            class="rm-step-icon"
                            :class="[`rm-step-icon--${stepStatus(i)}`, { spin: stepStatus(i) === 'running' }]"
                        />
                        <span class="rm-step-num">{{ String(i + 1).padStart(2, '0') }}</span>
                        <div class="rm-step-text" :class="{ 'rm-step-text--collapsed': !openSteps.has(i) }">
                            {{ openSteps.has(i) ? step : oneLine(step) }}
                        </div>
                    </div>
                </div>

                <div v-if="error" class="rm-card rm-card--err">
                    <div class="rm-card-title">error</div>
                    <div class="rm-card-body">{{ error }}</div>
                </div>

                <div class="rm-log">
                    <div class="rm-log-title">activity</div>
                    <div v-if="!log.length" class="rm-log-empty">nothing yet</div>
                    <div v-else class="rm-log-list">
                        <div
                            v-for="(e, i) in log"
                            :key="i"
                            class="rm-log-item"
                            :class="`rm-log-item--${e.meta.actor}`"
                        >
                            <component
                                :is="e.meta.icon"
                                :size="14"
                                :stroke-width="1.5"
                                class="rm-log-icon"
                            />
                            <div class="rm-log-body">
                                <div class="rm-log-head">
                                    <span class="rm-log-actor">{{ e.meta.label }}</span>
                                    <span v-if="logStepLabel(e)" class="rm-log-step">{{ logStepLabel(e) }}</span>
                                    <span class="rm-log-time">{{ fmtTime(e.at) }}</span>
                                </div>
                                <div v-if="e.payload?.question" class="rm-log-q">
                                    <span class="rm-log-q-tag">Q</span>
                                    <span class="rm-log-q-text">{{ e.payload.question }}</span>
                                </div>
                                <div v-if="e.payload?.text" class="rm-log-a">
                                    <span class="rm-log-a-tag">A</span>
                                    <span class="rm-log-a-text">{{ e.payload.text }}</span>
                                </div>
                                <div v-if="e.reason" class="rm-log-reason">{{ e.reason }}</div>
                            </div>
                        </div>
                    </div>
                </div>

            </template>

        </div>
    </div>
</template>

<style scoped>
.rm {
    display: flex;
    flex-direction: column;
    width: 100%;
    flex: 1;
    min-height: 0;
    font-family: var(--font-mono);
    font-size: var(--size-base);
}

.rm-body {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 14px 16px 18px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    scrollbar-width: thin;
}

.rm-empty {
    color: var(--text-muted);
    text-align: center;
    padding: 24px;
}

.rm-status { color: var(--text-faint); }
.rm-status--running     { color: var(--accent); }
.rm-status--done        { color: var(--ok); }
.rm-status--error       { color: var(--danger); }
.rm-status--user_paused { color: var(--warn); }
.rm-status--stopped     { color: var(--text-dim); }

.rm-steps {
    display: flex;
    flex-direction: column;
    gap: 4px;
    width: 100%;
    min-width: 0;
    overflow: hidden;
}
.rm-step {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    min-width: 0;
    overflow: hidden;
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 8px 10px;
    cursor: pointer;
    transition: border-color 0.1s, background 0.1s;
}
.rm-step:hover { border-color: var(--border-dim); }
.rm-step--open { background: var(--bg-input); }

.rm-step-icon {
    flex-shrink: 0;
    margin-top: 2px;
    color: var(--text-muted);
}
.rm-step-icon--pending { color: var(--text-muted); }
.rm-step-icon--done    { color: var(--ok); }
.rm-step-icon--running { color: var(--accent); }
.rm-step-icon--error   { color: var(--danger); }
.rm-step-icon--paused  { color: var(--warn); }

.rm-step-num {
    font-size: var(--size-xs);
    color: var(--text-faint);
    flex-shrink: 0;
    margin-top: 3px;
    min-width: 16px;
    letter-spacing: var(--tracking);
}

.rm-step-text {
    flex: 1;
    min-width: 0;
    color: var(--text-primary);
    font-size: var(--size-base);
    line-height: 1.55;
    white-space: pre-wrap;
    word-break: break-word;
    overflow-wrap: anywhere;
}
.rm-step-text--collapsed {
    white-space: nowrap !important;
    overflow: hidden;
    text-overflow: ellipsis;
    word-break: normal !important;
    overflow-wrap: normal !important;
}

.rm-card {
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--bg-panel);
    padding: 10px 12px;
}
.rm-card--err { border-color: var(--danger); }
.rm-card-title {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--text-faint);
    font-size: var(--size-sm);
    letter-spacing: var(--tracking);
    margin-bottom: 6px;
}
.rm-card-body {
    color: var(--text-primary);
    font-size: var(--size-base);
    line-height: 1.55;
    white-space: pre-wrap;
    word-break: break-word;
}

.rm-log {
    display: flex;
    flex-direction: column;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--bg-panel);
    padding: 10px 12px;
}
.rm-log-title {
    color: var(--text-faint);
    font-size: var(--size-sm);
    letter-spacing: var(--tracking);
    margin-bottom: 8px;
}
.rm-log-empty {
    color: var(--text-muted);
    font-size: var(--size-sm);
    padding: 6px 2px;
}
.rm-log-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.rm-log-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 8px 10px;
    background: var(--bg-input);
    border: 1px solid var(--border-dim);
    border-left: 2px solid var(--text-muted);
    border-radius: var(--radius);
}
.rm-log-item--cli { border-left-color: var(--warn); }
.rm-log-item--ai  { border-left-color: var(--accent); }
.rm-log-item--ok  { border-left-color: var(--ok); }

.rm-log-icon {
    margin-top: 2px;
    color: var(--text-muted);
    flex-shrink: 0;
}
.rm-log-item--cli .rm-log-icon { color: var(--warn);   }
.rm-log-item--ai  .rm-log-icon { color: var(--accent); }
.rm-log-item--ok  .rm-log-icon { color: var(--ok);     }

.rm-log-body {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
}
.rm-log-head {
    display: flex;
    align-items: baseline;
    gap: 8px;
}
.rm-log-actor {
    color: var(--text-primary);
    font-size: var(--size-sm);
    letter-spacing: var(--tracking);
    text-transform: uppercase;
}
.rm-log-item--cli .rm-log-actor { color: var(--warn);   }
.rm-log-item--ai  .rm-log-actor { color: var(--accent); }
.rm-log-item--ok  .rm-log-actor { color: var(--ok);     }

.rm-log-step {
    color: var(--text-muted);
    font-size: var(--size-xs);
    letter-spacing: var(--tracking);
}
.rm-log-time {
    color: var(--text-muted);
    font-size: var(--size-xs);
    flex-shrink: 0;
    margin-left: auto;
}

.rm-log-q,
.rm-log-a {
    display: flex;
    align-items: flex-start;
    gap: 6px;
    font-size: var(--size-sm);
    line-height: 1.5;
}
.rm-log-q-tag,
.rm-log-a-tag {
    font-size: var(--size-xs);
    letter-spacing: var(--tracking);
    flex-shrink: 0;
    width: 12px;
    text-align: center;
    margin-top: 2px;
    color: var(--text-muted);
}
.rm-log-q-text,
.rm-log-a-text {
    flex: 1;
    color: var(--text-primary);
    white-space: pre-wrap;
    word-break: break-word;
}
.rm-log-a-tag  { color: var(--accent); }

.rm-log-reason {
    color: var(--text-faint);
    font-size: var(--size-xs);
    line-height: 1.4;
    white-space: pre-wrap;
    word-break: break-word;
    font-style: italic;
}
</style>
