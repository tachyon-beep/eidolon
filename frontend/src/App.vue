<template>
  <div class="app">
    <TopNav />
    <div class="main-layout">
      <LeftDock />
      <main class="content">
        <router-view />
      </main>
      <RightDrawer v-if="selectedCard" />
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import TopNav from './components/TopNav.vue'
import LeftDock from './components/LeftDock.vue'
import RightDrawer from './components/RightDrawer.vue'
import { useCardStore } from './stores/cardStore'
import { storeToRefs } from 'pinia'

const cardStore = useCardStore()
const { selectedCard } = storeToRefs(cardStore)

let ws = null

onMounted(() => {
  // Connect to WebSocket for real-time updates
  ws = new WebSocket('ws://localhost:8000/api/ws')

  ws.onmessage = (event) => {
    const message = JSON.parse(event.data)
    cardStore.handleWebSocketMessage(message)
  }

  ws.onerror = (error) => {
    console.error('WebSocket error:', error)
  }

  // Load initial data
  cardStore.fetchCards()
  cardStore.fetchAgents()
})

onUnmounted(() => {
  if (ws) {
    ws.close()
  }
})
</script>

<style>
.app {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #0a0a0a;
  color: #e0e0e0;
}

.main-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}
</style>
