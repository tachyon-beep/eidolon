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
          <span>{{ currentActivity }}</span>
        </div>
        <div class="progress-percentage">{{ progressPercentage }}%</div>
      </div>

      <!-- Real-time Activity Log -->
      <div v-if="recentActivities.length > 0" class="activity-log">
        <div class="activity-log-title">Activity Log:</div>
        <div class="activity-items">
          <div
            v-for="(activity, index) in recentActivities.slice(0, 5)"
            :key="`${activity.timestamp}-${index}`"
            class="activity-item"
            :class="{ 'activity-latest': index === 0 }"
          >
            {{ activity.message }}
          </div>
        </div>
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

      <button class="new-card-btn" @click="showCreateCard = !showCreateCard">
        {{ showCreateCard ? 'Close' : 'New Card' }}
      </button>
    </div>

    <div v-if="showCreateCard" class="create-card-panel">
      <div class="panel-row">
        <label>Title</label>
        <input v-model="newCard.title" type="text" placeholder="Short title" />
      </div>
      <div class="panel-row">
        <label>Type</label>
        <select v-model="newCard.type">
          <option value="Review">Review</option>
          <option value="Change">Change</option>
          <option value="Architecture">Architecture</option>
          <option value="Defect">Defect</option>
          <option value="Test">Test</option>
          <option value="Requirement">Requirement</option>
        </select>
      </div>
      <div class="panel-row">
        <label>Priority</label>
        <select v-model="newCard.priority">
          <option value="P0">P0</option>
          <option value="P1">P1</option>
          <option value="P2">P2</option>
          <option value="P3">P3</option>
        </select>
      </div>
      <div class="panel-row">
        <label>Summary</label>
        <textarea v-model="newCard.summary" rows="3" placeholder="Why this matters"></textarea>
      </div>
      <div class="panel-actions">
        <button class="submit-btn" @click="handleCreateCard">Create</button>
        <button class="cancel-btn" @click="resetCreateCard">Cancel</button>
      </div>
    </div>

    <div class="cards-board">
      <div v-if="filteredCards.length === 0" class="empty-state">
        <div class="empty-icon">🔍</div>
        <h2>No Analysis Yet</h2>
        <p>Enter a path and click "Analyze" to begin hierarchical code analysis.</p>
      </div>

      <div v-else class="cards-grid">
        <div v-for="card in filteredCards" :key="card.id" class="card-with-issues">
          <CardTile :card="card" />
          <div v-if="card.issues && card.issues.length" class="inline-issues">
            <div class="issues-header">
              <span>Issues</span>
            </div>
            <div class="issues-list">
              <div
                v-for="(issue, idx) in card.issues"
                :key="idx"
                class="inline-issue"
              >
                <div class="inline-issue-main">
                  <div class="inline-issue-title">{{ issue.title }}</div>
                  <div class="inline-issue-meta">
                    <span class="inline-chip sev" :class="`sev-${(issue.severity || 'low').toLowerCase()}`">{{ issue.severity || 'Low' }}</span>
                    <span v-if="issue.line_start" class="inline-chip line">L{{ issue.line_start }}{{ issue.line_end ? `-${issue.line_end}` : '' }}</span>
                    <span v-if="issue.promoted" class="inline-chip promoted">Promoted</span>
                  </div>
                </div>
                  <div class="inline-issue-actions">
                    <label>Send to tab:</label>
                  <select :value="getDestination(card.id, idx)" @change="setDestination(card.id, idx, $event.target.value)">
                    <option value="Explore">Explore</option>
                    <option value="Code">Code</option>
                    <option value="Plan">Plan</option>
                  </select>
                  <button
                    class="promote-btn"
                    :disabled="issue.promoted"
                    @click="promoteIssue(card, issue, idx)"
                  >
                    {{ issue.promoted ? 'Promoted' : 'Promote' }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
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
const { cards, agents, isAnalyzing, analysisProgress, cacheStats, recentActivities } = storeToRefs(cardStore)

const analysisPath = ref('../examples')
const filters = ref({
  type: '',
  status: ''
})
const showCreateCard = ref(false)
const newCard = ref({
  title: '',
  type: 'Review',
  priority: 'P2',
  summary: ''
})
const issueDestinations = ref({})

const currentActivity = computed(() => {
  if (recentActivities.value.length > 0) {
    return recentActivities.value[0].message
  }
  return 'Deploying hierarchical agent mesh...'
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

const resetCreateCard = () => {
  newCard.value = {
    title: '',
    type: 'Review',
    priority: 'P2',
    summary: ''
  }
  showCreateCard.value = false
}

const handleCreateCard = async () => {
  if (!newCard.value.title) return
  try {
    await cardStore.createCard({
      title: newCard.value.title,
      type: newCard.value.type,
      summary: newCard.value.summary,
      priority: newCard.value.priority,
      status: 'New'
    })
    resetCreateCard()
    await cardStore.fetchCards()
  } catch (error) {
    console.error('Failed to create card', error)
  }
}

const getDestination = (cardId, issueIdx) => {
  const cardDest = issueDestinations.value[cardId]
  if (cardDest && cardDest[issueIdx]) {
    return cardDest[issueIdx]
  }
  return 'Explore'
}

const setDestination = (cardId, issueIdx, value) => {
  const existing = issueDestinations.value[cardId] || {}
  issueDestinations.value = {
    ...issueDestinations.value,
    [cardId]: {
      ...existing,
      [issueIdx]: value || 'Explore'
    }
  }
}

const promoteIssue = async (card, issue, idx) => {
  const severityMap = {
    high: 'P0',
    medium: 'P1',
    low: 'P2'
  }
  const typeMap = {
    defect: 'Defect',
    bug: 'Defect',
    security: 'Defect',
    refactor: 'Change',
    performance: 'Change',
    change: 'Change',
    doc: 'Review',
    review: 'Review',
    test: 'Test',
    requirement: 'Requirement'
  }

  const severityKey = (issue.severity || '').toLowerCase()
  const issueTypeKey = (issue.type || '').toLowerCase()
  const dest = getDestination(card.id, idx)

  const filePath = (card.links?.code && card.links.code.length > 0)
    ? card.links.code[0].split(':')[0]
    : ''

  const codeLinks = []
  if (filePath) {
    const start = issue.line_start || ''
    codeLinks.push(start ? `${filePath}:${start}` : filePath)
  }

  try {
    await cardStore.createCard({
      title: issue.title || 'Issue',
      type: typeMap[issueTypeKey] || 'Review',
      summary: issue.description || '',
      priority: severityMap[severityKey] || 'P2',
      status: 'New',
      parent: card.id,
      links: { code: codeLinks },
      routing: { from_tab: card.routing?.to_tab || 'Explore', to_tab: dest },
      payload_issue_index: idx
    })
    await cardStore.fetchCards()
  } catch (error) {
    console.error('Failed to promote issue', error)
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
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
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
  animation: titleShimmer 3s ease-in-out infinite;
}

@keyframes titleShimmer {
  0%, 100% {
    filter: brightness(1);
  }
  50% {
    filter: brightness(1.2);
  }
}

.view-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
  letter-spacing: 0.3px;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.path-input {
  padding: 12px 16px;
  background: rgba(30, 30, 52, 0.6);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(167, 139, 250, 0.2);
  border-radius: 12px;
  color: var(--text-primary);
  font-family: var(--font-display);
  font-size: 13px;
  width: 320px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.path-input::placeholder {
  color: var(--text-muted);
  opacity: 0.6;
}

.path-input:focus {
  outline: none;
  border-color: var(--amber-primary);
  background: rgba(30, 30, 52, 0.8);
  box-shadow:
    0 0 0 3px var(--amber-glow),
    0 4px 12px rgba(0, 0, 0, 0.2);
  transform: translateY(-1px);
}

.analyze-btn {
  padding: 12px 28px;
  background: linear-gradient(135deg, var(--amber-primary), var(--amber-bright));
  color: var(--deep-space);
  border: none;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.5px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  text-transform: uppercase;
  box-shadow: 0 0 20px var(--amber-glow);
  position: relative;
  overflow: hidden;
}

.analyze-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, var(--amber-bright), var(--amber-primary));
  opacity: 0;
  transition: opacity 0.3s;
}

.analyze-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 0 30px var(--amber-glow), 0 6px 16px rgba(0, 0, 0, 0.3);
}

.analyze-btn:hover:not(:disabled)::before {
  opacity: 1;
}

.analyze-btn span {
  position: relative;
  z-index: 1;
}

.analyze-btn:disabled {
  background: rgba(107, 107, 130, 0.2);
  color: var(--text-muted);
  cursor: not-allowed;
  box-shadow: none;
}

.analysis-progress {
  padding: 24px;
  background: rgba(30, 30, 52, 0.6);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(6, 182, 212, 0.3);
  border-radius: 16px;
  position: relative;
  overflow: hidden;
  animation: progressPulse 2s ease-in-out infinite;
}

@keyframes progressPulse {
  0%, 100% {
    box-shadow: 0 0 20px rgba(6, 182, 212, 0.2);
  }
  50% {
    box-shadow: 0 0 30px rgba(6, 182, 212, 0.3);
  }
}

.analysis-progress::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg,
    transparent,
    var(--cyan-active),
    var(--electric-blue),
    transparent
  );
  animation: shimmer 2s linear infinite;
}

