<template>
  <div class="explore-view">
    <div class="view-header">
      <div>
        <h1>Explore</h1>
        <p class="view-subtitle">Audit & documentation • Refresh thinking • Peer review</p>
      </div>

      <div class="header-actions">
        <input
          v-model="analysisPath"
          type="text"
          placeholder="Path to analyze..."
          class="path-input"
        />
        <button
          @click="startAnalysis"
          :disabled="isAnalyzing || !analysisPath"
          class="analyze-btn"
        >
          {{ isAnalyzing ? 'Analyzing...' : 'Analyze' }}
        </button>
      </div>
    </div>

    <div v-if="isAnalyzing" class="analysis-progress">
      <div class="progress-indicator">
        <div class="spinner"></div>
        <span>Deploying hierarchical agent mesh...</span>
      </div>
    </div>

    <div class="filter-bar">
      <div class="filter-group">
        <label>Type:</label>
        <select v-model="filters.type" @change="applyFilters" class="filter-select">
          <option value="">All</option>
          <option value="Review">Review</option>
          <option value="Architecture">Architecture</option>
          <option value="Change">Change</option>
        </select>
      </div>

      <div class="filter-group">
        <label>Status:</label>
        <select v-model="filters.status" @change="applyFilters" class="filter-select">
          <option value="">All</option>
          <option value="New">New</option>
          <option value="Proposed">Proposed</option>
          <option value="In-Review">In-Review</option>
        </select>
      </div>

      <div class="stats">
        {{ filteredCards.length }} card{{ filteredCards.length !== 1 ? 's' : '' }}
      </div>
    </div>

    <div class="cards-board">
      <div v-if="filteredCards.length === 0" class="empty-state">
        <div class="empty-icon">🔍</div>
        <h2>No Analysis Yet</h2>
        <p>Enter a path and click "Analyze" to begin hierarchical code analysis.</p>
      </div>

      <div v-else class="cards-grid">
        <CardTile
          v-for="card in filteredCards"
          :key="card.id"
          :card="card"
        />
      </div>
    </div>

    <!-- Agent Hierarchy Visualization -->
    <div v-if="systemAgent" class="agent-hierarchy">
      <h2>Agent Hierarchy</h2>
      <AgentTree :agent-id="systemAgent.id" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useCardStore } from '../stores/cardStore'
import { storeToRefs } from 'pinia'
import CardTile from '../components/CardTile.vue'
import AgentTree from '../components/AgentTree.vue'

const cardStore = useCardStore()
const { cards, agents, isAnalyzing } = storeToRefs(cardStore)

const analysisPath = ref('../examples')
const filters = ref({
  type: '',
  status: ''
})

const filteredCards = computed(() => {
  let result = cards.value

  if (filters.value.type) {
    result = result.filter(c => c.type === filters.value.type)
  }

  if (filters.value.status) {
    result = result.filter(c => c.status === filters.value.status)
  }

  return result
})

const systemAgent = computed(() => {
  return agents.value.find(a => a.scope === 'System')
})

const startAnalysis = async () => {
  try {
    await cardStore.analyzeCodebase(analysisPath.value)
  } catch (error) {
    console.error('Analysis failed:', error)
  }
}

const applyFilters = () => {
  // Filters are reactive, so this just triggers the computed
}

onMounted(() => {
  cardStore.fetchCards()
  cardStore.fetchAgents()
})
</script>

<style scoped>
.explore-view {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.view-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
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

.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.path-input {
  padding: 10px 14px;
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 6px;
  color: #e0e0e0;
  font-size: 13px;
  width: 300px;
  transition: all 0.2s;
}

.path-input:focus {
  outline: none;
  border-color: #00d4aa;
  box-shadow: 0 0 0 3px rgba(0, 212, 170, 0.1);
}

.analyze-btn {
  padding: 10px 20px;
  background: #00d4aa;
  color: #000;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.analyze-btn:hover:not(:disabled) {
  background: #00ffcc;
  transform: translateY(-1px);
}

.analyze-btn:disabled {
  background: #2a2a2a;
  color: #666;
  cursor: not-allowed;
}

.analysis-progress {
  padding: 20px;
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 8px;
}

.progress-indicator {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
  color: #00d4aa;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid #2a2a2a;
  border-top-color: #00d4aa;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
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

.filter-select:focus {
  outline: none;
  border-color: #00d4aa;
}

.stats {
  margin-left: auto;
  font-size: 12px;
  color: #666;
}

.cards-board {
  min-height: 300px;
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

.agent-hierarchy {
  margin-top: 24px;
  padding: 20px;
  background: #111;
  border: 1px solid #222;
  border-radius: 8px;
}

.agent-hierarchy h2 {
  font-size: 18px;
  font-weight: 600;
  color: #e0e0e0;
  margin-bottom: 16px;
}
</style>
