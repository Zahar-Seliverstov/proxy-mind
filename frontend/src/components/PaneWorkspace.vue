<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useSessionsStore } from '../stores/sessions.js'
import { useNotificationsStore } from '../stores/notifications.js'
import { getModels } from '../api/ollama.js'
import * as aiApi from '../api/ai.js'
import { fmtPath } from '../utils.js'
import {
    Play, Sparkles, ChevronLeft, RefreshCw,
    Folder, TriangleAlert,
} from 'lucide-vue-next'
import ModelSelect from './ModelSelect.vue'
import ModeSelect from './ModeSelect.vue'
import PlanReview from './PlanReview.vue'
import ClarifyQuestions from './ClarifyQuestions.vue'
import RunMonitor from './RunMonitor.vue'
import TopBar from './TopBar.vue'

const props = defineProps({ paneId: { type: String, required: true } })
const emit  = defineEmits(['loading'])

const store  = useSessionsStore()
const nStore = useNotificationsStore()

const pane = computed(() => store.findPane(props.paneId))

// ── copy-to-clipboard ─────────────────────────────────
const pathCopied = ref(false)
let pathCopyTimer = null
function copyPath() {
    const path = pane.value?.path
    if (!path) return
    navigator.clipboard.writeText(path)
    pathCopied.value = true
    clearTimeout(pathCopyTimer)
    pathCopyTimer = setTimeout(() => { pathCopied.value = false }, 1200)
}

// ── models ────────────────────────────────────────────
const models        = ref([])
const selectedModel = ref('')
const modelsLoading = ref(false)
const modelsFailed  = ref(false)

// ── modes ─────────────────────────────────────────────
const modes        = ref([])
const selectedMode = ref('plan')

// ── caret-following generate button ───────────────────
const generateBtnPos  = ref(null)
const generateBtnReady = ref(false)
let generateBtnTimer = null

function measureCaretPos(el) {
    if (!el || !input.value.trim()) { generateBtnPos.value = null; return }
    const cs  = window.getComputedStyle(el)
    const elR = el.getBoundingClientRect()
    const wrap = document.createElement('div')
    Object.assign(wrap.style, {
        position: 'fixed', top: elR.top + 'px', left: elR.left + 'px',
        width: el.clientWidth + 'px', height: el.clientHeight + 'px',
        overflow: 'hidden', visibility: 'hidden', pointerEvents: 'none',
        boxSizing: 'border-box', padding: cs.padding,
    })
    const inner = document.createElement('div')
    Object.assign(inner.style, {
        position: 'relative', top: -el.scrollTop + 'px',
        whiteSpace: 'pre-wrap', wordBreak: 'break-word', overflowWrap: 'anywhere',
        font: cs.font, lineHeight: cs.lineHeight, letterSpacing: cs.letterSpacing,
    })
    inner.textContent = el.value.substring(0, el.selectionEnd ?? el.value.length)
    const marker = document.createElement('span')
    marker.textContent = '​'
    inner.appendChild(marker)
    wrap.appendChild(inner)
    document.body.appendChild(wrap)
    const mR = marker.getBoundingClientRect()
    document.body.removeChild(wrap)
    const BTN_W = 116, BTN_H = 26, PAD = 12
    const cx = mR.left - elR.left
    const cy = mR.bottom - elR.top
    generateBtnPos.value = {
        left: Math.max(PAD, Math.min(cx - BTN_W / 2, el.clientWidth - BTN_W - PAD)) + 'px',
        top:  Math.max(PAD, Math.min(cy + 18, el.clientHeight - BTN_H - PAD)) + 'px',
    }
    generateBtnReady.value = false
    clearTimeout(generateBtnTimer)
    generateBtnTimer = setTimeout(() => { generateBtnReady.value = true }, 400)
}

// ── input & workflow ──────────────────────────────────
const input           = ref('')
const manualSteps     = ref([])
const originalPrompt  = ref('')
const phase           = ref('idle')
const reviewData      = ref(null)
const currentQuestion = ref(null)
const clarifyHistory  = ref([])
const warnStatus      = ref(null)

