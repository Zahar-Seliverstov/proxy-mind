<script setup>
defineProps({ title: { type: String, default: '' } })
</script>

<template>
    <div class="bar">
        <slot />
        <div class="bar-center">
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
}
.bar-spacer { flex: 1; }
</style>
