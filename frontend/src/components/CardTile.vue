<template>
  <div
    class="card-tile"
    :class="[`type-${card.type.toLowerCase()}`, `status-${card.status.toLowerCase()}`]"
    draggable="true"
    @dragstart="handleDragStart"
    @click="handleClick"
  >
    <div class="card-header">
      <span class="card-type">{{ card.type }}</span>
      <span class="card-priority" :class="`priority-${card.priority.toLowerCase()}`">
        {{ card.priority }}
      </span>
    </div>

    <h3 class="card-title">{{ card.title }}</h3>

    <div class="card-meta">
      <span class="card-id">{{ card.id }}</span>
      <span class="card-status">{{ statusIcon }} {{ card.status }}</span>
    </div>

    <div v-if="card.owner_agent" class="card-owner">
      <span class="agent-badge">{{ card.owner_agent }}</span>
    </div>

    <div v-if="card.metrics" class="card-metrics">
      <div class="metric" v-if="card.metrics.confidence > 0">
        <span class="metric-label">Confidence:</span>
        <div class="metric-bar">
          <div class="metric-fill" :style="{ width: `${card.metrics.confidence * 100}%` }"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useCardStore } from '../stores/cardStore'
import { useRoute } from 'vue-router'

const props = defineProps({
  card: {
    type: Object,
    required: true
  }
})

const cardStore = useCardStore()
const route = useRoute()

const statusIcon = computed(() => {
  const icons = {
    'New': '○',
    'Queued': '◔',
    'In-Analysis': '◑',
    'Proposed': '◕',
    'In-Review': '◑',
    'Approved': '●',
    'Blocked': '⨯',
    'Done': '✓'
  }
  return icons[props.card.status] || '○'
})

const handleDragStart = (event) => {
  event.dataTransfer.setData('cardId', props.card.id)
  event.dataTransfer.setData('fromTab', route.name)
}

const handleClick = () => {
  cardStore.selectCard(props.card)
}
</script>

<style scoped>
.card-tile {
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
}

.card-tile:hover {
  border-color: #00d4aa;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.card-type {
  font-size: 11px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.type-review .card-type {
  background: #1a3a4a;
  color: #5dade2;
}

.type-change .card-type {
  background: #3a2a1a;
  color: #e59d5d;
}

.type-architecture .card-type {
  background: #2a1a3a;
  color: #a95de5;
}

.card-priority {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 3px;
}

.priority-p0 {
  background: #4a1a1a;
  color: #e55d5d;
}

.priority-p1 {
  background: #4a3a1a;
  color: #e5a55d;
}

.priority-p2,
.priority-p3 {
  background: #2a2a2a;
  color: #888;
}

.card-title {
  font-size: 14px;
  font-weight: 500;
  color: #e0e0e0;
  margin-bottom: 12px;
  line-height: 1.4;
}

.card-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  color: #666;
  margin-bottom: 8px;
}

.card-id {
  font-family: monospace;
}

.card-status {
  display: flex;
  align-items: center;
  gap: 4px;
}

.card-owner {
  margin-top: 8px;
}

.agent-badge {
  display: inline-block;
  font-size: 10px;
  padding: 4px 8px;
  background: #0a2a2a;
  color: #00d4aa;
  border-radius: 4px;
  font-family: monospace;
}

.card-metrics {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #2a2a2a;
}

.metric {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
}

.metric-label {
  color: #888;
  min-width: 70px;
}

.metric-bar {
  flex: 1;
  height: 4px;
  background: #2a2a2a;
  border-radius: 2px;
  overflow: hidden;
}

.metric-fill {
  height: 100%;
  background: #00d4aa;
  transition: width 0.3s;
}
</style>