// ── computed ──────────────────────────────────────────
const isIdle        = computed(() => phase.value === 'idle')
const isValidating  = computed(() => phase.value === 'validating')
const isWarning     = computed(() => phase.value === 'warning')
const isQuestioning = computed(() => phase.value === 'questioning')
const isClarifying  = computed(() => phase.value === 'clarifying')
const isGenerating  = computed(() => phase.value === 'generating')
const isRunning     = computed(() => phase.value === 'running')
const isReview      = computed(() => phase.value === 'review')
const isLoading     = computed(() => isValidating.value || isQuestioning.value || isGenerating.value || isRunning.value)
watch(isLoading, val => emit('loading', val))

const isActivePane = computed(() => store.activeTabPaneId === props.paneId)
watch(isActivePane, active => { if (active) emit('loading', isLoading.value) })

const isDirectLike = computed(() =>
    selectedMode.value === 'direct' || selectedMode.value === 'manual'
)
const canGenerate = computed(() => {
    if (!selectedModel.value || !isIdle.value) return false
    if (selectedMode.value === 'manual') {
        return manualSteps.value.some(s => s.trim().length > 0)
    }
    return input.value.trim().length > 0
})
const generateLabel = computed(() => isDirectLike.value ? 'run' : 'generate')
const generateIcon  = computed(() => isDirectLike.value ? Play : Sparkles)
const idleTitle     = computed(() => selectedMode.value === 'manual' ? 'new plan' : 'new prompt')
const loadingLabel = computed(() => {
    if (isValidating.value)  return 'checking'
    if (isQuestioning.value) return 'analyzing'
    if (isGenerating.value)  return 'generating'
    if (isRunning.value)     return 'starting'
    return ''
})

// ── run presence detection ────────────────────────────
const hasRun = ref(false)
let runProbeTimer = null
const RUN_PROBE_MS = 5000

async function probeRun() {
    try {
        const data = await aiApi.getRun(props.paneId)
        hasRun.value = !!data
    } catch {
        hasRun.value = false
    }
}

function startRunProbe() {
    if (runProbeTimer) return
    probeRun()
    runProbeTimer = setInterval(probeRun, RUN_PROBE_MS)
}

function stopRunProbe() {
    if (runProbeTimer) { clearInterval(runProbeTimer); runProbeTimer = null }
}

const WARN_MESSAGES = {
    low_info:  'prompt is too vague — not enough details for the assistant to produce a quality result',
    off_topic: 'prompt topic is not related to coding — the result may be unpredictable',
    gibberish: 'prompt was not recognized as a meaningful request — the result will be unpredictable',
}
const warnMessage = computed(() => WARN_MESSAGES[warnStatus.value] ?? '')

watch(phase, (val) => { store.setPanePhase(props.paneId, val) }, { immediate: true })

onMounted(() => {
    Promise.all([fetchModels(), fetchConfig()])
    startRunProbe()
})
onUnmounted(() => {
    stopRunProbe()
    clearTimeout(generateBtnTimer)
    clearTimeout(pathCopyTimer)
    store.setPanePhase(props.paneId, null)
})

// ── init ──────────────────────────────────────────────
async function fetchModels() {
    modelsLoading.value = true
    modelsFailed.value  = false
    try {
        models.value = await getModels()
        if (models.value.length && !selectedModel.value) selectedModel.value = models.value[0]
    } catch (e) {
        modelsFailed.value = true
        nStore.push('error', String(e), 'Failed to load models')
    } finally {
        modelsLoading.value = false
    }
}

async function fetchConfig() {
    try {
        modes.value = await aiApi.getModes()
        selectedMode.value = modes.value[0]?.key ?? 'plan'
    } catch {
        modes.value = [
            { key: 'plan',     label: 'Auto Plan',    description: 'AI breaks your task into small verifiable steps and runs them one by one' },
            { key: 'direct',   label: 'Direct',       description: 'Your prompt is sent as-is (translated to English), no AI processing' },
            { key: 'optimize', label: 'Rewrite',      description: 'AI rewrites your prompt for clarity and precision, keeping every detail' },
            { key: 'manual',   label: 'Manual Plan',  description: 'Write the steps yourself — they are translated and sent one by one' },
        ]
    }
}

