<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import {
    ChevronLeft, Pause, Play, ChevronDown,
    Circle, Check, LoaderCircle, X,
    MessageSquare, Zap, AlertCircle, Flag,
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
    if (!snap) { state.value = null; emit('gone'); return }
    state.value = snap
    _autoOpen(snap.step_index)
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

function _autoOpen(idx) {
    if (idx == null) return
    const next = new Set(openSteps.value)
    next.add(idx)
    openSteps.value = next
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
watch(() => state.value?.step_index, (idx) => { if (idx != null) _autoOpen(idx) })

// ── computed ──────────────────────────────────────────────────────────────────

const status        = computed(() => state.value?.status ?? 'loading')
const isRunning     = computed(() => status.value === 'running')
const isUserPaused  = computed(() => status.value === 'user_paused')
const isLimitPaused = computed(() => status.value === 'limit_paused')
const isTerminal    = computed(() => ['done', 'error', 'stopped'].includes(status.value))
const statusLabel   = computed(() => {
    if (status.value === 'user_paused')  return 'paused'
    if (status.value === 'limit_paused') return 'limit reached'
    return status.value
})

const steps = computed(() => state.value?.steps ?? [])
const globalError = computed(() => state.value?.error ?? null)

const logsByStep = computed(() => {
    const map = {}
    for (const e of (state.value?.log ?? [])) {
        const idx = e.step_index ?? 0
        if (!map[idx]) map[idx] = []
        // skip pure "working" noise unless it's the only entry
        if (e.state !== 'working') map[idx].push(e)
    }
    return map
})

function stepStatus(i) {
    const s = state.value
    if (!s) return 'pending'
    if (s.status === 'done')         return 'done'
    if (i < s.step_index)            return 'done'
    if (i > s.step_index)            return 'pending'
    if (s.status === 'error')        return 'error'
    if (s.status === 'running')      return 'running'
    if (s.status === 'user_paused')  return 'paused'
    if (s.status === 'limit_paused') return 'paused'
    if (s.status === 'stopped')      return 'stopped'
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
    return new Date(t * 1000).toLocaleTimeString('en-GB', { hour12: false })
}

// ── log entry helpers ─────────────────────────────────────────────────────────

function entryKind(e) {
    if (e.state === 'ask_user')   return 'ask'
    if (e.state === 'auto_reply') return 'reply'
    if (e.state === 'next_step')  return 'done'
    if (e.state === 'error')      return 'error'
    return 'info'
}

// Pair ask_user + auto_reply entries together so they render as Q/A
function pairedLog(entries) {
    const result = []
    let i = 0
    while (i < entries.length) {
        const e = entries[i]
        if (e.state === 'ask_user') {
            const next = entries[i + 1]
            if (next?.state === 'auto_reply') {
                result.push({ type: 'qa', ask: e, reply: next, key: e.seq ?? e.at })
                i += 2
                continue
            }
        }
        result.push({ type: 'single', entry: e, key: e.seq ?? e.at })
        i++
    }
    return result
}

// ── actions ───────────────────────────────────────────────────────────────────

async function onPause() {
    if (acting.value) return
    acting.value = true
    try { state.value = await aiApi.pauseRun(props.paneId) }
    catch (e) { nStore.push('error', String(e), 'Pause failed') }
    finally { acting.value = false }
}

async function onResumeUser() {
    if (acting.value) return
    acting.value = true
    try { state.value = await aiApi.unpauseRun(props.paneId) }
    catch (e) { nStore.push('error', String(e), 'Resume failed') }
    finally { acting.value = false }
}

async function onResumeLimit() {
    if (acting.value) return
    acting.value = true
    try { state.value = await aiApi.resumeRun(props.paneId) }
    catch (e) { nStore.push('error', String(e), 'Resume failed') }
    finally { acting.value = false }
}

async function onCancel() {
    if (acting.value) return
    acting.value = true
    try { await aiApi.stopRun(props.paneId) }
    catch (e) { nStore.push('error', String(e), 'Cancel failed') }
    finally { acting.value = false; state.value = null; emit('gone') }
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
                <span class="rm-status" :class="`rm-status--${status}`">{{ statusLabel }}</span>
            </template>
            <template #end>
                <button v-if="isRunning" class="btn btn--warn" :disabled="acting" @click="onPause">
                    <Pause :size="14" :stroke-width="1.5" /> pause
                </button>
                <button v-if="isUserPaused" class="btn btn--accent" :disabled="acting" @click="onResumeUser">
                    <Play :size="14" :stroke-width="1.5" /> resume
                </button>
                <button v-if="isLimitPaused" class="btn btn--accent" :disabled="acting" @click="onResumeLimit">
                    <Play :size="14" :stroke-width="1.5" /> resume
                </button>
            </template>
        </TopBar>

        <div class="rm-body">
            <div v-if="!state" class="rm-empty">loading…</div>

            <template v-else>

                <!-- limit banner -->
                <div v-if="isLimitPaused" class="rm-banner rm-banner--warn">
                    <AlertCircle :size="14" :stroke-width="1.5" />
                    CLI hit a usage or billing limit. Top up your balance or wait for the reset, then press <b>resume</b>.
                </div>

                <!-- global error banner -->
                <div v-if="globalError" class="rm-banner rm-banner--err">
                    <AlertCircle :size="14" :stroke-width="1.5" />
                    {{ globalError }}
                </div>

                <!-- steps -->
                <div class="rm-steps">
                    <div
                        v-for="(step, i) in steps"
                        :key="i"
                        class="rm-step"
                        :class="[
                            `rm-step--${stepStatus(i)}`,
                            { 'rm-step--open': openSteps.has(i) }
                        ]"
                    >
                        <!-- step header -->
                        <div class="rm-step-header" @click="toggleStep(i)">
                            <div class="rm-step-icon-wrap">
                                <PulseDot v-if="stepStatus(i) === 'running'" :size="8" />
                                <Check         v-else-if="stepStatus(i) === 'done'"    :size="14" :stroke-width="2"   class="rm-sicon rm-sicon--done" />
                                <X             v-else-if="stepStatus(i) === 'error'"   :size="14" :stroke-width="2"   class="rm-sicon rm-sicon--error" />
                                <Pause         v-else-if="stepStatus(i) === 'paused'"  :size="14" :stroke-width="1.5" class="rm-sicon rm-sicon--paused" />
                                <LoaderCircle  v-else-if="stepStatus(i) === 'stopped'" :size="14" :stroke-width="1.5" class="rm-sicon rm-sicon--stopped" />
                                <Circle        v-else                                  :size="14" :stroke-width="1.5" class="rm-sicon rm-sicon--pending" />
                            </div>
                            <span class="rm-step-num">{{ String(i + 1).padStart(2, '0') }}</span>
                            <div class="rm-step-text">
                                {{ openSteps.has(i) ? step : oneLine(step) }}
                            </div>
                            <div class="rm-step-meta">
                                <span
                                    v-if="(logsByStep[i] ?? []).length && !openSteps.has(i)"
                                    class="rm-step-badge"
                                >{{ logsByStep[i].length }}</span>
                                <ChevronDown
                                    :size="12"
                                    :stroke-width="1.5"
                                    class="rm-step-chevron"
                                    :class="{ 'rm-step-chevron--open': openSteps.has(i) }"
                                />
                            </div>
                        </div>

                        <!-- step log -->
                        <div v-if="openSteps.has(i) && logsByStep[i]?.length" class="rm-step-log">
                            <template v-for="item in pairedLog(logsByStep[i] ?? [])" :key="item.key">

                                <!-- Q/A pair -->
                                <div v-if="item.type === 'qa'" class="rm-log-qa">
                                    <div class="rm-log-qa-q">
                                        <MessageSquare :size="11" :stroke-width="1.5" class="rm-log-qa-icon" />
                                        <span class="rm-log-qa-text">{{ item.ask.payload?.question }}</span>
                                        <span v-if="item.ask.payload?.kind" class="rm-log-badge rm-log-badge--ask">{{ item.ask.payload.kind }}</span>
                                        <span class="rm-log-time">{{ fmtTime(item.ask.at) }}</span>
                                    </div>
                                    <div class="rm-log-qa-a">
                                        <Zap :size="11" :stroke-width="1.5" class="rm-log-qa-icon rm-log-qa-icon--ai" />
                                        <span class="rm-log-qa-answer">{{ item.reply.payload?.text || '—' }}</span>
                                    </div>
                                </div>

                                <!-- single entry -->
                                <template v-else>
                                    <div v-if="entryKind(item.entry) === 'ask'" class="rm-log-qa">
                                        <div class="rm-log-qa-q">
                                            <MessageSquare :size="11" :stroke-width="1.5" class="rm-log-qa-icon" />
                                            <span class="rm-log-qa-text">{{ item.entry.payload?.question }}</span>
                                            <span v-if="item.entry.payload?.kind" class="rm-log-badge rm-log-badge--ask">{{ item.entry.payload.kind }}</span>
                                            <span class="rm-log-time">{{ fmtTime(item.entry.at) }}</span>
                                        </div>
                                    </div>
                                    <div v-else-if="entryKind(item.entry) === 'reply'" class="rm-log-qa">
                                        <div class="rm-log-qa-a">
                                            <Zap :size="11" :stroke-width="1.5" class="rm-log-qa-icon rm-log-qa-icon--ai" />
                                            <span class="rm-log-qa-answer">{{ item.entry.payload?.text || '—' }}</span>
                                        </div>
                                    </div>
                                    <div v-else-if="entryKind(item.entry) === 'error'" class="rm-log-err">
                                        <AlertCircle :size="11" :stroke-width="1.5" />
                                        <span>{{ item.entry.reason }}</span>
                                    </div>
                                    <div v-else-if="entryKind(item.entry) === 'done'" class="rm-log-done">
                                        <Flag :size="11" :stroke-width="1.5" />
                                        <span>step complete</span>
                                        <span class="rm-log-time">{{ fmtTime(item.entry.at) }}</span>
                                    </div>
                                </template>

                            </template>
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
    padding: 12px 14px 18px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    scrollbar-width: thin;
}

.rm-empty {
    color: var(--text-muted);
    text-align: center;
    padding: 24px;
}

/* status chip */
.rm-status { color: var(--text-faint); }
.rm-status--running      { color: var(--text-secondary); }
.rm-status--done         { color: var(--ok); }
.rm-status--error        { color: var(--danger); }
.rm-status--user_paused  { color: var(--warn); }
.rm-status--limit_paused { color: var(--warn); }
.rm-status--stopped      { color: var(--text-dim); }

/* banners */
.rm-banner {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 9px 12px;
    border-radius: var(--radius);
    font-size: var(--size-sm);
    line-height: 1.5;
    border: 1px solid;
}
.rm-banner--warn { border-color: var(--warn);   color: var(--warn);   background: color-mix(in srgb, var(--warn) 8%, transparent); }
.rm-banner--err  { border-color: var(--danger); color: var(--danger); background: color-mix(in srgb, var(--danger) 8%, transparent); }
.rm-banner b { font-weight: 600; }
.rm-banner svg { flex-shrink: 0; margin-top: 1px; }

/* steps list */
.rm-steps {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

/* step card */
.rm-step {
    border: 1px solid var(--border);
    border-radius: calc(var(--radius) * 1.5);
    background: var(--bg-panel);
    overflow: hidden;
    transition: border-color 0.12s;
}
.rm-step--running { border-color: color-mix(in srgb, var(--accent) 40%, var(--border)); }
.rm-step--done    { border-color: color-mix(in srgb, var(--ok) 25%, var(--border)); }
.rm-step--error   { border-color: color-mix(in srgb, var(--danger) 35%, var(--border)); }
.rm-step--paused  { border-color: color-mix(in srgb, var(--warn) 35%, var(--border)); }

/* step header row */
.rm-step-header {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 9px 10px;
    cursor: pointer;
    user-select: none;
}
.rm-step-header:hover { background: color-mix(in srgb, var(--border) 30%, transparent); }

.rm-step-icon-wrap {
    flex-shrink: 0;
    width: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-top: 2px;
}

.rm-sicon          { flex-shrink: 0; }
.rm-sicon--pending { color: var(--text-muted); }
.rm-sicon--done    { color: var(--ok); }
.rm-sicon--error   { color: var(--danger); }
.rm-sicon--paused  { color: var(--warn); }
.rm-sicon--stopped { color: var(--text-dim); }

.rm-step-num {
    flex-shrink: 0;
    font-size: var(--size-xs);
    color: var(--text-faint);
    letter-spacing: var(--tracking);
    margin-top: 3px;
    min-width: 18px;
}

.rm-step-text {
    flex: 1;
    min-width: 0;
    color: var(--text-primary);
    font-size: var(--size-base);
    line-height: 1.55;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.rm-step--open .rm-step-text {
    white-space: pre-wrap;
    word-break: break-word;
    overflow-wrap: anywhere;
    overflow: visible;
}

.rm-step-meta {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 5px;
    margin-top: 2px;
}

.rm-step-badge {
    font-size: 10px;
    color: var(--text-faint);
    background: var(--bg-input);
    border: 1px solid var(--border-dim);
    border-radius: 8px;
    padding: 0 5px;
    line-height: 16px;
}

.rm-step-chevron {
    color: var(--text-muted);
    transition: transform 0.15s;
}
.rm-step-chevron--open { transform: rotate(180deg); }

/* step inline log */
.rm-step-log {
    border-top: 1px solid var(--border);
    padding: 8px 10px 10px 36px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    background: color-mix(in srgb, var(--bg-input) 60%, transparent);
}

/* Q/A block */
.rm-log-qa {
    display: flex;
    flex-direction: column;
    gap: 3px;
}
.rm-log-qa-q,
.rm-log-qa-a {
    display: flex;
    align-items: baseline;
    gap: 6px;
    font-size: var(--size-sm);
    line-height: 1.5;
}
.rm-log-qa-icon {
    flex-shrink: 0;
    margin-top: 2px;
    color: var(--text-muted);
}
.rm-log-qa-icon--ai { color: var(--accent); }
.rm-log-qa-text {
    flex: 1;
    color: var(--text-primary);
    word-break: break-word;
}
.rm-log-qa-answer {
    flex: 1;
    color: var(--accent);
    word-break: break-word;
}
.rm-log-badge {
    flex-shrink: 0;
    font-size: 10px;
    letter-spacing: var(--tracking);
    padding: 0 5px;
    border-radius: 4px;
    line-height: 16px;
    border: 1px solid;
}
.rm-log-badge--ask { color: var(--text-faint); border-color: var(--border-dim); }

.rm-log-time {
    flex-shrink: 0;
    font-size: var(--size-xs);
    color: var(--text-muted);
    margin-left: auto;
}

/* error / done rows */
.rm-log-err,
.rm-log-done {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: var(--size-sm);
    line-height: 1.5;
}
.rm-log-err  { color: var(--danger); }
.rm-log-done { color: var(--ok); }
.rm-log-done .rm-log-time { color: var(--text-muted); }
</style>
