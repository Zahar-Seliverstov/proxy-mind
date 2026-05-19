<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useNotificationsStore } from '../stores/notifications.js'
import * as aiApi from '../api/ai.js'
import TopBar from './TopBar.vue'

const nStore = useNotificationsStore()

const props = defineProps({
    paneId: { type: String, required: true },
})

const emit = defineEmits(['gone'])

const state     = ref(null)
const acting    = ref(false)
const openSteps = ref(new Set())
const POLL_MS   = 1500

let timer = null

async function poll() {
    try {
        const data = await aiApi.getRun(props.paneId)
        if (!data) {
            state.value = null
            stopPolling()
            emit('gone')
            return
        }
        state.value = data
        if (isTerminal.value && timer) stopPolling()
    } catch {
        state.value = null
        stopPolling()
        emit('gone')
    }
}

function startPolling() {
    if (timer) return
    poll()
    timer = setInterval(poll, POLL_MS)
}

function stopPolling() {
    if (timer) {
        clearInterval(timer)
        timer = null
    }
}

onMounted(startPolling)
onUnmounted(stopPolling)
watch(() => props.paneId, () => {
    stopPolling()
    state.value = null
    openSteps.value = new Set()
    startPolling()
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
    return [...items].reverse()
})

const STEP_ICONS = {
    pending: 'radio_button_unchecked',
    done:    'check',
    running: 'progress_activity',
    error:   'close',
    paused:  'pause',
}

function stepIcon(s) {
    return STEP_ICONS[s] ?? 'circle'
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

const ACTOR_META = {
    working:    { actor: 'cli', icon: 'progress_activity', label: 'cli working'   },
    next_step:  { actor: 'ok',  icon: 'check_circle', label: 'step finished' },
    done:       { actor: 'ok',  icon: 'flag',         label: 'plan finished' },
    ask_user:   { actor: 'cli', icon: 'help',         label: 'cli asked'     },
    auto_reply: { actor: 'ai',  icon: 'bolt',         label: 'ai answered'   },
    error:      { actor: 'cli', icon: 'error',        label: 'cli error'     },
}

function logMeta(e) {
    return ACTOR_META[e.state] ?? { actor: 'cli', icon: 'circle', label: e.state }
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
        if (!timer) startPolling()
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
        stopPolling()
        state.value = null
        emit('gone')
    }
}

</script>

<template>
    <div class="rm">
        <TopBar>
            <button class="btn btn--ghost" :disabled="acting" @click="onCancel">
                <span class="material-symbols-outlined">keyboard_arrow_left</span>
                {{ isTerminal ? 'back' : 'cancel' }}
            </button>
            <template #center>
                <span v-if="isRunning" class="rm-pulse">
                    <span class="rm-pulse-ring" />
                </span>
                <span>{{ statusLabel }}</span>
            </template>
            <template #end>
                <button v-if="isRunning" class="btn btn--warn" :disabled="acting" @click="onPause">
                    <span class="material-symbols-outlined">pause</span>
                    pause
                </button>
                <button v-if="isUserPaused" class="btn btn--accent" :disabled="acting" @click="onResumeUser">
                    <span class="material-symbols-outlined">play_arrow</span>
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
                        <span
                            class="material-symbols-outlined rm-step-icon"
                            :class="`rm-step-icon--${stepStatus(i)}`"
                        >{{ stepIcon(stepStatus(i)) }}</span>
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
                            :class="`rm-log-item--${logMeta(e).actor}`"
                        >
                            <span class="material-symbols-outlined rm-log-icon">{{ logMeta(e).icon }}</span>
                            <div class="rm-log-body">
                                <div class="rm-log-head">
                                    <span class="rm-log-actor">{{ logMeta(e).label }}</span>
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

/* ── top center pulse ── */
.rm-pulse {
    position: relative;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--accent);
    flex-shrink: 0;
}
.rm-pulse-ring {
    position: absolute;
    inset: 0;
    border-radius: 50%;
    border: 1px solid var(--accent);
    animation: ring-expand 2s ease-out infinite;
}

/* ── step list ── */
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
    font-size: 16px;
    flex-shrink: 0;
    margin-top: 2px;
    line-height: 1;
    color: var(--text-muted);
}
.rm-step-icon--pending { color: var(--text-muted); }
.rm-step-icon--done    { color: var(--ok); }
.rm-step-icon--running { color: var(--accent); animation: spin 1s linear infinite; }
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

/* ── error card ── */
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

/* ── log ── */
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
.rm-log-item--cli { border-left-color: var(--warn);   }
.rm-log-item--ai  { border-left-color: var(--accent); }
.rm-log-item--ok  { border-left-color: var(--ok);     }

.rm-log-icon {
    font-size: var(--size-icon);
    line-height: 1;
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
