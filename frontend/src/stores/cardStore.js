import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'

const API_BASE = '/api'

export const useCardStore = defineStore('cards', () => {
  // State
  const cards = ref([])
  const agents = ref([])
  const selectedCard = ref(null)
  const selectedAgent = ref(null)
  const isAnalyzing = ref(false)
  const analysisProgress = ref(null)
  const cacheStats = ref(null)
  const recentActivities = ref([])  // Recent activity log

  // Actions
  async function fetchCards(filters = {}) {
    try {
      const params = new URLSearchParams(filters)
      const response = await axios.get(`${API_BASE}/cards?${params}`)
      cards.value = response.data
    } catch (error) {
      console.error('Error fetching cards:', error)
    }
  }

  async function fetchAgents() {
    try {
      const response = await axios.get(`${API_BASE}/agents`)
      agents.value = response.data
    } catch (error) {
      console.error('Error fetching agents:', error)
    }
  }

  async function getCard(cardId) {
    try {
      const response = await axios.get(`${API_BASE}/cards/${cardId}`)
      return response.data
    } catch (error) {
      console.error('Error fetching card:', error)
      return null
    }
  }

  async function getAgent(agentId) {
    try {
      const response = await axios.get(`${API_BASE}/agents/${agentId}`)
      selectedAgent.value = response.data
      return response.data
    } catch (error) {
      console.error('Error fetching agent:', error)
      return null
    }
  }

  async function getAgentHierarchy(agentId) {
    try {
      const response = await axios.get(`${API_BASE}/agents/${agentId}/hierarchy`)
      return response.data
    } catch (error) {
      console.error('Error fetching agent hierarchy:', error)
      return null
    }
  }

  async function updateCard(cardId, updates) {
    try {
      const response = await axios.put(`${API_BASE}/cards/${cardId}`, updates)
      // Update local state
      const index = cards.value.findIndex(c => c.id === cardId)
      if (index !== -1) {
        cards.value[index] = response.data
      } else {
        cards.value.push(response.data)
      }
      return response.data
    } catch (error) {
      console.error('Error updating card:', error)
      return null
    }
  }

  async function createCard(payload) {
    try {
      const response = await axios.post(`${API_BASE}/cards`, payload)
      cards.value.push(response.data)
      return response.data
    } catch (error) {
      console.error('Error creating card:', error)
      throw error
    }
  }

  async function routeCard(cardId, fromTab, toTab) {
    return await updateCard(cardId, {
      routing: { from_tab: fromTab, to_tab: toTab }
    })
  }

  async function applyFix(cardId) {
    try {
      const response = await axios.post(`${API_BASE}/cards/${cardId}/apply-fix`)
      // Refresh the card to get updated status
      await fetchCards()
      return response.data
    } catch (error) {
      console.error('Error applying fix:', error)
      throw error
    }
  }

  async function reviewCard(cardId, options) {
    try {
      const response = await axios.post(`${API_BASE}/cards/${cardId}/review`, options)
      await fetchCards()
      return response.data
    } catch (error) {
      console.error('Error reviewing card:', error)
      throw error
    }
  }

  async function generateBAProject(payload) {
    try {
      const response = await axios.post(`${API_BASE}/ba/projects`, payload)
      return response.data.cards || []
    } catch (error) {
      let detail = error?.response?.data?.detail
      if (detail && typeof detail !== 'string') {
        try {
          detail = JSON.stringify(detail)
        } catch {
          detail = String(detail)
        }
      }
      detail = detail || error.message
      console.error('Error generating BA project cards:', detail)
      throw new Error(detail)
    }
  }

  async function analyzeCodebase(path) {
    try {
      isAnalyzing.value = true
      const response = await axios.post(`${API_BASE}/analyze`, { path })
      await fetchCards()
      await fetchAgents()
      return response.data
    } catch (error) {
      console.error('Error analyzing codebase:', error)
      throw error
    } finally {
      isAnalyzing.value = false
    }
  }

  function selectCard(card) {
    selectedCard.value = card
  }

  function clearSelection() {
    selectedCard.value = null
    selectedAgent.value = null
  }

  async function fetchCacheStats() {
    try {
      const response = await axios.get(`${API_BASE}/cache/stats`)
      cacheStats.value = response.data
    } catch (error) {
      console.error('Error fetching cache stats:', error)
    }
  }

  async function clearCache() {
    try {
      const response = await axios.delete(`${API_BASE}/cache`)
      await fetchCacheStats()
      return response.data
    } catch (error) {
      console.error('Error clearing cache:', error)
      throw error
    }
  }

  function handleWebSocketMessage(message) {
    switch (message.type) {
      case 'card_updated':
        const index = cards.value.findIndex(c => c.id === message.data.id)
        if (index !== -1) {
          cards.value[index] = message.data
        } else {
          cards.value.push(message.data)
        }
        break
      case 'card_deleted':
        cards.value = cards.value.filter(c => c.id !== message.data.id)
        break
      case 'analysis_started':
        isAnalyzing.value = true
        analysisProgress.value = null
        recentActivities.value = []  // Clear old activities
        break
      case 'activity_update':
        // Add new activity to the front of the list
        recentActivities.value.unshift(message.data)
        // Keep only last 20 activities
        if (recentActivities.value.length > 20) {
          recentActivities.value.pop()
        }
        break
      case 'analysis_progress':
        analysisProgress.value = message.data
        break
      case 'analysis_completed':
        isAnalyzing.value = false
        analysisProgress.value = null
        fetchCards()
        fetchAgents()
        break
      case 'analysis_error':
        isAnalyzing.value = false
        analysisProgress.value = null
        console.error('Analysis error:', message.data.error)
        break
      case 'cache_cleared':
        fetchCacheStats()
        break
    }
  }

  return {
    // State
    cards,
    agents,
    selectedCard,
    selectedAgent,
    isAnalyzing,
    analysisProgress,
    cacheStats,
    recentActivities,

    // Actions
    fetchCards,
    fetchAgents,
    getCard,
    getAgent,
    getAgentHierarchy,
    updateCard,
    createCard,
    routeCard,
    applyFix,
    reviewCard,
    analyzeCodebase,
    selectCard,
    clearSelection,
    fetchCacheStats,
    clearCache,
    handleWebSocketMessage,
    generateBAProject
  }
})
