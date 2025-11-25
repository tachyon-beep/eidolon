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

        <div class="detail-section" v-if="card.metrics?.grade">
          <label>Grade</label>
          <div class="detail-value">{{ card.metrics.grade }}</div>
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

        <div v-if="card.issues && card.issues.length" class="issues-section">
          <h3>Issues ({{ card.issues.length }})</h3>
          <div v-for="(issue, idx) in card.issues" :key="idx" class="issue-item">
            <div class="issue-header">
              <div class="issue-title">{{ issue.title }}</div>
              <div class="issue-chips">
                <span class="issue-chip severity" :class="`sev-${issue.severity?.toLowerCase() || 'low'}`">{{ issue.severity || 'Low' }}</span>
                <span v-if="issue.type" class="issue-chip type">{{ issue.type }}</span>
                <span v-if="issue.line_start" class="issue-chip line">L{{ issue.line_start }}{{ issue.line_end ? `-${issue.line_end}` : '' }}</span>
              </div>
            </div>
            <div class="issue-description">{{ issue.description }}</div>
            <pre v-if="issue.fix_code" class="issue-fix"><code>{{ issue.fix_code }}</code></pre>
            <div class="issue-actions">
              <div class="issue-route">
                <label>Send to tab:</label>
                <select :value="getDestination(idx)" @change="setDestination(idx, $event.target.value)">
                  <option value="Explore">Explore</option>
                  <option value="Code">Code</option>
                  <option value="Plan">Plan</option>
                </select>
              </div>
              <button
                class="promote-btn"
                :disabled="isPromoted(issue, idx)"
                @click="promoteIssue(issue, idx)"
              >
                {{ isPromoted(issue, idx) ? 'Promoted' : 'Promote to Card' }}
              </button>
            </div>
          </div>
        </div>
        <div v-else class="issues-fallback">
          <span>No structured issues attached; showing raw analysis only.</span>
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

      <!-- Fix Tab -->
      <div v-if="activeTab === 'fix' && card.proposed_fix" class="tab-panel">
        <div class="fix-header">
          <h3>Proposed Fix</h3>
          <div class="fix-badges">
            <span v-if="card.proposed_fix.validated" class="badge badge-success">✓ Validated</span>
            <span v-else class="badge badge-error">⚠ Validation Failed</span>
            <span class="badge badge-confidence">
              {{ Math.round(card.proposed_fix.confidence * 100) }}% confident
            </span>
          </div>
        </div>

        <div v-if="card.proposed_fix.explanation" class="fix-explanation">
          <h4>Explanation</h4>
          <p>{{ card.proposed_fix.explanation }}</p>
        </div>

        <div class="fix-diff">
          <div class="diff-panel">
            <h4>Original Code</h4>
            <pre class="code-block original"><code>{{ card.proposed_fix.original_code }}</code></pre>
          </div>

          <div class="diff-panel">
            <h4>Fixed Code</h4>
            <pre class="code-block fixed"><code>{{ card.proposed_fix.fixed_code }}</code></pre>
          </div>
        </div>

        <div v-if="!card.proposed_fix.validated" class="validation-errors">
          <h4>Validation Errors</h4>
          <div v-for="(error, idx) in card.proposed_fix.validation_errors" :key="idx" class="error-item">
            {{ error }}
          </div>
        </div>

        <div class="fix-actions">
          <button
            v-if="card.proposed_fix.validated"
            class="apply-fix-btn"
            @click="applyFix"
            :disabled="applying"
          >
            {{ applying ? 'Applying...' : 'Apply Fix' }}
          </button>
          <button
            v-if="backupPath"
            class="rollback-btn"
            @click="rollbackFix"
            :disabled="applying"
          >
            Rollback
          </button>
          <p class="fix-warning" v-if="card.proposed_fix.validated">
            A backup will be created before applying the fix
          </p>
          <p v-if="backupPath" class="fix-backup">Backup: {{ backupPath }}</p>
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
        <AgentSnoop :agent="agentData" @select-card="selectCardFromSnoop" />
      </div>
    </div>

    <div class="drawer-actions">
      <button class="action-btn" @click="routeCard">
        Route Card
      </button>
      <button class="action-btn secondary" @click="updateStatus">
        Update Status
      </button>
      <button class="action-btn tertiary" @click="showReviewModal = true">
        LLM Review
      </button>
    </div>

    <div v-if="showReviewModal" class="modal-backdrop">
      <div class="modal">
        <h3>Send for LLM Review</h3>
        <label class="modal-row">
          <input type="checkbox" v-model="reviewOptions.include_callers" />
          <span>Attach callers</span>
        </label>
        <label class="modal-row">
          <input type="checkbox" v-model="reviewOptions.include_callees" />
          <span>Attach callees</span>
        </label>
        <label class="modal-row">
          <input type="checkbox" v-model="reviewOptions.include_peers" />
          <span>Attach peers (class/method)</span>
        </label>

        <div class="modal-actions">
          <button class="action-btn" @click="requestReview" :disabled="reviewing">
            {{ reviewing ? 'Reviewing...' : 'Send' }}
          </button>
          <button class="action-btn secondary" @click="showReviewModal = false">Cancel</button>
        </div>

        <div v-if="reviewResponse" class="modal-response">
          <h4>LLM Response</h4>
          <pre>{{ reviewResponse }}</pre>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useCardStore } from '../stores/cardStore'
