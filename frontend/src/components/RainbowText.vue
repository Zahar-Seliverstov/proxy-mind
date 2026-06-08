<script setup>
import { computed, useSlots } from 'vue'

const props = defineProps({

    text: { type: String, default: '' },

    speed: { type: Number, default: 3 },

    fontSize: { type: [Number, String], default: null },
})

const slots = useSlots()

const source = computed(() => {
    if (props.text) return props.text
    const node = slots.default?.()
    return _slotToText(node) ?? ''
})

function _slotToText(nodes) {
    if (!nodes) return ''
    return nodes
        .map(n => (typeof n.children === 'string' ? n.children : ''))
        .join('')
}

const chars = computed(() => Array.from(source.value))

const stagger = computed(() => props.speed * 0.08)

function charStyle(i) {
    return {
        animationDuration: `${props.speed}s`,
        animationDelay: `${-(i * stagger.value)}s`,
    }
}

const rootStyle = computed(() => {
    if (props.fontSize == null) return {}
    const fs = typeof props.fontSize === 'number' ? `${props.fontSize}px` : props.fontSize
    return { fontSize: fs }
})

function isSpace(ch) {
    return ch === ' ' || ch === ' ' || ch === '\t'
}
</script>

<template>
    <span class="rainbow" :style="rootStyle" aria-label="source" role="text">
        <span
            v-for="(ch, i) in chars"
            :key="i"
            class="rainbow__ch"
            :class="{ 'rainbow__ch--space': isSpace(ch) }"
            :style="charStyle(i)"
        >{{ ch }}</span>
    </span>
</template>

<style scoped>
.rainbow {
    display: inline-block;
    white-space: pre-wrap;
    font-family: inherit;
    font-weight: 700;
}

.rainbow__ch {
    display: inline-block;
    white-space: pre;
    animation-name: rainbow-cycle;
    animation-timing-function: linear;
    animation-iteration-count: infinite;
    will-change: color;
}

.rainbow__ch--space {
    animation: none;
}

@keyframes rainbow-cycle {
    0%   { color: #ff0000; }
    16%  { color: #ff8800; }
    33%  { color: #ffee00; }
    50%  { color: #00cc44; }
    66%  { color: #0099ff; }
    83%  { color: #6633ff; }
    100% { color: #ff0000; }
}

@media (prefers-reduced-motion: reduce) {
    .rainbow__ch { animation: none; color: var(--accent, #6633ff); }
}
</style>
