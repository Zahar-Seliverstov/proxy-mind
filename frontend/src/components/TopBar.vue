<script setup>
import { computed } from 'vue'

const props = defineProps({
    title:   { type: String,  default: '' },
    rainbow: { type: Boolean, default: false },
})

const RAINBOW = ['#ff4444', '#ff922b', '#ffd43b', '#69db7c', '#4dabf7', '#cc5de8', '#f783ac']

const chars = computed(() => {
    if (!props.rainbow || !props.title) return []
    return props.title.split('').map((ch, i) => ({
        ch,
        color: RAINBOW[i % RAINBOW.length],
        delay: `${(i * 0.12).toFixed(2)}s`,
    }))
})
</script>

<template>
    <div class="bar">
        <slot />
        <div class="bar-center" :class="{ 'bar-center--static': !$slots.center }">
            <slot v-if="$slots.center" name="center" />
            <span v-else-if="rainbow && title" class="rb-title">
                <span
                    v-for="(c, i) in chars"
                    :key="i"
                    class="rb-char"
                    :style="{ '--ch-color': c.color, animationDelay: c.delay }"
                >{{ c.ch }}</span>
            </span>
            <span v-else-if="title">{{ title }}</span>
        </div>
        <div class="bar-spacer" />
        <slot name="end" />
    </div>
</template>

<style scoped>
.bar {
    position: relative;
    container-type: inline-size;
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 7px 14px;
    min-height: 36px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-panel);
    flex-shrink: 0;
}
.bar-center {
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    align-items: center;
    gap: 6px;
    color: var(--text-faint);
    font-size: var(--size-sm);
    letter-spacing: var(--tracking);
    pointer-events: none;
    white-space: nowrap;
}
@container (max-width: 460px) {
    .bar-center--static { display: none; }
}
.bar-spacer { flex: 1; }

.rb-title { display: inline-flex; }

.rb-char {
    display: inline-block;
    color: var(--ch-color);
    animation: rb-pulse 1.4s ease-in-out infinite alternate;
}

@keyframes rb-pulse {
    0%   { color: var(--text-faint); }
    100% { color: var(--ch-color); }
}
</style>
