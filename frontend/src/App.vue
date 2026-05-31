<script setup>
import MainView from './views/MainView.vue'
</script>

<template>
    <MainView />
</template>

<style>
*, *::before, *::after { box-sizing: border-box; }
button, input, select, textarea { font-family: inherit; font-size: inherit; }

body {
    margin: 0;
    background: var(--bg-app);
    color: var(--text-primary);
    font-family: var(--font-mono);
}

#app {
    width: 100%;
    min-height: 100vh;
    position: relative;
}

/* CRT scanlines */
#app::after {
    content: '';
    position: fixed;
    inset: 0;
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 3px,
        rgba(0, 0, 0, 0.07) 3px,
        rgba(0, 0, 0, 0.07) 4px
    );
    pointer-events: none;
    z-index: var(--z-scanlines);
}

/* Neon scrollbar */
::-webkit-scrollbar { width: 3px; height: 3px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-dim); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.20);
}

::selection {
    background: rgba(255, 255, 255, 0.14);
    color: var(--text-bright);
}
</style>