import { storeToRefs } from 'pinia'
import AgentSnoop from './AgentSnoop.vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const cardStore = useCardStore()
const { selectedCard, selectedAgent } = storeToRefs(cardStore)

const card = computed(() => selectedCard.value)
const agentData = computed(() => selectedAgent.value)

const activeTab = ref('details')
const applying = ref(false)
const promotedIndices = ref([])
const showReviewModal = ref(false)
const reviewing = ref(false)
const reviewResponse = ref('')
const reviewOptions = ref({
  include_callers: true,
  include_callees: true,
  include_peers: false
})
const issueDestinations = ref({})
const backupPath = ref('')

const tabs = computed(() => {
  const baseTabs = [
    { id: 'details', label: 'Details' },
    { id: 'links', label: 'Links' },
    { id: 'log', label: 'Log' }
  ]

  if (card.value?.proposed_fix) {
    baseTabs.splice(1, 0, { id: 'fix', label: 'Proposed Fix' })
  }

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

const applyFix = async () => {
  if (!card.value?.proposed_fix || !card.value.proposed_fix.validated) {
    return
  }

  if (!confirm(`Apply this fix to ${card.value.proposed_fix.file_path}?\n\nA backup will be created automatically.`)) {
    return
  }

  applying.value = true
  try {
    const res = await cardStore.applyFix(card.value.id)
    backupPath.value = res.backup
    alert('Fix applied successfully! A backup was created.')
  } catch (error) {
    alert(`Failed to apply fix: ${error.message}`)
  } finally {
    applying.value = false
  }
}

const rollbackFix = async () => {
  alert(`Rollback is manual. Restore from backup:\n${backupPath.value || 'No backup recorded yet.'}`)
}

const renderMarkdown = (text) => {
  if (!text) return ''
  try {
    // Parse markdown to HTML
    const rawHtml = marked.parse(text)
    // Sanitize HTML to prevent XSS attacks
    return DOMPurify.sanitize(rawHtml, {
      ALLOWED_TAGS: ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'strong', 'em', 'code', 'pre', 'ul', 'ol', 'li', 'br', 'a'],
      ALLOWED_ATTR: ['href', 'title']
    })
  } catch (error) {
    console.error('Markdown rendering error:', error)
    return text
  }
}

const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  return date.toLocaleString()
}

const requestReview = async () => {
  if (!card.value) return
  reviewing.value = true
  reviewResponse.value = ''
  try {
    const res = await cardStore.reviewCard(card.value.id, reviewOptions.value)
    reviewResponse.value = res.response
  } catch (error) {
    reviewResponse.value = `Review failed: ${error.message || error}`
  } finally {
    reviewing.value = false
  }
}

const promoteIssue = async (issue, idx) => {
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

  const filePath = (card.value?.links?.code && card.value.links.code.length > 0)
    ? card.value.links.code[0].split(':')[0]
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
      parent: card.value?.id,
      links: { code: codeLinks },
      routing: { from_tab: card.value?.routing?.to_tab || 'Explore', to_tab: getDestination(idx) },
      payload_issue_index: idx
    })
    promotedIndices.value.push(idx)
    // Mark issue promoted locally and on card
    if (card.value?.issues && card.value.issues[idx]) {
      card.value.issues[idx].promoted = true
      await cardStore.updateCard(card.value.id, { issues: card.value.issues })
    }
  } catch (error) {
    console.error('Failed to promote issue', error)
  }
}

const isPromoted = (issue, idx) => issue?.promoted || promotedIndices.value.includes(idx)

const getDestination = (issueIdx) => {
  if (issueDestinations.value[issueIdx]) {
    return issueDestinations.value[issueIdx]
  }
  return 'Explore'
}

const setDestination = (issueIdx, value) => {
  issueDestinations.value = {
    ...issueDestinations.value,
    [issueIdx]: value || 'Explore'
  }
}

const selectCardFromSnoop = async (payload) => {
  // payload may be a full card or {id, title}; resolve to full card
  if (!payload) return
  let target = null
  const cards = cardStore.cards
  if (cards && Array.isArray(cards) && cards.value) {
    target = cards.value.find(c => c.id === payload.id)
  }
  if (!target && payload.id) {
    target = await cardStore.getCard(payload.id)
  }
  if (target) {
    cardStore.selectCard(target)
  }
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

.issues-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 12px;
}

.issues-section h3 {
  margin: 0;
  font-size: 13px;
  color: #e0e0e0;
}

.issue-item {
  padding: 12px;
  border: 1px solid #222;
  border-radius: 8px;
  background: #111;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.issue-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.issue-title {
  font-size: 13px;
  font-weight: 700;
  color: #e0e0e0;
}

