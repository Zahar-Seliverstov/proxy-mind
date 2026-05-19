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
}
</style>
