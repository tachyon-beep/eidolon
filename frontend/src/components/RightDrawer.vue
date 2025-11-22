<template>
  <aside class="right-drawer">
    <div class="drawer-header">
      <h2>{{ card.title }}</h2>
      <button class="close-btn" @click="closeDrawer">✕</button>
    </div>

    <div class="drawer-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="drawer-tab"
        :class="{ active: activeTab === tab.id }"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>

    <div class="drawer-content">
      <!-- Details Tab -->
      <div v-if="activeTab === 'details'" class="tab-panel">
        <div class="detail-section">
          <label>ID</label>
          <div class="detail-value mono">{{ card.id }}</div>
        </div>

        <div class="detail-section">
          <label>Type</label>
          <div class="detail-value">{{ card.type }}</div>
        </div>

        <div class="detail-section">
          <label>Status</label>
          <div class="detail-value">{{ card.status }}</div>
        </div>

        <div class="detail-section">
          <label>Priority</label>
          <div class="detail-value">{{ card.priority }}</div>
        </div>

        <div class="detail-section" v-if="card.owner_agent">
          <label>Owner Agent</label>
          <div class="detail-value">
            <button class="agent-link" @click="openAgent(card.owner_agent)">
              {{ card.owner_agent }}
            </button>
          </div>
        </div>

        <div class="detail-section">
          <label>Summary</label>
          <div class="detail-value markdown" v-html="renderMarkdown(card.summary)"></div>
        </div>
      </div>

      <!-- Links Tab -->
      <div v-if="activeTab === 'links'" class="tab-panel">
        <div v-if="card.links.code.length > 0" class="link-section">
          <h3>Code References</h3>
          <div v-for="link in card.links.code" :key="link" class="link-item mono">
            {{ link }}
          </div>
        </div>

        <div v-if="card.links.tests.length > 0" class="link-section">
          <h3>Tests</h3>
          <div v-for="link in card.links.tests" :key="link" class="link-item mono">
            {{ link }}
          </div>
        </div>
      </div>

      <!-- Log Tab -->
      <div v-if="activeTab === 'log'" class="tab-panel">
        <div class="log-entries">
          <div v-for="(entry, idx) in card.log" :key="idx" class="log-entry">
            <div class="log-header">
              <span class="log-actor">{{ entry.actor }}</span>
              <span class="log-time">{{ formatTime(entry.timestamp) }}</span>
            </div>
            <div class="log-event">{{ entry.event }}</div>
          </div>
        </div>
      </div>

      <!-- Agent Snoop Tab (if owner_agent exists) -->
      <div v-if="activeTab === 'snoop' && agentData" class="tab-panel">
        <AgentSnoop :agent="agentData" />
      </div>
    </div>

    <div class="drawer-actions">
      <button class="action-btn" @click="routeCard">
        Route Card
      </button>
      <button class="action-btn secondary" @click="updateStatus">
        Update Status
      </button>
    </div>
  </aside>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useCardStore } from '../stores/cardStore'
import { storeToRefs } from 'pinia'
import AgentSnoop from './AgentSnoop.vue'

const cardStore = useCardStore()
const { selectedCard, selectedAgent } = storeToRefs(cardStore)

const card = computed(() => selectedCard.value)
const agentData = computed(() => selectedAgent.value)

const activeTab = ref('details')

const tabs = computed(() => {
  const baseTabs = [
    { id: 'details', label: 'Details' },
    { id: 'links', label: 'Links' },
    { id: 'log', label: 'Log' }
  ]

  if (card.value?.owner_agent) {
    baseTabs.push({ id: 'snoop', label: 'Agent Snoop' })
  }

  return baseTabs
})

// Watch for owner_agent changes and load agent data
watch(() => card.value?.owner_agent, async (ownerAgent) => {
  if (ownerAgent && activeTab.value === 'snoop') {
    await cardStore.getAgent(ownerAgent)
  }
})

// Load agent when switching to snoop tab
watch(activeTab, async (newTab) => {
  if (newTab === 'snoop' && card.value?.owner_agent) {
    await cardStore.getAgent(card.value.owner_agent)
  }
})

