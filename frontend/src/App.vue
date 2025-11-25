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
    <NotificationSystem ref="notificationSystem" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, provide } from 'vue'
import TopNav from './components/TopNav.vue'
import LeftDock from './components/LeftDock.vue'
import RightDrawer from './components/RightDrawer.vue'
import NotificationSystem from './components/NotificationSystem.vue'
import { useCardStore } from './stores/cardStore'
import { storeToRefs } from 'pinia'

const cardStore = useCardStore()
const { selectedCard } = storeToRefs(cardStore)

// Notification system ref
const notificationSystem = ref(null)

// Provide notification methods to all child components
provide('notify', {
  success: (msg, opts) => notificationSystem.value?.success(msg, opts),
  error: (msg, opts) => notificationSystem.value?.error(msg, opts),
  warning: (msg, opts) => notificationSystem.value?.warning(msg, opts),
  info: (msg, opts) => notificationSystem.value?.info(msg, opts)
})

let ws = null
let reconnectAttempts = 0
const maxReconnectAttempts = 10
const baseReconnectDelay = 1000 // 1 second

// Construct WebSocket URL from current location
function getWebSocketUrl() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.hostname
  const port = import.meta.env.VITE_API_PORT || '8000'
  return `${protocol}//${host}:${port}/api/ws`
}

function connectWebSocket() {
  const wsUrl = getWebSocketUrl()
  console.log(`[WebSocket] Connecting to ${wsUrl}`)

  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    console.log('[WebSocket] Connected')
    reconnectAttempts = 0 // Reset on successful connection
  }

  ws.onmessage = (event) => {
    const message = JSON.parse(event.data)
    cardStore.handleWebSocketMessage(message)
  }

  ws.onerror = (error) => {
    console.error('[WebSocket] Error:', error)
  }

  ws.onclose = (event) => {
    console.log(`[WebSocket] Closed (code: ${event.code})`)

    // Attempt reconnection with exponential backoff
    if (reconnectAttempts < maxReconnectAttempts) {
      const delay = baseReconnectDelay * Math.pow(2, reconnectAttempts)
      reconnectAttempts++
      console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttempts}/${maxReconnectAttempts})`)
      setTimeout(connectWebSocket, delay)
    } else {
      console.error('[WebSocket] Max reconnection attempts reached')
    }
  }
}

onMounted(() => {
  // Connect to WebSocket for real-time updates
  connectWebSocket()

  // Load initial data
  cardStore.fetchCards()
  cardStore.fetchAgents()
})

onUnmounted(() => {
  reconnectAttempts = maxReconnectAttempts // Prevent reconnection on unmount
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
  background: transparent;
  color: var(--text-primary);
}

.main-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
  position: relative;
}

.content {
  flex: 1;
  overflow-y: auto;
  padding: 32px 40px;
  animation: fadeIn 0.6s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
