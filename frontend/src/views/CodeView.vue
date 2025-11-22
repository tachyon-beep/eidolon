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
  gap: 24px;
}

.view-header h1 {
  font-size: 28px;
  font-weight: 600;
  color: #e0e0e0;
  margin-bottom: 6px;
}

.view-subtitle {
  font-size: 13px;
  color: #888;
}

.filter-bar {
  display: flex;
  gap: 16px;
  align-items: center;
  padding: 12px 16px;
  background: #111;
  border: 1px solid #222;
  border-radius: 6px;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-group label {
  font-size: 12px;
  color: #888;
  font-weight: 500;
}

.filter-select {
  padding: 6px 10px;
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 4px;
  color: #e0e0e0;
  font-size: 12px;
  cursor: pointer;
}

.stats {
  margin-left: auto;
  font-size: 12px;
  color: #666;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
  opacity: 0.3;
}

.empty-state h2 {
  font-size: 20px;
  font-weight: 600;
  color: #666;
  margin-bottom: 8px;
}

.empty-state p {
  font-size: 14px;
  color: #555;
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}
</style>