const closeDrawer = () => {
  cardStore.clearSelection()
}

const openAgent = async (agentId) => {
  activeTab.value = 'snoop'
  await cardStore.getAgent(agentId)
}

const routeCard = () => {
  // Simple routing to Code tab for demo
  cardStore.routeCard(card.value.id, 'Explore', 'Code')
}

const updateStatus = () => {
  // Cycle through statuses for demo
  const statuses = ['New', 'Queued', 'In-Analysis', 'Proposed', 'Approved']
  const currentIndex = statuses.indexOf(card.value.status)
  const nextStatus = statuses[(currentIndex + 1) % statuses.length]

  cardStore.updateCard(card.value.id, { status: nextStatus })
}

const renderMarkdown = (text) => {
  // Simple markdown rendering (replace with proper library in production)
  return text
    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
    .replace(/^## (.*$)/gim, '<h2>$1</h2>')
    .replace(/^# (.*$)/gim, '<h1>$1</h1>')
    .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
    .replace(/\*(.*)\*/gim, '<em>$1</em>')
    .replace(/```(\w+)?\n([\s\S]*?)```/gim, '<pre><code>$2</code></pre>')
    .replace(/`([^`]+)`/gim, '<code>$1</code>')
    .replace(/\n/gim, '<br>')
}

const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  return date.toLocaleString()
}
</script>

<style scoped>
.right-drawer {
  width: 400px;
  background: #0d0d0d;
  border-left: 1px solid #222;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.drawer-header {
  padding: 20px;
  border-bottom: 1px solid #222;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.drawer-header h2 {
  font-size: 16px;
  font-weight: 600;
  color: #e0e0e0;
  margin: 0;
  flex: 1;
  line-height: 1.4;
}

.close-btn {
  background: none;
  border: none;
  color: #666;
  font-size: 20px;
  cursor: pointer;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
}

.close-btn:hover {
  background: #1a1a1a;
  color: #ccc;
}

.drawer-tabs {
  display: flex;
  gap: 4px;
  padding: 12px 20px;
  border-bottom: 1px solid #222;
}

.drawer-tab {
  padding: 6px 12px;
  background: none;
  border: none;
  color: #888;
  font-size: 13px;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
}

.drawer-tab:hover {
  background: #1a1a1a;
  color: #ccc;
}

.drawer-tab.active {
  background: #00d4aa;
  color: #000;
  font-weight: 500;
}

.drawer-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.tab-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.detail-section label {
  font-size: 11px;
  font-weight: 600;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.detail-value {
  font-size: 14px;
  color: #e0e0e0;
  line-height: 1.6;
}

.detail-value.mono {
  font-family: monospace;
  font-size: 12px;
}

.detail-value.markdown {
  line-height: 1.8;
}

.agent-link {
  background: #0a2a2a;
  color: #00d4aa;
  border: 1px solid #00d4aa;
  padding: 6px 12px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.agent-link:hover {
  background: #00d4aa;
  color: #000;
}

.link-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.link-section h3 {
  font-size: 12px;
  font-weight: 600;
  color: #888;
  margin: 0;
}

.link-item {
  padding: 8px 12px;
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 4px;
  font-size: 12px;
  color: #00d4aa;
}

.log-entries {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.log-entry {
  padding: 12px;
  background: #1a1a1a;
  border-left: 2px solid #00d4aa;
  border-radius: 4px;
}

.log-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
}

.log-actor {
  font-size: 11px;
  font-weight: 600;
  color: #00d4aa;
}

.log-time {
  font-size: 10px;
  color: #666;
}

.log-event {
  font-size: 13px;
  color: #ccc;
}

.drawer-actions {
  padding: 16px 20px;
  border-top: 1px solid #222;
  display: flex;
  gap: 8px;
}

.action-btn {
  flex: 1;
  padding: 10px 16px;
  background: #00d4aa;
  color: #000;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:hover {
  background: #00ffcc;
  transform: translateY(-1px);
}

.action-btn.secondary {
  background: #2a2a2a;
  color: #ccc;
}

.action-btn.secondary:hover {
  background: #3a3a3a;
}
</style>
