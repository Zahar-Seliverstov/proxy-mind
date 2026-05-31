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
    background: var(--pd-color);
    animation: pd-blink var(--pd-duration) linear infinite;
}

@keyframes pd-blink {
    0%,  40% { opacity: 1; }
    50%, 90% { opacity: 0; }
    100%     { opacity: 1; }
}
</style>
