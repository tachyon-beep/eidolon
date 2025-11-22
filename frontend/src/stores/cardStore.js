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
      }
      return response.data
    } catch (error) {
      console.error('Error updating card:', error)
      return null
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
        }
        break
      case 'card_deleted':
        cards.value = cards.value.filter(c => c.id !== message.data.id)
        break
      case 'analysis_started':
        isAnalyzing.value = true
        analysisProgress.value = null
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

    // Actions
    fetchCards,
    fetchAgents,
    getCard,
    getAgent,
    getAgentHierarchy,
    updateCard,
    routeCard,
    applyFix,
    analyzeCodebase,
    selectCard,
    clearSelection,
    fetchCacheStats,
    clearCache,
    handleWebSocketMessage
  }
})