@keyframes shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.progress-title {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 14px;
  color: var(--cyan-active);
  font-weight: 600;
  letter-spacing: 0.3px;
}

.progress-percentage {
  font-family: var(--font-display);
  font-size: 24px;
  font-weight: 800;
  color: var(--cyan-active);
  font-variant-numeric: tabular-nums;
  text-shadow: 0 0 12px var(--cyan-glow);
}

.progress-details {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.progress-bar-container {
  width: 100%;
  height: 10px;
  background: rgba(13, 13, 30, 0.6);
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid rgba(59, 130, 246, 0.2);
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.3);
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg,
    var(--cyan-active),
    var(--electric-blue),
    var(--purple-soft)
  );
  border-radius: 6px;
  transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 0 16px var(--cyan-glow);
  position: relative;
  overflow: hidden;
}

.progress-bar::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 50%;
  background: linear-gradient(180deg,
    rgba(255, 255, 255, 0.3),
    transparent
  );
}

.progress-stats {
  display: flex;
  gap: 32px;
}

.stat-item {
  display: flex;
  gap: 10px;
  align-items: center;
  font-size: 13px;
}

.stat-label {
  color: var(--text-secondary);
  font-weight: 500;
  text-transform: uppercase;
  font-size: 11px;
  letter-spacing: 0.5px;
}

