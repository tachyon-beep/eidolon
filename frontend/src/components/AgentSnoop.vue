<template>
  <div class="agent-snoop">
    <div class="agent-header">
      <div class="agent-info">
        <span class="agent-scope" :class="`scope-${agent.scope.toLowerCase()}`">
          {{ agent.scope }}
        </span>
        <span class="agent-target">{{ agent.target }}</span>
      </div>
      <div class="agent-status" :class="`status-${agent.status.toLowerCase()}`">
        {{ agent.status }}
      </div>
    </div>

    <div class="agent-metrics">
      <div class="metric-item">
        <span class="metric-label">Total Tokens</span>
        <span class="metric-value">{{ agent.total_tokens.toLocaleString() }}</span>
      </div>
      <div class="metric-item">
        <span class="metric-label">Messages</span>
        <span class="metric-value">{{ agent.messages.length }}</span>
      </div>
      <div class="metric-item">
        <span class="metric-label">Findings</span>
        <span class="metric-value">{{ agent.findings.length }}</span>
      </div>
      <div class="metric-item">
        <span class="metric-label">Cards Created</span>
        <span class="metric-value">{{ agent.cards_created.length }}</span>
      </div>
    </div>

    <div class="snoop-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="snoop-tab"
        :class="{ active: activeTab === tab.id }"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- Messages Tab -->
    <div v-if="activeTab === 'messages'" class="snoop-panel">
      <div class="messages-list">
        <div
          v-for="(msg, idx) in agent.messages"
          :key="idx"
          class="message-item"
          :class="`role-${msg.role}`"
        >
          <div class="message-header">
            <span class="message-role">{{ msg.role }}</span>
            <div class="message-meta">
              <span v-if="msg.tokens_in > 0" class="token-count">
                ↓{{ msg.tokens_in }}
              </span>
              <span v-if="msg.tokens_out > 0" class="token-count">
                ↑{{ msg.tokens_out }}
              </span>
              <span v-if="msg.latency_ms > 0" class="latency">
                {{ msg.latency_ms.toFixed(0) }}ms
              </span>
            </div>
          </div>
          <div class="message-content">{{ msg.content }}</div>
          <div v-if="msg.tool_calls.length > 0" class="tool-calls">
            <span class="tool-label">Tools:</span>
            {{ msg.tool_calls.join(', ') }}
          </div>
        </div>
      </div>
    </div>

    <!-- Findings Tab -->
    <div v-if="activeTab === 'findings'" class="snoop-panel">
      <div class="findings-list">
        <div v-for="(finding, idx) in agent.findings" :key="idx" class="finding-item">
          {{ finding }}
        </div>
      </div>
    </div>

    <!-- Snapshots Tab -->
    <div v-if="activeTab === 'snapshots'" class="snoop-panel">
      <div class="snapshots-list">
        <div v-for="(snapshot, idx) in agent.snapshots" :key="idx" class="snapshot-item">
          <div class="snapshot-header">
            <span class="snapshot-type">{{ snapshot.type }}</span>
            <span class="snapshot-time">{{ formatTime(snapshot.timestamp) }}</span>
          </div>
          <pre class="snapshot-data">{{ JSON.stringify(snapshot.data, null, 2) }}</pre>
        </div>
      </div>
    </div>

    <!-- Graph Tab -->
    <div v-if="activeTab === 'graph'" class="snoop-panel">
      <div class="agent-graph">
        <div v-if="agent.parent_id" class="graph-section">
          <h4>Parent</h4>
          <div class="graph-node">{{ agent.parent_id }}</div>
        </div>

        <div v-if="agent.children_ids.length > 0" class="graph-section">
          <h4>Children ({{ agent.children_ids.length }})</h4>
          <div class="graph-nodes">
            <div v-for="childId in agent.children_ids" :key="childId" class="graph-node">
              {{ childId }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  agent: {
    type: Object,
    required: true
  }
})

const activeTab = ref('messages')

const tabs = [
  { id: 'messages', label: 'Messages' },
  { id: 'findings', label: 'Findings' },
  { id: 'snapshots', label: 'Snapshots' },
  { id: 'graph', label: 'Graph' }
]

const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString()
}
</script>

<style scoped>
.agent-snoop {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.agent-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 12px;
  background: #1a1a1a;
  border-radius: 6px;
}

.agent-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.agent-scope {
  font-size: 10px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  width: fit-content;
}

.scope-system {
  background: #2a1a1a;
  color: #e55d5d;
}

.scope-module {
  background: #1a2a2a;
  color: #5d9de5;
}

.scope-function {
  background: #1a2a1a;
  color: #5de585;
}

.agent-target {
  font-size: 12px;
  font-family: monospace;
  color: #ccc;
}

.agent-status {
  font-size: 11px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 4px;
}

.status-analyzing {
  background: #2a2a1a;
  color: #e5d55d;
}

.status-completed {
  background: #1a2a1a;
  color: #5de585;
}

.agent-metrics {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.metric-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px;
  background: #1a1a1a;
  border-radius: 4px;
}

.metric-label {
  font-size: 10px;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.metric-value {
  font-size: 16px;
  font-weight: 600;
  color: #00d4aa;
}

.snoop-tabs {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid #2a2a2a;
}

.snoop-tab {
  padding: 8px 12px;
  background: none;
  border: none;
  color: #888;
  font-size: 12px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.snoop-tab:hover {
  color: #ccc;
}

.snoop-tab.active {
  color: #00d4aa;
  border-bottom-color: #00d4aa;
}

.snoop-panel {
  max-height: 400px;
  overflow-y: auto;
}

.messages-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message-item {
  padding: 12px;
  background: #1a1a1a;
  border-radius: 6px;
  border-left: 3px solid #2a2a2a;
}

.message-item.role-user {
  border-left-color: #5d9de5;
}

.message-item.role-assistant {
  border-left-color: #00d4aa;
}

.message-item.role-system {
  border-left-color: #888;
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.message-role {
  font-size: 10px;
  font-weight: 600;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.message-meta {
  display: flex;
  gap: 8px;
  font-size: 10px;
  color: #666;
}

.token-count,
.latency {
  font-family: monospace;
}

.message-content {
  font-size: 12px;
  line-height: 1.6;
  color: #ccc;
  white-space: pre-wrap;
  word-break: break-word;
}

.tool-calls {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #2a2a2a;
  font-size: 11px;
  color: #888;
}

.tool-label {
  font-weight: 600;
}

.findings-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.finding-item {
  padding: 10px 12px;
  background: #1a1a1a;
  border-left: 3px solid #00d4aa;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.6;
  color: #ccc;
}

.snapshots-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.snapshot-item {
  background: #1a1a1a;
  border-radius: 6px;
  overflow: hidden;
}

.snapshot-header {
  padding: 10px 12px;
  background: #222;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.snapshot-type {
  font-size: 11px;
  font-weight: 600;
  color: #00d4aa;
  text-transform: uppercase;
}

.snapshot-time {
  font-size: 10px;
  color: #666;
}

.snapshot-data {
  padding: 12px;
  margin: 0;
  font-size: 11px;
  color: #ccc;
  overflow-x: auto;
}

.agent-graph {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.graph-section h4 {
  font-size: 11px;
  font-weight: 600;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.graph-nodes {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.graph-node {
  padding: 8px 12px;
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 4px;
  font-size: 11px;
  font-family: monospace;
  color: #00d4aa;
}
</style>