.issue-chips {
  display: flex;
  gap: 6px;
  align-items: center;
}

.issue-chip {
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 11px;
  border: 1px solid #2a2a2a;
  color: #ccc;
}

.issue-chip.severity {
  border-color: #4b5563;
}

.issue-chip.sev-high {
  border-color: rgba(248, 113, 113, 0.6);
  color: #f87171;
}

.issue-chip.sev-medium {
  border-color: rgba(245, 158, 11, 0.6);
  color: #f59e0b;
}

.issue-chip.sev-low {
  border-color: rgba(52, 211, 153, 0.6);
  color: #34d399;
}

.issue-chip.type {
  border-color: rgba(59, 130, 246, 0.4);
  color: #7cc4ff;
}

.issue-chip.line {
  border-color: rgba(167, 139, 250, 0.4);
  color: #c4b5fd;
}

.issue-description {
  font-size: 12px;
  color: #ccc;
  line-height: 1.5;
}

.issue-fix {
  margin: 0;
  background: #0f172a;
  color: #c7d2fe;
  border-radius: 6px;
  padding: 8px;
  font-size: 12px;
  overflow-x: auto;
}

.issue-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.issue-route {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #aaa;
}

.issue-route select {
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  color: #e0e0e0;
  border-radius: 6px;
  padding: 6px 8px;
  font-size: 11px;
}

.promote-btn {
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid rgba(0, 212, 170, 0.4);
  background: rgba(0, 212, 170, 0.12);
  color: #00d4aa;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
}

.promote-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.promote-btn:not(:disabled):hover {
  background: rgba(0, 212, 170, 0.2);
  border-color: rgba(0, 212, 170, 0.6);
}

.issues-fallback {
  margin-top: 12px;
  padding: 10px;
  background: #111;
  border: 1px dashed #333;
  border-radius: 8px;
  color: #aaa;
  font-size: 12px;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
}

.modal {
  background: #0f0f0f;
  border: 1px solid #222;
  border-radius: 12px;
  padding: 20px;
  width: 420px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.modal-row {
  display: flex;
  gap: 10px;
  align-items: center;
  color: #e0e0e0;
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.modal-response {
  margin-top: 10px;
  background: #111;
  border: 1px solid #222;
  border-radius: 8px;
  padding: 10px;
  max-height: 200px;
  overflow-y: auto;
  color: #e0e0e0;
}

.action-btn.tertiary {
  border: 1px solid rgba(59, 130, 246, 0.4);
  background: rgba(59, 130, 246, 0.12);
  color: #7cc4ff;
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

/* Fix viewer styles */
.fix-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.fix-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #e0e0e0;
  margin: 0;
}

.fix-badges {
  display: flex;
  gap: 8px;
}

.badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
}

.badge-success {
  background: #1a2a1a;
  color: #5de585;
}

.badge-error {
  background: #2a1a1a;
  color: #e55d5d;
}

.badge-confidence {
  background: #1a2a2a;
  color: #5d9de5;
}

.fix-explanation {
  margin-bottom: 16px;
  padding: 12px;
  background: #1a1a1a;
  border-left: 3px solid #00d4aa;
  border-radius: 4px;
}

.fix-explanation h4 {
  font-size: 12px;
  font-weight: 600;
  color: #888;
  margin: 0 0 8px 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.fix-explanation p {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: #ccc;
}

.fix-diff {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 16px;
}

.diff-panel h4 {
  font-size: 11px;
  font-weight: 600;
  color: #888;
  margin: 0 0 8px 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.code-block {
  margin: 0;
  padding: 12px;
  background: #0a0a0a;
  border: 1px solid #2a2a2a;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 11px;
  line-height: 1.5;
}

.code-block.original {
  border-left: 3px solid #e55d5d;
}

.code-block.fixed {
  border-left: 3px solid #5de585;
}

.code-block code {
  color: #e0e0e0;
  font-family: 'Courier New', monospace;
}

.validation-errors {
  margin-bottom: 16px;
  padding: 12px;
  background: #2a1a1a;
  border: 1px solid #e55d5d;
  border-radius: 4px;
}

.validation-errors h4 {
  font-size: 12px;
  font-weight: 600;
  color: #e55d5d;
  margin: 0 0 8px 0;
}

.error-item {
  font-size: 12px;
  color: #e55d5d;
  margin: 4px 0;
}

.fix-actions {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #2a2a2a;
}

.apply-fix-btn {
  width: 100%;
  padding: 12px;
  background: #00d4aa;
  color: #000;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.apply-fix-btn:hover:not(:disabled) {
  background: #00ffcc;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 212, 170, 0.3);
}

.apply-fix-btn:disabled {
  background: #2a2a2a;
  color: #666;
  cursor: not-allowed;
}

.fix-warning {
  margin-top: 8px;
  font-size: 11px;
  color: #888;
  text-align: center;
}
</style>
