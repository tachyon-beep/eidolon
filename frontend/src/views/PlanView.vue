<template>
  <div class="plan-view">
    <div class="view-header">
      <div>
        <h1>Plan</h1>
        <p class="view-subtitle">Architecture • Top-down design • Decomposition</p>
      </div>
    </div>

    <div class="filter-bar">
      <div class="filter-group">
        <label>Status:</label>
        <select v-model="statusFilter" @change="applyFilters" class="filter-select">
          <option value="">All</option>
          <option value="New">New</option>
          <option value="Proposed">Proposed</option>
          <option value="Approved">Approved</option>
        </select>
      </div>

      <div class="stats">
        {{ filteredCards.length }} architecture card{{ filteredCards.length !== 1 ? 's' : '' }}
      </div>

      <button class="new-ba-btn" @click="showBA = true">New Project (BA)</button>
    </div>

    <div v-if="showBA" class="ba-panel">
      <div class="panel-row">
        <label>Project Name</label>
        <input v-model="baForm.project_name" type="text" placeholder="New initiative name" />
      </div>
      <div class="panel-row">
        <label>Path (folder/repo)</label>
        <input v-model="baForm.path" type="text" placeholder="/path/to/repo" />
      </div>
      <div class="panel-row">
        <label>Description</label>
        <textarea v-model="baForm.description" rows="3" placeholder="High-level description"></textarea>
      </div>
      <div class="panel-row">
        <label>Goals (comma separated)</label>
        <input v-model="baGoals" type="text" placeholder="Improve reliability, Reduce latency" />
      </div>
      <div class="panel-row">
        <label>Constraints (comma separated)</label>
        <input v-model="baConstraints" type="text" placeholder="No downtime, Budget cap" />
      </div>
      <div class="panel-row">
        <label>Assumptions (comma separated)</label>
        <input v-model="baAssumptions" type="text" placeholder="Team size 3, Python stack" />
      </div>
      <div v-if="baError" class="ba-error">{{ baError }}</div>
      <div class="panel-actions">
        <button class="submit-btn" :disabled="baLoading" @click="runBA">
          {{ baLoading ? 'Generating...' : 'Generate feature cards' }}
        </button>
        <button class="cancel-btn" @click="resetBA">Close</button>
      </div>
      <div v-if="baGenerated.length" class="ba-results">
        <h4>Generated Feature Cards</h4>
        <div class="ba-card" v-for="(c, idx) in baGenerated" :key="idx">
          <div class="ba-title">{{ c.title }}</div>
          <div class="ba-summary">{{ c.summary }}</div>
          <div class="ba-meta">Priority: {{ c.priority }}</div>
          <button class="submit-btn" @click="saveGenerated(c)">Save to Plan</button>
        </div>
      </div>
    </div>

    <div class="cards-board">
      <div v-if="filteredCards.length === 0" class="empty-state">
        <div class="empty-icon">📐</div>
        <h2>No Architecture Cards</h2>
        <p>System-level architecture and planning cards will appear here.</p>
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
const showBA = ref(false)
const baLoading = ref(false)
const baGenerated = ref([])
const baForm = ref({
  project_name: '',
  description: '',
  path: ''
})
const baGoals = ref('')
const baConstraints = ref('')
const baAssumptions = ref('')
const baError = ref('')

const filteredCards = computed(() => {
  let result = cards.value.filter(c => c.type === 'Architecture')

  if (statusFilter.value) {
    result = result.filter(c => c.status === statusFilter.value)
  }

  return result
})

const applyFilters = () => {
  // Filters are reactive
}

const resetBA = () => {
  baForm.value = { project_name: '', description: '', path: '' }
  baGoals.value = ''
  baConstraints.value = ''
  baAssumptions.value = ''
  baGenerated.value = []
  showBA.value = false
  baError.value = ''
}

const runBA = async () => {
  if (!baForm.value.project_name || !baForm.value.description || !baForm.value.path) return
  baLoading.value = true
  baError.value = ''
  try {
    const cards = await cardStore.generateBAProject({
      project_name: baForm.value.project_name,
      description: baForm.value.description,
      path: baForm.value.path,
      goals: baGoals.value ? baGoals.value.split(',').map(g => g.trim()).filter(Boolean) : [],
      constraints: baConstraints.value ? baConstraints.value.split(',').map(g => g.trim()).filter(Boolean) : [],
      assumptions: baAssumptions.value ? baAssumptions.value.split(',').map(g => g.trim()).filter(Boolean) : []
    })
    baGenerated.value = cards
  } catch (error) {
    baError.value = error.message || 'BA generation failed'
  } finally {
    baLoading.value = false
  }
}

const saveGenerated = async (c) => {
  try {
    await cardStore.createCard({
      title: c.title,
      summary: c.summary,
      priority: c.priority || 'P2',
      status: 'New',
      type: 'Requirement',
      routing: { from_tab: 'Plan', to_tab: 'Plan' }
    })
    await cardStore.fetchCards()
  } catch (error) {
    console.error('Failed to save generated card', error)
  }
}

onMounted(() => {
  cardStore.fetchCards()
})
</script>

<style scoped>
.plan-view {
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

.new-ba-btn {
  padding: 10px 14px;
  border: 1px solid rgba(59, 130, 246, 0.4);
  border-radius: 10px;
  background: rgba(59, 130, 246, 0.12);
  color: var(--text-primary);
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
}

.new-ba-btn:hover {
  border-color: rgba(59, 130, 246, 0.6);
  background: rgba(59, 130, 246, 0.18);
}

.ba-panel {
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

.ba-results {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ba-error {
  color: var(--coral-danger);
  font-size: 12px;
  padding: 8px 10px;
  background: rgba(248, 113, 113, 0.1);
  border: 1px solid rgba(248, 113, 113, 0.3);
  border-radius: 8px;
}

.ba-card {
  background: rgba(13, 13, 30, 0.4);
  border: 1px solid rgba(167, 139, 250, 0.15);
  border-radius: 10px;
  padding: 10px;
}

.ba-title {
  font-weight: 700;
  font-size: 13px;
  color: var(--text-primary);
}

.ba-summary {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 6px 0;
  white-space: pre-wrap;
}

.ba-meta {
  font-size: 11px;
  color: var(--text-muted);
  margin-bottom: 6px;
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
