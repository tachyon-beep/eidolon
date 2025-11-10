import axios from 'axios'
import type { OrchestratorStatus, Agent, Message, Finding } from '@/types'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export const orchestratorApi = {
  // Status
  async getStatus(): Promise<OrchestratorStatus> {
    const response = await api.get<OrchestratorStatus>('/status')
    return response.data
  },

  // Analysis
  async startAnalysis(filePath: string, options?: {
    complexityThreshold?: number
    maxParallelAgents?: number
  }): Promise<{ session_id: string; status: string }> {
    const response = await api.post('/analyze', {
      file_path: filePath,
      complexity_threshold: options?.complexityThreshold || 10,
      max_parallel_agents: options?.maxParallelAgents || 5
    })
    return response.data
  },

  async getSession(sessionId: string): Promise<any> {
    const response = await api.get(`/sessions/${sessionId}`)
    return response.data
  },

  // Agents
  async getAgents(): Promise<Agent[]> {
    const response = await api.get<Agent[]>('/agents')
    return response.data
  },

  // Messages
  async getMessages(options?: {
    sessionId?: string
    limit?: number
  }): Promise<Message[]> {
    const response = await api.get<Message[]>('/messages', {
      params: options
    })
    return response.data
  },

  // Findings
  async getFindings(sessionId?: string): Promise<Finding[]> {
    const response = await api.get<Finding[]>('/findings', {
      params: { session_id: sessionId }
    })
    return response.data
  },

  // File Upload
  async uploadFile(file: File): Promise<{
    file_path: string
    filename: string
    size: number
  }> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return response.data
  }
}

export default api