// ── actions ───────────────────────────────────────────
async function onGenerate() {
    if (!canGenerate.value) return

    if (selectedMode.value === 'manual') {
        const steps = manualSteps.value.map(s => s.trim()).filter(Boolean)
        await doRun({ mode: 'manual', model: selectedModel.value, steps })
        return
    }

    originalPrompt.value = input.value.trim()

    if (selectedMode.value !== 'direct') {
        phase.value = 'validating'
        try {
            const { status } = await aiApi.validate({
                prompt: originalPrompt.value,
                mode:   selectedMode.value,
                model:  selectedModel.value,
            })
            if (status !== 'ok') {
                warnStatus.value = status
                phase.value = 'warning'
                return
            }
        } catch {
            // fail open — не блокируем при ошибке валидации
        }
    }

    await proceed()
}

async function proceed() {
    if (selectedMode.value === 'direct') {
        await doRun({ mode: 'direct', model: selectedModel.value, content: originalPrompt.value })
        return
    }
    if (selectedMode.value === 'optimize') {
        await doGenerate([])
        return
    }
    await doAskNextQuestion([])
}

function onWarnContinue() {
    warnStatus.value = null
    proceed()
}

function onWarnCancel() {
    phase.value      = 'idle'
    warnStatus.value = null
}

async function doAskNextQuestion(history) {
    phase.value = 'questioning'
    try {
        const result = await aiApi.getQuestions({
            prompt:  originalPrompt.value,
            mode:    selectedMode.value,
            model:   selectedModel.value,
            history: history,
        })
        if (result.question) {
            currentQuestion.value = result.question
            phase.value = 'clarifying'
        } else {
            await doGenerate(history)
        }
    } catch {
        await doGenerate(history)
    }
}

function onClarifyNext(answer) {
    const history = [...clarifyHistory.value]
    history.push({ question: currentQuestion.value.text, answer: answer || '' })
    clarifyHistory.value = history
    doAskNextQuestion(history)
}

async function doGenerate(history = []) {
    phase.value = 'generating'
    const answers = history.map(h => `${h.question}: ${h.answer}`)
    try {
        const result = await aiApi.generate({
            prompt:  originalPrompt.value,
            mode:    selectedMode.value,
            model:   selectedModel.value,
            answers: answers.length ? answers : undefined,
        })
        reviewData.value = result
        phase.value = 'review'
    } catch (e) {
        nStore.push('error', String(e), 'Generation failed')
        phase.value = 'idle'
    }
}

async function onRegenerate() {
    await doGenerate(clarifyHistory.value)
}

async function onRun() {
    const d = reviewData.value
    const payload = d.mode === 'plan'
        ? { mode: 'plan',  model: selectedModel.value, steps:   d.steps  }
        : { mode: d.mode,  model: selectedModel.value, content: d.result }
    await doRun(payload)
}

async function doRun(payload) {
    const prev = phase.value
    phase.value = 'running'
    try {
        await aiApi.run({ ...payload, pane_id: props.paneId })
        phase.value        = 'idle'
        input.value        = ''
        manualSteps.value  = []
        reviewData.value   = null
        hasRun.value       = true
        probeRun()
    } catch (e) {
        nStore.push('error', String(e), 'Run failed')
        phase.value = prev
    }
}

function onBack() {
    phase.value           = 'idle'
    reviewData.value      = null
    currentQuestion.value = null
    clarifyHistory.value  = []
    warnStatus.value      = null
}
</script>

