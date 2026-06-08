<script setup>
defineProps({ loading: { type: Boolean, default: false } })
</script>

<template>
    <div class="grid-bg">
        <Transition name="spinner">
            <div v-if="loading" class="grid-spinner" />
        </Transition>
    </div>
</template>

<style scoped>
.grid-bg {
    position: absolute;
    inset: 0;
    background-image:
        linear-gradient(rgba(255, 255, 255, 0.018) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.018) 1px, transparent 1px);
    background-size: 36px 36px;
    pointer-events: none;
    z-index: -1;
    display: flex;
    align-items: center;
    justify-content: center;
}

.grid-spinner {
    width: 32px;
    height: 32px;
    border: 2px solid var(--accent-border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

.spinner-enter-active,
.spinner-leave-active { transition: opacity 0.25s ease; }
.spinner-enter-from,
.spinner-leave-to    { opacity: 0; }
</style>
