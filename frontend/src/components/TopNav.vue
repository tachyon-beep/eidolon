<template>
  <nav class="top-nav">
    <div class="logo">
      <h1>MONAD</h1>
      <span class="tagline">Recursive unity made manifest</span>
    </div>
    <div class="tabs">
      <router-link
        v-for="tab in tabs"
        :key="tab.path"
        :to="tab.path"
        class="tab"
        :class="{ active: isActive(tab.path) }"
      >
        {{ tab.name }}
      </router-link>
    </div>
  </nav>
</template>

<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()

const tabs = [
  { name: 'Explore', path: '/explore' },
  { name: 'Code', path: '/code' },
  { name: 'Plan', path: '/plan' }
]

const isActive = (path) => {
  return route.path === path
}
</script>

<style scoped>
.top-nav {
  background: #111;
  border-bottom: 1px solid #333;
  padding: 12px 24px;
  display: flex;
  align-items: center;
  gap: 40px;
}

.logo {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.logo h1 {
  font-size: 20px;
  font-weight: 600;
  color: #00d4aa;
  letter-spacing: 2px;
}

.tagline {
  font-size: 11px;
  color: #666;
  font-style: italic;
}

.tabs {
  display: flex;
  gap: 8px;
}

.tab {
  padding: 8px 16px;
  color: #888;
  text-decoration: none;
  border-radius: 4px;
  transition: all 0.2s;
  font-size: 14px;
  font-weight: 500;
}

.tab:hover {
  background: #1a1a1a;
  color: #ccc;
}

.tab.active {
  background: #00d4aa;
  color: #000;
}
</style>