<template>
    <div class="pw">

        <!-- active run monitor (preempts idle prompt input) -->
        <RunMonitor
            v-if="isIdle && hasRun"
            :pane-id="props.paneId"
            @gone="hasRun = false"
        />

        <!-- idle: toolbar + prompt input -->
        <template v-else-if="isIdle">
            <TopBar :title="idleTitle">
                <div class="pw-ctrl">
                    <span class="pw-ctrl-label">mode</span>
                    <ModeSelect v-if="modes.length" v-model="selectedMode" :modes="modes" />
                </div>
                <div class="pw-ctrl">
                    <span class="pw-ctrl-label">model</span>
                    <ModelSelect v-if="models.length" v-model="selectedModel" :options="models" />
                    <button v-else-if="modelsFailed" class="pw-model-err" @click="fetchModels">
                        unavailable
                        <RefreshCw :size="14" :stroke-width="1.5" />
                    </button>
                    <span v-else class="pw-ctrl-dim">{{ modelsLoading ? 'loading…' : 'no models' }}</span>
                </div>
            </TopBar>

            <!-- manual: PlanReview with built-in caret run button -->
            <PlanReview v-if="selectedMode === 'manual'" v-model:steps="manualSteps" @run="onGenerate" />

            <!-- text modes: textarea with caret-following button -->
            <div v-else class="pw-input-wrap">
                <textarea
                    v-model="input"
                    class="pw-textarea"
                    placeholder="Enter prompt…"
                    spellcheck="false"
                    @input="e => measureCaretPos(e.target)"
                    @click="e => measureCaretPos(e.target)"
                    @keyup="e => measureCaretPos(e.target)"
                    @focus="e => measureCaretPos(e.target)"
                />
                <Transition name="caret-btn">
                    <button
                        v-if="input.trim() && generateBtnPos"
                        class="btn btn--accent pw-caret-btn"
                        :class="{ 'pw-caret-btn--moving': !generateBtnReady }"
                        :style="generateBtnPos"
                        :disabled="!canGenerate"
                        @mousedown.prevent
                        @click="onGenerate"
                    >
                        <component :is="generateIcon" :size="14" :stroke-width="1.5" />
                        {{ generateLabel }}
                    </button>
                </Transition>
            </div>
        </template>

        <!-- loading -->
        <template v-else-if="isLoading">
            <TopBar :title="loadingLabel" :rainbow="true" />
            <div class="pw-loading" />
        </template>

        <!-- validation warning -->
        <template v-else-if="isWarning">
            <TopBar title="warning">
                <button class="btn btn--ghost" @click="onWarnCancel">
                    <ChevronLeft :size="14" :stroke-width="1.5" />
                    cancel
                </button>
                <div v-if="models.length" class="pw-ctrl">
                    <span class="pw-ctrl-label">model</span>
                    <ModelSelect v-model="selectedModel" :options="models" />
                </div>
            </TopBar>
            <div class="pw-warn-body">
                <TriangleAlert :size="22" :stroke-width="1.5" class="pw-warn-icon" />
                <p class="pw-warn-text">{{ warnMessage }}</p>
                <button class="btn btn--warn" @click="onWarnContinue">
                    <component :is="generateIcon" :size="14" :stroke-width="1.5" />
                    {{ generateLabel }} anyway
                </button>
            </div>
        </template>

        <!-- clarifying questions -->
        <ClarifyQuestions
            v-else-if="isClarifying"
            :question="currentQuestion"
            v-model:model="selectedModel"
            :models="models"
            @next="onClarifyNext"
            @back="onBack"
        />

        <!-- plan review -->
        <template v-else-if="isReview && reviewData.mode === 'plan'">
            <TopBar title="plan">
                <button class="btn btn--ghost" @click="onBack">
                    <ChevronLeft :size="14" :stroke-width="1.5" />
                    cancel
                </button>
                <div v-if="models.length" class="pw-ctrl">
                    <span class="pw-ctrl-label">model</span>
                    <ModelSelect v-model="selectedModel" :options="models" />
                </div>
            </TopBar>
            <PlanReview
                v-model:steps="reviewData.steps"
                :show-regenerate="true"
                @run="onRun"
                @regenerate="onRegenerate"
            />
        </template>

        <!-- optimize review -->
        <template v-else-if="isReview && reviewData.mode === 'optimize'">
            <TopBar title="optimized prompt">
                <button class="btn btn--ghost" @click="onBack">
                    <ChevronLeft :size="14" :stroke-width="1.5" />
                    cancel
                </button>
                <div v-if="models.length" class="pw-ctrl">
                    <span class="pw-ctrl-label">model</span>
                    <ModelSelect v-model="selectedModel" :options="models" />
                </div>
            </TopBar>
            <div class="pw-prompt-area">
                <textarea
                    v-model="reviewData.result"
                    class="pw-textarea"
                    spellcheck="false"
                />
                <div class="pw-opt-actions">
                    <button class="btn btn--warn" @click="onRegenerate">
                        <RefreshCw :size="14" :stroke-width="1.5" />
                        regenerate
                    </button>
                    <button class="btn btn--accent" @click="onRun">
                        <Play :size="14" :stroke-width="1.5" />
                        run
                    </button>
                </div>
            </div>
        </template>

        <!-- path bar -->
        <div class="pw-path">
            <Folder :size="14" :stroke-width="1.5" class="pw-path-icon" />
            <span
                class="pw-path-text"
                :class="{ 'is-copied': pathCopied }"
                :title="pane?.path"
                @click="copyPath"
            >{{ fmtPath(pane?.path ?? '') }}</span>
            <span class="pw-pane-id">{{ props.paneId }}</span>
        </div>

    </div>
