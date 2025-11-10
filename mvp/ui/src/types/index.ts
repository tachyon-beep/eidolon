export type Severity = 'critical' | 'high' | 'medium' | 'low'
export type FileStatus = 'queued' | 'analyzing' | 'complete' | 'failed'
export type AgentStatus = 'spawning' | 'active' | 'completed' | 'failed'
export type FindingType = 'bug' | 'security' | 'performance' | 'style' | 'complexity'

export interface FileAnalysis {
  id: string
  filename: string
  filepath: string
  status: FileStatus
  progress: number
  findings: Finding[]
  startedAt?: string
  completedAt?: string
  error?: string
}

export interface Agent {
  id: string
  role: string
  status: AgentStatus
  workspace: string
  messageCount: number
  createdAt: string
}

export interface Message {
  id: string
  timestamp: string
  fromAgent: string
  toAgent: string
  content: string
  fullContent: string
  type?: 'task' | 'result' | 'error'
}

export interface Finding {
  id: string
  severity: Severity
  type: FindingType
  description: string
  file_path: string
  line_number?: number
  suggested_fix?: string
  agent_id: string
  function_name?: string
  complexity?: number
}

export interface ModuleOverride {
  moduleAssessment: Severity
  functionAssessments: Record<string, Severity>
  reason: string
  overriddenFunctions: string[]
}

export interface AnalysisSession {
  id: string
  filePath: string
  startedAt: string
  status: 'running' | 'completed' | 'failed'
  agents: Agent[]
  messages: Message[]
  findings: Finding[]
  moduleOverride?: ModuleOverride
}

export type WebSocketEvent =
  | { type: 'agent_spawned'; agent_id: string; role: string }
  | { type: 'message_sent'; from: string; to: string; content: string }
  | { type: 'finding_detected'; session_id: string; finding: Finding }
  | { type: 'analysis_complete'; session_id: string; findings_count: number }
  | { type: 'analysis_started'; session_id: string; file_path: string }
  | { type: 'analysis_progress'; session_id: string; message: string }
  | { type: 'analysis_failed'; session_id: string; error: string }

export interface OrchestratorStatus {
  status: 'idle' | 'running'
  activeSessions: number
  workspace: string
}
