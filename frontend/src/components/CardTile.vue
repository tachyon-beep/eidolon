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
      <span v-if="grade" class="card-grade">{{ grade }}</span>
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

const grade = computed(() => props.card.metrics?.grade || '')

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
  background: rgba(30, 30, 52, 0.5);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(167, 139, 250, 0.15);
  border-radius: 16px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.card-tile::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--amber-primary), transparent);
  opacity: 0;
  transition: opacity 0.4s;
}

.card-tile:hover::before {
  opacity: 1;
}

.card-tile::after {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at var(--mouse-x, 50%) var(--mouse-y, 50%),
    rgba(245, 158, 11, 0.08) 0%,
    transparent 50%
  );
  opacity: 0;
  transition: opacity 0.3s;
  pointer-events: none;
}

.card-tile:hover::after {
  opacity: 1;
}

.card-tile:hover {
  border-color: var(--amber-primary);
  transform: translateY(-4px);
  box-shadow:
    0 8px 24px rgba(0, 0, 0, 0.4),
    0 0 20px var(--amber-glow);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  position: relative;
  z-index: 1;
}

.card-type {
  font-family: var(--font-display);
  font-size: 10px;
  font-weight: 700;
  padding: 6px 10px;
  border-radius: 8px;
  text-transform: uppercase;
  letter-spacing: 1px;
  border: 1px solid;
}

.card-grade {
  font-family: var(--font-display);
  font-size: 10px;
  font-weight: 700;
  padding: 4px 8px;
  border-radius: 8px;
  border: 1px solid rgba(59, 130, 246, 0.3);
  color: var(--electric-blue);
  background: rgba(59, 130, 246, 0.12);
}

.type-review .card-type {
  background: rgba(59, 130, 246, 0.15);
  color: var(--electric-blue);
  border-color: rgba(59, 130, 246, 0.3);
  box-shadow: 0 0 12px rgba(59, 130, 246, 0.2);
}

.type-change .card-type {
  background: rgba(245, 158, 11, 0.15);
  color: var(--amber-bright);
  border-color: rgba(245, 158, 11, 0.3);
  box-shadow: 0 0 12px rgba(245, 158, 11, 0.2);
}

.type-architecture .card-type {
  background: rgba(167, 139, 250, 0.15);
  color: var(--purple-soft);
  border-color: rgba(167, 139, 250, 0.3);
  box-shadow: 0 0 12px rgba(167, 139, 250, 0.2);
}

.card-priority {
  font-family: var(--font-display);
  font-size: 9px;
  font-weight: 700;
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid;
}

.priority-p0 {
  background: rgba(248, 113, 113, 0.15);
  color: var(--coral-danger);
  border-color: rgba(248, 113, 113, 0.4);
  animation: priorityPulse 2s ease-in-out infinite;
}

@keyframes priorityPulse {
  0%, 100% {
    box-shadow: 0 0 8px rgba(248, 113, 113, 0.3);
  }
  50% {
    box-shadow: 0 0 16px rgba(248, 113, 113, 0.5);
  }
}

.priority-p1 {
  background: rgba(245, 158, 11, 0.15);
  color: var(--amber-primary);
  border-color: rgba(245, 158, 11, 0.3);
}

.priority-p2,
.priority-p3 {
  background: rgba(107, 107, 130, 0.1);
  color: var(--text-muted);
  border-color: rgba(107, 107, 130, 0.2);
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 14px;
  line-height: 1.5;
  position: relative;
  z-index: 1;
}

.card-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  color: var(--text-muted);
  margin-bottom: 10px;
  position: relative;
  z-index: 1;
}

.card-id {
  font-family: var(--font-display);
  font-size: 10px;
  padding: 4px 8px;
  background: rgba(167, 139, 250, 0.08);
  border: 1px solid rgba(167, 139, 250, 0.15);
  border-radius: 6px;
  color: var(--purple-soft);
}

.card-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
  color: var(--text-secondary);
}

.card-owner {
  margin-top: 10px;
  position: relative;
  z-index: 1;
}

.agent-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-display);
  font-size: 10px;
  font-weight: 600;
  padding: 6px 10px;
  background: rgba(6, 182, 212, 0.12);
  border: 1px solid rgba(6, 182, 212, 0.25);
  color: var(--cyan-active);
  border-radius: 8px;
}

.agent-badge::before {
  content: '◎';
  font-size: 11px;
  opacity: 0.7;
}

.card-metrics {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid rgba(167, 139, 250, 0.12);
  position: relative;
  z-index: 1;
}

.metric {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 11px;
}

.metric-label {
  font-weight: 500;
  color: var(--text-secondary);
  min-width: 80px;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.metric-bar {
  flex: 1;
  height: 6px;
  background: rgba(107, 107, 130, 0.15);
  border-radius: 3px;
  overflow: hidden;
  border: 1px solid rgba(167, 139, 250, 0.1);
}

.metric-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--cyan-active), var(--electric-blue));
  transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 0 8px var(--cyan-glow);
}
</style>
