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
      <div class="progress-header">
        <div class="progress-title">
          <div class="spinner"></div>
          <span>Deploying hierarchical agent mesh...</span>
        </div>
        <div class="progress-percentage">{{ progressPercentage }}%</div>
      </div>

      <div v-if="analysisProgress" class="progress-details">
        <div class="progress-bar-container">
          <div class="progress-bar" :style="{ width: progressPercentage + '%' }"></div>
        </div>

        <div class="progress-stats">
          <div class="stat-item">
            <span class="stat-label">Modules:</span>
            <span class="stat-value">{{ analysisProgress.completed_modules }} / {{ analysisProgress.total_modules }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Functions:</span>
            <span class="stat-value">{{ analysisProgress.completed_functions }} / {{ analysisProgress.total_functions }}</span>
          </div>
          <div v-if="analysisProgress.errors && analysisProgress.errors.length > 0" class="stat-item error">
            <span class="stat-label">Errors:</span>
            <span class="stat-value">{{ analysisProgress.errors.length }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Cache Statistics -->
    <div v-if="cacheStats && cacheStats.enabled" class="cache-stats">
      <div class="cache-header">
        <div class="cache-title">
          <span>⚡ Cache Statistics</span>
          <span class="cache-hit-rate" :class="{ 'high-hit-rate': cacheStats.hit_rate > 50 }">
            {{ cacheStats.hit_rate }}% hit rate
          </span>
        </div>
        <button @click="handleClearCache" class="clear-cache-btn">Clear Cache</button>
      </div>
      <div class="cache-metrics">
        <div class="cache-metric">
          <span class="metric-label">Cached Entries:</span>
          <span class="metric-value">{{ cacheStats.total_entries }}</span>
        </div>
        <div class="cache-metric">
          <span class="metric-label">Cache Size:</span>
          <span class="metric-value">{{ cacheStats.total_size_mb }} MB</span>
        </div>
        <div class="cache-metric">
          <span class="metric-label">Session Hits:</span>
          <span class="metric-value">{{ cacheStats.session_hits }}</span>
        </div>
        <div class="cache-metric">
          <span class="metric-label">Session Misses:</span>
          <span class="metric-value">{{ cacheStats.session_misses }}</span>
        </div>
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
const { cards, agents, isAnalyzing, analysisProgress, cacheStats } = storeToRefs(cardStore)

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

const progressPercentage = computed(() => {
  if (!analysisProgress.value) return 0
  const { total_modules, completed_modules, total_functions, completed_functions } = analysisProgress.value

  if (total_modules === 0 && total_functions === 0) return 0

  // Weight: 30% modules, 70% functions (since there are more functions)
  const moduleProgress = total_modules > 0 ? (completed_modules / total_modules) * 0.3 : 0
  const functionProgress = total_functions > 0 ? (completed_functions / total_functions) * 0.7 : 0

  return Math.round((moduleProgress + functionProgress) * 100)
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

const handleClearCache = async () => {
  if (confirm('Are you sure you want to clear the entire analysis cache? This cannot be undone.')) {
    try {
      await cardStore.clearCache()
      alert('Cache cleared successfully!')
    } catch (error) {
      alert('Failed to clear cache: ' + error.message)
    }
  }
}

onMounted(() => {
  cardStore.fetchCards()
  cardStore.fetchAgents()
  cardStore.fetchCacheStats()
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

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.progress-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
  color: #00d4aa;
  font-weight: 500;
}

.progress-percentage {
  font-size: 18px;
  font-weight: 700;
  color: #00d4aa;
  font-variant-numeric: tabular-nums;
}

.progress-details {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.progress-bar-container {
  width: 100%;
  height: 8px;
  background: #111;
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid #2a2a2a;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #00d4aa, #00ffcc);
  border-radius: 4px;
  transition: width 0.5s ease-out;
}

.progress-stats {
  display: flex;
  gap: 24px;
}

.stat-item {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 13px;
}

.stat-label {
  color: #888;
  font-weight: 500;
}

.stat-value {
  color: #e0e0e0;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.stat-item.error .stat-label,
.stat-item.error .stat-value {
  color: #ff6b6b;
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

.cache-stats {
  padding: 16px 20px;
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 8px;
}

.cache-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.cache-title {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 14px;
  font-weight: 600;
  color: #e0e0e0;
}

.cache-hit-rate {
  padding: 4px 10px;
  background: #2a2a2a;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  color: #888;
}

.cache-hit-rate.high-hit-rate {
  background: rgba(0, 212, 170, 0.15);
  color: #00d4aa;
}

.clear-cache-btn {
  padding: 6px 14px;
  background: #2a2a2a;
  border: 1px solid #3a3a3a;
  border-radius: 4px;
  color: #e0e0e0;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.clear-cache-btn:hover {
  background: #ff6b6b;
  border-color: #ff6b6b;
  color: #fff;
}

.cache-metrics {
  display: flex;
  gap: 24px;
}

.cache-metric {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 12px;
}

.metric-label {
  color: #888;
  font-weight: 500;
}

.metric-value {
  color: #e0e0e0;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
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