</template>

<style scoped>
.pw {
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100%;
    font-family: var(--font-mono);
    font-size: var(--size-base);
}

/* ── optimize actions (below textarea, inside pw-prompt-area) ── */
.pw-opt-actions {
    display: flex;
    gap: 8px;
    flex-shrink: 0;
}

/* ── path bar ── */
.pw-path {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    border-top: 1px solid var(--border);
    background: var(--bg-panel);
    flex-shrink: 0;
}
.pw-path-icon { color: var(--text-faint); flex-shrink: 0; }

.pw-path-text {
    flex: 1;
    color: var(--text-secondary);
    font-size: var(--size-sm);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    cursor: pointer;
    transition: color 0.15s;
    border-radius: 3px;
}
.pw-path-text:hover {
    color: var(--text-primary);
    text-decoration: underline;
    text-decoration-style: dotted;
    text-decoration-color: var(--text-muted);
    text-underline-offset: 3px;
}

.pw-pane-id { color: var(--text-muted); font-size: var(--size-xs); flex-shrink: 0; }

/* ── idle toolbar controls ── */
.pw-ctrl {
    display: flex;
    align-items: center;
    gap: 7px;
    flex-shrink: 0;
}
.pw-ctrl-label { color: var(--text-faint); font-size: var(--size-sm); letter-spacing: var(--tracking); }
.pw-ctrl-dim   { color: var(--text-muted); font-size: var(--size-sm); }

.pw-model-err {
    display: flex;
    align-items: center;
    gap: 4px;
    background: none;
    border: 1px solid var(--border-dim);
    border-radius: var(--radius);
    color: var(--warn);
    cursor: pointer;
    font-size: var(--size-sm);
    padding: 2px 8px;
}

/* ── caret-following button ── */
.pw-input-wrap {
    flex: 1;
    position: relative;
    display: flex;
    flex-direction: column;
    min-height: 0;
}
.pw-caret-btn {
    position: absolute;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.35);
    transition: top 0.07s ease, left 0.07s ease;
}
.pw-caret-btn--moving { pointer-events: none; }
.caret-btn-enter-active { transition: opacity 0.15s, transform 0.15s; }
.caret-btn-leave-active { transition: opacity 0.1s,  transform 0.1s;  }
.caret-btn-enter-from,
.caret-btn-leave-to     { opacity: 0; transform: scale(0.85); }

/* ── prompt area: scrollable bg, textarea grows with content ── */
.pw-prompt-area {
    flex: 1;
    overflow-y: auto;
    background: var(--bg-input);
    display: flex;
    flex-direction: column;
    padding: 16px;
    scrollbar-width: thin;
}

/* ── textarea (prompt input & optimize result) ── */
.pw-textarea {
    flex: 1;
    resize: none;
    background: var(--bg-input);
    border: none;
    outline: none;
    color: var(--text-primary);
    font-family: var(--font-mono);
    font-size: var(--size-base);
    line-height: 1.6;
    padding: 16px;
    scrollbar-width: thin;
}

/* prompt textarea (inside pw-prompt-area) grows with content */
.pw-prompt-area .pw-textarea {
    flex: none;
    padding: 0;
    field-sizing: content;
    min-height: 1.6em;
    width: 100%;
}
/* prompt textarea (inside pw-input-wrap) fills space for caret tracking */
.pw-input-wrap .pw-textarea {
    flex: 1;
}

.pw-textarea::placeholder { color: var(--text-muted); }

.pw-loading { flex: 1; }


/* ── validation warning ── */
.pw-warn-body {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 14px;
    padding: 24px;
}
.pw-warn-icon {
    color: var(--warn);
}
.pw-warn-text {
    color: var(--text-secondary);
    font-size: var(--size-base);
    line-height: 1.6;
    text-align: center;
    max-width: 360px;
    margin: 0;
}
</style>
