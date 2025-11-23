<template>
  <div class="code-view">
    <div class="view-header">
      <div>
        <h1>Code</h1>
        <p class="view-subtitle">Changes • Patches • Diffs • Code browser</p>
      </div>
    </div>

    <div class="filter-bar">
      <div class="filter-group">
        <label>Status:</label>
        <select v-model="statusFilter" @change="applyFilters" class="filter-select">
          <option value="">All</option>
          <option value="Proposed">Proposed</option>
          <option value="In-Review">In-Review</option>
          <option value="Approved">Approved</option>
        </select>
      </div>

      <div class="stats">
        {{ filteredCards.length }} change{{ filteredCards.length !== 1 ? 's' : '' }}
      </div>
    </div>

    <div class="cards-board">
      <div v-if="filteredCards.length === 0" class="empty-state">
        <div class="empty-icon">💻</div>
        <h2>No Code Changes</h2>
        <p>Code change cards will appear here when analysis produces patch proposals.</p>
      </div>

      <div v-else class="cards-grid">
        <CardTile
          v-for="card in filteredCards"
          :key="card.id"
          :card="card"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useCardStore } from '../stores/cardStore'
import { storeToRefs } from 'pinia'
import CardTile from '../components/CardTile.vue'

const cardStore = useCardStore()
const { cards } = storeToRefs(cardStore)

const statusFilter = ref('')

const filteredCards = computed(() => {
  let result = cards.value.filter(c => c.type === 'Change')

  if (statusFilter.value) {
    result = result.filter(c => c.status === statusFilter.value)
  }

  return result
})

const applyFilters = () => {
  // Filters are reactive
}

onMounted(() => {
  cardStore.fetchCards()
})
</script>

<style scoped>
.code-view {
  display: flex;
  flex-direction: column;
  gap: 28px;
  animation: slideIn 0.5s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.view-header {
  position: relative;
}

.view-header::before {
  content: '';
  position: absolute;
  left: -40px;
  top: 0;
  width: 3px;
  height: 60px;
  background: linear-gradient(180deg, var(--amber-primary), transparent);
  border-radius: 2px;
}

.view-header h1 {
  font-family: var(--font-display);
  font-size: 36px;
  font-weight: 800;
  color: var(--text-primary);
  margin-bottom: 8px;
  letter-spacing: -0.5px;
  background: linear-gradient(135deg, var(--text-primary), var(--amber-bright));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.view-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
  letter-spacing: 0.3px;
}

.filter-bar {
  display: flex;
  gap: 20px;
  align-items: center;
  padding: 16px 20px;
  background: rgba(30, 30, 52, 0.3);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  border: 1px solid rgba(167, 139, 250, 0.12);
  border-radius: 12px;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.filter-group label {
  font-size: 11px;
  color: var(--text-secondary);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.filter-select {
  padding: 8px 12px;
  background: rgba(30, 30, 52, 0.6);
  border: 1px solid rgba(167, 139, 250, 0.2);
  border-radius: 8px;
  color: var(--text-primary);
  font-family: var(--font-display);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-select:focus {
  outline: none;
  border-color: var(--purple-soft);
  box-shadow: 0 0 0 2px var(--purple-glow);
}

.stats {
  margin-left: auto;
  font-family: var(--font-display);
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  padding: 6px 12px;
  background: rgba(167, 139, 250, 0.08);
  border-radius: 8px;
  border: 1px solid rgba(167, 139, 250, 0.15);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;
  background: rgba(30, 30, 52, 0.2);
  border: 2px dashed rgba(167, 139, 250, 0.2);
  border-radius: 16px;
}

.empty-icon {
  font-size: 72px;
  margin-bottom: 20px;
  opacity: 0.2;
  filter: grayscale(1);
}

.empty-state h2 {
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 700;
  color: var(--text-secondary);
  margin-bottom: 10px;
}

.empty-state p {
  font-size: 14px;
  color: var(--text-muted);
  max-width: 400px;
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 20px;
  animation: cardsAppear 0.6s ease-out;
}

@keyframes cardsAppear {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.cards-grid > * {
  animation: cardSlideIn 0.4s ease-out backwards;
}

.cards-grid > *:nth-child(1) { animation-delay: 0.05s; }
.cards-grid > *:nth-child(2) { animation-delay: 0.1s; }
.cards-grid > *:nth-child(3) { animation-delay: 0.15s; }
.cards-grid > *:nth-child(4) { animation-delay: 0.2s; }
.cards-grid > *:nth-child(5) { animation-delay: 0.25s; }
.cards-grid > *:nth-child(6) { animation-delay: 0.3s; }

@keyframes cardSlideIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
