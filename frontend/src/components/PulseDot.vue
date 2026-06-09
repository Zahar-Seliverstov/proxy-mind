<script setup>
defineProps({
    active:   { type: Boolean, default: true },
    size:     { type: Number, default: 6 },
    duration: { type: Number, default: 1.4 },
    color:    { type: String, default: 'var(--accent)' },
})
</script>

<template>
    <span
        class="pd"
        :class="{ 'pd--active': active }"
        :style="{
            '--pd-size':     size + 'px',
            '--pd-color':    color,
            '--pd-duration': duration + 's',
        }"
    />
</template>

<style scoped>
.pd {
    display: inline-block;
    width: var(--pd-size);
    height: var(--pd-size);
    border-radius: 50%;
    flex-shrink: 0;
    background: var(--border-dim);
}

.pd--active {
    animation: pd-blink var(--pd-duration) ease-in-out infinite;
}

@keyframes pd-blink {
    0%, 100% { background: var(--border-dim); }
    50%      { background: var(--pd-color); }
}
</style>
