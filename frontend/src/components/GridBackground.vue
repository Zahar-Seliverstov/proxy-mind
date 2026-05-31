<script setup>
defineProps({ loading: { type: Boolean, default: false } })
</script>

<template>
    <div class="grid-bg" :class="{ 'grid-bg--loading': loading }" />
</template>

<!-- @property must be unscoped to register as a global custom property -->
<style>
@property --glow-r {
    syntax: '<length>';
    initial-value: 28vh;
    inherits: false;
}
</style>

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

/*
 * Rainbow only through grid lines, only inside the radial zone.
 * mask-composite: intersect (radial ∩ grid) keeps outer static grid intact.
 */
.grid-bg--loading::before {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(to bottom,
        hsl(0,   100%, 60%),
        hsl(51,  100%, 58%),
        hsl(120, 100%, 48%),
        hsl(180, 100%, 48%),
        hsl(240, 100%, 62%),
        hsl(300, 100%, 60%),
        hsl(360, 100%, 60%)
    );
    background-size: 100% 252px; /* 7 × 36px — one full color cycle per 7 grid rows */
    -webkit-mask:
        radial-gradient(circle var(--glow-r) at 50% 50%, black 30%, transparent 70%),
        repeating-linear-gradient(to right,  #000 0 1px, transparent 1px 36px),
        repeating-linear-gradient(to bottom, #000 0 1px, transparent 1px 36px);
    -webkit-mask-composite: source-in, add;
    mask:
        radial-gradient(circle var(--glow-r) at 50% 50%, black 30%, transparent 70%),
        repeating-linear-gradient(to right,  #000 0 1px, transparent 1px 36px),
        repeating-linear-gradient(to bottom, #000 0 1px, transparent 1px 36px);
    mask-composite: intersect, add;
    pointer-events: none;
    animation: flow-down 1.8s linear infinite, zone-pulse 4s ease-in-out infinite;
}

@keyframes flow-down {
    from { background-position: 0 0;      }
    to   { background-position: 0 -252px; }
}

@keyframes zone-pulse {
    0%, 100% { --glow-r: 28vh; }
    50%       { --glow-r: 44vh; }
}
</style>
