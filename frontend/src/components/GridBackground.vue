<template>
    <div class="grid-bg" />
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
}
</style>
