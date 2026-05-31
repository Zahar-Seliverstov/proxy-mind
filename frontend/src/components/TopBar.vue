<script setup>
defineProps({
    title:   { type: String,  default: '' },
    rainbow: { type: Boolean, default: false },
})
</script>

<template>
    <div class="bar">
        <slot />
        <div class="bar-center" :class="{ 'bar-center--static': !$slots.center, 'bar-center--rainbow': rainbow && !$slots.center }">
            <slot v-if="$slots.center" name="center" />
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

.bar-center--rainbow span {
    background: linear-gradient(90deg,
        #ff6b6b, #ff922b, #ffd43b, #69db7c, #4dabf7, #cc5de8, #f783ac, #ff6b6b
    );
    background-size: 250% auto;
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    color: transparent;
    animation: rainbow-flow 2.4s linear infinite;
}
@keyframes rainbow-flow {
    0%   { background-position: 0% center; }
    100% { background-position: 250% center; }
}
</style>