.stat-value {
  font-family: var(--font-display);
  color: var(--text-primary);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.stat-item.error .stat-label,
.stat-item.error .stat-value {
  color: var(--coral-danger);
}

.spinner {
  width: 22px;
  height: 22px;
  border: 3px solid rgba(6, 182, 212, 0.2);
  border-top-color: var(--cyan-active);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.activity-log {
  margin-top: 20px;
  padding: 16px;
  background: rgba(13, 13, 30, 0.4);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 12px;
}

.activity-log-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}

.activity-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.activity-item {
  font-family: var(--font-display);
  font-size: 12px;
  color: var(--text-secondary);
  padding: 8px 12px;
  background: rgba(30, 30, 52, 0.4);
  border-left: 2px solid rgba(59, 130, 246, 0.3);
  border-radius: 6px;
  animation: activityFadeIn 0.3s ease-out;
  transition: all 0.3s;
}

.activity-item.activity-latest {
  color: var(--cyan-active);
  border-left-color: var(--cyan-active);
  background: rgba(6, 182, 212, 0.1);
  box-shadow: 0 0 12px rgba(6, 182, 212, 0.15);
}

@keyframes activityFadeIn {
  from {
    opacity: 0;
    transform: translateX(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.cache-stats {
  padding: 20px 24px;
  background: rgba(30, 30, 52, 0.4);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(167, 139, 250, 0.15);
  border-radius: 14px;
}

.cache-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.cache-title {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.cache-hit-rate {
  padding: 6px 12px;
  background: rgba(107, 107, 130, 0.15);
  border: 1px solid rgba(107, 107, 130, 0.25);
  border-radius: 8px;
  font-family: var(--font-display);
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
}

.cache-hit-rate.high-hit-rate {
  background: rgba(6, 182, 212, 0.15);
  border-color: rgba(6, 182, 212, 0.3);
  color: var(--cyan-active);
  box-shadow: 0 0 12px var(--cyan-glow);
}

.clear-cache-btn {
  padding: 8px 16px;
  background: rgba(248, 113, 113, 0.1);
  border: 1px solid rgba(248, 113, 113, 0.3);
  border-radius: 8px;
  color: var(--coral-danger);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.clear-cache-btn:hover {
  background: rgba(248, 113, 113, 0.2);
  border-color: var(--coral-danger);
  transform: translateY(-1px);
  box-shadow: 0 0 12px rgba(248, 113, 113, 0.3);
}

.cache-metrics {
  display: flex;
  gap: 28px;
}

.cache-metric {
  display: flex;
  gap: 10px;
  align-items: center;
  font-size: 12px;
}

.metric-label {
  color: var(--text-secondary);
  font-weight: 500;
  text-transform: uppercase;
  font-size: 10px;
  letter-spacing: 0.5px;
}

.metric-value {
  font-family: var(--font-display);
  color: var(--text-primary);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
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

.new-card-btn {
  padding: 10px 14px;
  border: 1px solid rgba(59, 130, 246, 0.4);
  border-radius: 10px;
  background: rgba(59, 130, 246, 0.12);
  color: var(--text-primary);
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
}

.new-card-btn:hover {
  border-color: rgba(59, 130, 246, 0.6);
  background: rgba(59, 130, 246, 0.18);
}

.create-card-panel {
  padding: 16px;
  background: rgba(30, 30, 52, 0.4);
  border: 1px solid rgba(167, 139, 250, 0.2);
  border-radius: 12px;
  display: grid;
  gap: 12px;
}

.panel-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.panel-row label {
  font-size: 11px;
  text-transform: uppercase;
  color: var(--text-secondary);
  letter-spacing: 0.5px;
}

.panel-row input,
.panel-row select,
.panel-row textarea {
  background: rgba(30, 30, 52, 0.6);
  border: 1px solid rgba(167, 139, 250, 0.2);
  border-radius: 8px;
  padding: 8px 10px;
  color: var(--text-primary);
  font-family: var(--font-display);
}

.panel-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.submit-btn,
.cancel-btn {
  padding: 10px 14px;
  border-radius: 8px;
  border: 1px solid rgba(167, 139, 250, 0.2);
  background: rgba(167, 139, 250, 0.1);
  color: var(--text-primary);
  cursor: pointer;
  font-weight: 700;
}

.submit-btn {
  border-color: rgba(0, 212, 170, 0.5);
  background: rgba(0, 212, 170, 0.15);
}

.submit-btn:hover {
  background: rgba(0, 212, 170, 0.25);
}

.cancel-btn:hover {
  background: rgba(167, 139, 250, 0.18);
}

.cards-board {
  min-height: 300px;
}

.card-with-issues {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.inline-issues {
  background: rgba(30, 30, 52, 0.25);
  border: 1px solid rgba(167, 139, 250, 0.15);
  border-radius: 12px;
  padding: 10px;
}

.issues-header {
  font-size: 12px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}

.issues-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.inline-issue {
  background: rgba(13, 13, 30, 0.4);
  border: 1px solid rgba(167, 139, 250, 0.12);
  border-radius: 10px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.inline-issue-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.inline-issue-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
}

.inline-issue-meta {
  display: flex;
  gap: 6px;
  align-items: center;
}

.inline-chip {
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 11px;
  border: 1px solid rgba(167, 139, 250, 0.2);
  color: var(--text-primary);
}

.inline-chip.sev-high {
  border-color: rgba(248, 113, 113, 0.6);
  color: #f87171;
}

.inline-chip.sev-medium {
  border-color: rgba(245, 158, 11, 0.6);
  color: #f59e0b;
}

.inline-chip.sev-low {
  border-color: rgba(52, 211, 153, 0.6);
  color: #34d399;
}

.inline-chip.line {
  border-color: rgba(167, 139, 250, 0.4);
  color: #c4b5fd;
}

.inline-chip.promoted {
  border-color: rgba(0, 212, 170, 0.5);
  color: #00d4aa;
}

.inline-issue-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: var(--text-secondary);
}

.inline-issue-actions select {
  background: rgba(30, 30, 52, 0.6);
  border: 1px solid rgba(167, 139, 250, 0.2);
  border-radius: 6px;
  color: var(--text-primary);
  padding: 6px 8px;
}

.inline-issue-actions .promote-btn {
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid rgba(0, 212, 170, 0.4);
  background: rgba(0, 212, 170, 0.12);
  color: #00d4aa;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
}

.inline-issue-actions .promote-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.inline-issue-actions .promote-btn:not(:disabled):hover {
  background: rgba(0, 212, 170, 0.2);
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

.agent-hierarchy {
  margin-top: 32px;
  padding: 24px;
  background: rgba(30, 30, 52, 0.4);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(167, 139, 250, 0.15);
  border-radius: 16px;
}

.agent-hierarchy h2 {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(167, 139, 250, 0.15);
}
</style>
