import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  FileAnalysis,
  Agent,
  Message,
  Finding,
  AnalysisSession,
  WebSocketEvent,
  OrchestratorStatus,
  Severity
} from '@/types'
import { orchestratorApi } from '@/services/api'

export const useOrchestrationStore = defineStore('orchestration', () => {
  // State
  const files = ref<FileAnalysis[]>([])
  const agents = ref<Agent[]>([])
  const messages = ref<Message[]>([])
  const findings = ref<Finding[]>([])
  const sessions = ref<Map<string, AnalysisSession>>(new Map())
  const currentSessionId = ref<string | null>(null)
  const orchestratorStatus = ref<OrchestratorStatus>({
    status: 'idle',
    activeSessions: 0,
    workspace: ''
  })
  const wsConnected = ref(false)
  const wsError = ref<string | null>(null)

  let ws: WebSocket | null = null
  let reconnectAttempts = 0
  const maxReconnectAttempts = 5
  const reconnectDelay = 3000

  // Computed
  const currentSession = computed(() => {
    if (!currentSessionId.value) return null
    return sessions.value.get(currentSessionId.value) || null
  })

  const findingsBySeverity = computed(() => {
    const grouped: Record<Severity, Finding[]> = {
      critical: [],
      high: [],
      medium: [],
      low: []
    }

    findings.value.forEach(finding => {
      grouped[finding.severity].push(finding)
    })

    return grouped
  })

  const activeFiles = computed(() =>
    files.value.filter(f => f.status === 'analyzing' || f.status === 'queued')
  )

  const completedFiles = computed(() =>
    files.value.filter(f => f.status === 'complete')
  )

  const failedFiles = computed(() =>
    files.value.filter(f => f.status === 'failed')
  )

  // WebSocket connection
  function connectWebSocket() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = import.meta.env.DEV
      ? 'ws://localhost:8181/ws/events'
      : `${wsProtocol}//${window.location.host}/ws/events`

    try {
      ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log('WebSocket connected')
        wsConnected.value = true
        wsError.value = null
        reconnectAttempts = 0
      }

      ws.onmessage = (event) => {
        try {
          const data: WebSocketEvent = JSON.parse(event.data)
          handleWebSocketEvent(data)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        wsError.value = 'WebSocket connection error'
      }

      ws.onclose = () => {
        console.log('WebSocket disconnected')
        wsConnected.value = false

        // Attempt to reconnect
        if (reconnectAttempts < maxReconnectAttempts) {
          reconnectAttempts++
          console.log(`Attempting to reconnect (${reconnectAttempts}/${maxReconnectAttempts})...`)
          setTimeout(connectWebSocket, reconnectDelay)
        } else {
          wsError.value = 'Failed to connect to server after multiple attempts'
        }
      }
    } catch (error) {
      console.error('Failed to create WebSocket:', error)
      wsError.value = 'Failed to establish WebSocket connection'
    }
  }

  function disconnectWebSocket() {
    if (ws) {
      ws.close()
      ws = null
    }
    wsConnected.value = false
  }

  // WebSocket event handlers
  function handleWebSocketEvent(event: WebSocketEvent) {
    console.log('WebSocket event:', event)

    switch (event.type) {
      case 'agent_spawned':
        handleAgentSpawned(event.agent_id, event.role)
        break

      case 'message_sent':
        handleMessageSent(event.from, event.to, event.content)
        break

      case 'finding_detected':
        handleFindingDetected(event.session_id, event.finding)
        break

      case 'analysis_complete':
        handleAnalysisComplete(event.session_id, event.findings_count)
        break

      case 'analysis_started':
        handleAnalysisStarted(event.session_id, event.file_path)
        break

      case 'analysis_progress':
        handleAnalysisProgress(event.session_id, event.message)
        break

      case 'analysis_failed':
        handleAnalysisFailed(event.session_id, event.error)
        break
    }
  }

  function handleAgentSpawned(agentId: string, role: string) {
    const agent: Agent = {
      id: agentId,
      role,
      status: 'active',
      workspace: '',
      messageCount: 0,
      createdAt: new Date().toISOString()
    }
    agents.value.push(agent)

    // Add agent to current session
    if (currentSessionId.value) {
      const session = sessions.value.get(currentSessionId.value)
      if (session) {
        session.agents.push(agent)
      }
    }
  }

  function handleMessageSent(from: string, to: string, content: string) {
    const message: Message = {
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      fromAgent: from,
      toAgent: to,
      content: content.substring(0, 200),
      fullContent: content
    }
    messages.value.push(message)

    // Update agent message counts
    const agent = agents.value.find(a => a.id === from)
    if (agent) {
      agent.messageCount++
    }

    // Add message to current session
    if (currentSessionId.value) {
      const session = sessions.value.get(currentSessionId.value)
      if (session) {
        session.messages.push(message)
      }
    }
  }

  function handleFindingDetected(sessionId: string, finding: Finding) {
    findings.value.push(finding)

    // Update file findings
    const file = files.value.find(f => f.id === sessionId)
    if (file) {
      file.findings.push(finding)
    }

    // Update session
    const session = sessions.value.get(sessionId)
    if (session) {
      session.findings.push(finding)
    }
  }

  function handleAnalysisComplete(sessionId: string, findingsCount: number) {
    const file = files.value.find(f => f.id === sessionId)
    if (file) {
      file.status = 'complete'
      file.progress = 100
      file.completedAt = new Date().toISOString()
    }

    const session = sessions.value.get(sessionId)
    if (session) {
      session.status = 'completed'
    }
  }

  function handleAnalysisStarted(sessionId: string, filePath: string) {
    if (!filePath) {
      return
    }
    const filename = filePath.split('/').pop() || filePath

    // Create file entry
    const file: FileAnalysis = {
      id: sessionId,
      filename,
      filepath: filePath,
      status: 'analyzing',
      progress: 0,
      findings: [],
      startedAt: new Date().toISOString()
    }
    files.value.push(file)
    currentSessionId.value = sessionId

    // Create session entry
    const session: AnalysisSession = {
      id: sessionId,
      filePath: filePath,
      startedAt: new Date().toISOString(),
      status: 'running',
      agents: [],
      messages: [],
      findings: []
    }
    sessions.value.set(sessionId, session)
  }

  function handleAnalysisProgress(sessionId: string, message: string) {
    const file = files.value.find(f => f.id === sessionId)
    if (file && file.status === 'analyzing') {
      // Increment progress gradually
      file.progress = Math.min(file.progress + 10, 90)
    }
  }

  function handleAnalysisFailed(sessionId: string, error: string) {
    const file = files.value.find(f => f.id === sessionId)
    if (file) {
      file.status = 'failed'
      file.error = error
      file.completedAt = new Date().toISOString()
    }

    const session = sessions.value.get(sessionId)
    if (session) {
      session.status = 'failed'
    }
  }

  // Actions
  function selectFile(fileId: string) {
    currentSessionId.value = fileId
  }

  function addFile(file: FileAnalysis) {
    files.value.push(file)
  }

  function updateFileProgress(fileId: string, progress: number) {
    const file = files.value.find(f => f.id === fileId)
    if (file) {
      file.progress = progress
    }
  }

  function clearAll() {
    files.value = []
    agents.value = []
    messages.value = []
    findings.value = []
    sessions.value.clear()
    currentSessionId.value = null
  }

  async function uploadFile(file: File) {
    return await orchestratorApi.uploadFile(file)
  }

  async function startAnalysis(filePath: string, options?: { complexityThreshold?: number; maxParallelAgents?: number }) {
    return await orchestratorApi.startAnalysis(filePath, options)
  }

  return {
    // State
    files,
    agents,
    messages,
    findings,
    sessions,
    currentSessionId,
    orchestratorStatus,
    wsConnected,
    wsError,

    // Computed
    currentSession,
    findingsBySeverity,
    activeFiles,
    completedFiles,
    failedFiles,

    // Actions
    connectWebSocket,
    disconnectWebSocket,
    selectFile,
    addFile,
    updateFileProgress,
    clearAll,
    uploadFile,
    startAnalysis
  }
})
