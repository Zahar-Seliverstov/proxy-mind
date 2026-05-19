<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useSessionsStore } from '../stores/sessions.js'
import { useNotificationsStore } from '../stores/notifications.js'
import { getModels } from '../api/ollama.js'
import * as aiApi from '../api/ai.js'
import { fmtPath } from '../utils.js'
import ModelSelect from './ModelSelect.vue'
import ModeSelect from './ModeSelect.vue'
import PlanReview from './PlanReview.vue'
import ClarifyQuestions from './ClarifyQuestions.vue'
import RunMonitor from './RunMonitor.vue'
import TopBar from './TopBar.vue'

const store  = useSessionsStore()
const nStore = useNotificationsStore()

// ── models ────────────────────────────────────────────
const models        = ref([])
const selectedModel = ref('')
const modelsLoading = ref(false)
const modelsFailed  = ref(false)

// ── modes ─────────────────────────────────────────────
const modes        = ref([])
const selectedMode = ref('plan')

// ── input & workflow ──────────────────────────────────
const input           = ref('')
const manualSteps     = ref([])
const originalPrompt  = ref('')
const phase           = ref('idle')   // 'idle' | 'validating' | 'warning' | 'questioning' | 'clarifying' | 'generating' | 'review' | 'running'
const reviewData      = ref(null)     // { mode: 'plan', steps: [] } | { mode: 'optimize', result: '' }
const currentQuestion = ref(null)    // { text, options } | null
const clarifyHistory  = ref([])      // [{ question, answer }]
const warnStatus      = ref(null)    // 'low_info' | 'off_topic' | 'gibberish'

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
const generateIcon  = computed(() => isDirectLike.value ? 'play_arrow' : 'auto_awesome')
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
const RUN_PROBE_MS = 2000

async function probeRun() {
    const id = store.selectedPane?.id
    if (!id) { hasRun.value = false; return }
    try {
        const data = await aiApi.getRun(id)
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

watch(() => store.selectedPane?.id, () => { hasRun.value = false; probeRun() })

const WARN_MESSAGES = {
    low_info:  'prompt is too vague — not enough details for the assistant to produce a quality result',
    off_topic: 'prompt topic is not related to coding — the result may be unpredictable',
    gibberish: 'prompt was not recognized as a meaningful request — the result will be unpredictable',
}
const warnMessage = computed(() => WARN_MESSAGES[warnStatus.value] ?? '')

onMounted(() => {
    Promise.all([fetchModels(), fetchConfig()])
    startRunProbe()
})
onUnmounted(stopRunProbe)

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
    if (answer) history.push({ question: currentQuestion.value.text, answer })
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
    const paneId = store.selectedPane?.id
    if (!paneId) {
        nStore.push('error', 'no pane selected', 'Run failed')
        return
    }
    const prev = phase.value
    phase.value = 'running'
    try {
        await aiApi.run({ ...payload, pane_id: paneId })
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
            v-if="isIdle && hasRun && store.selectedPane"
            :pane-id="store.selectedPane.id"
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
                    <button v-else-if="modelsFailed" class="pw-warn" @click="fetchModels">
                        unavailable
                        <span class="material-symbols-outlined">refresh</span>
                    </button>
                    <span v-else class="pw-ctrl-dim">{{ modelsLoading ? 'loading…' : 'no models' }}</span>
                </div>
                <template #end>
                    <button class="btn btn--accent" :disabled="!canGenerate" @click="onGenerate">
                        <span class="material-symbols-outlined">{{ generateIcon }}</span>
                        {{ generateLabel }}
                    </button>
                </template>
            </TopBar>
            <PlanReview v-if="selectedMode === 'manual'" v-model:steps="manualSteps" />
            <textarea v-else v-model="input" class="pw-textarea" placeholder="Enter prompt…" spellcheck="false" />
        </template>

        <!-- loading -->
        <template v-else-if="isLoading">
            <TopBar>
                <template #center>
                    <span class="pw-pulse">
                        <span class="pw-pulse-ring" />
                    </span>
                    {{ loadingLabel }}
                </template>
            </TopBar>
            <div class="pw-loading" />
        </template>

        <!-- validation warning -->
        <template v-else-if="isWarning">
            <TopBar title="warning">
                <button class="btn btn--ghost" @click="onWarnCancel">
                    <span class="material-symbols-outlined">keyboard_arrow_left</span>
                    cancel
                </button>
                <template #end>
                    <button class="btn btn--accent" @click="onWarnContinue">
                        <span class="material-symbols-outlined">{{ generateIcon }}</span>
                        {{ generateLabel }} anyway
                    </button>
                </template>
            </TopBar>
            <div class="pw-warn-body">
                <span class="material-symbols-outlined pw-warn-icon">warning</span>
                <p class="pw-warn-text">{{ warnMessage }}</p>
            </div>
        </template>

        <!-- clarifying questions -->
        <ClarifyQuestions
            v-else-if="isClarifying"
            :question="currentQuestion"
            @next="onClarifyNext"
            @back="onBack"
        />

        <!-- plan review -->
        <template v-else-if="isReview && reviewData.mode === 'plan'">
            <TopBar title="plan">
                <button class="btn btn--ghost" @click="onBack">
                    <span class="material-symbols-outlined">keyboard_arrow_left</span>
                    cancel
                </button>
                <template #end>
                    <button class="btn btn--ghost" @click="onRegenerate">
                        <span class="material-symbols-outlined">refresh</span>
                        regenerate
                    </button>
                    <button class="btn btn--accent" :disabled="!reviewData.steps.length" @click="onRun">
                        <span class="material-symbols-outlined">play_arrow</span>
                        run
                    </button>
                </template>
            </TopBar>
            <PlanReview v-model:steps="reviewData.steps" />
        </template>

        <!-- optimize review -->
        <template v-else-if="isReview && reviewData.mode === 'optimize'">
            <TopBar title="optimized prompt">
                <button class="btn btn--ghost" @click="onBack">
                    <span class="material-symbols-outlined">keyboard_arrow_left</span>
                    cancel
                </button>
                <template #end>
                    <button class="btn btn--ghost" @click="onRegenerate">
                        <span class="material-symbols-outlined">refresh</span>
                        regenerate
                    </button>
                    <button class="btn btn--accent" @click="onRun">
                        <span class="material-symbols-outlined">play_arrow</span>
                        run
                    </button>
                </template>
            </TopBar>
            <textarea v-model="reviewData.result" class="pw-textarea" spellcheck="false" />
        </template>

        <!-- path bar -->
        <div class="pw-path">
            <span class="material-symbols-outlined pw-path-icon">folder</span>
            <span class="pw-path-text" :title="store.selectedPane.path">{{ fmtPath(store.selectedPane.path) }}</span>
            <span class="pw-pane-id">{{ store.selectedPane.id }}</span>
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
.pw-path-icon { font-size: var(--size-icon); color: var(--text-faint); flex-shrink: 0; }
.pw-path-text {
    flex: 1;
    color: var(--text-secondary);
    font-size: var(--size-sm);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
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

.pw-warn {
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
.pw-warn .material-symbols-outlined { font-size: var(--size-icon); line-height: 1; }

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
.pw-textarea::placeholder { color: var(--text-muted); }

/* ── loading ── */
.pw-loading { flex: 1; }

.pw-pulse {
    position: relative;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--accent);
    flex-shrink: 0;
}
.pw-pulse-ring {
    position: absolute;
    inset: 0;
    border-radius: 50%;
    border: 1px solid var(--accent);
    animation: ring-expand 2s ease-out infinite;
}

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
    font-size: 22px;
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
