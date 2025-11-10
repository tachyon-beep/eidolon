<template>
  <div class="h-full flex flex-col">
    <!-- Header -->
    <div v-if="session" class="mb-6">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h2 class="text-2xl font-bold text-gray-900">
            {{ session.filePath.split('/').pop() }}
          </h2>
          <p class="text-sm text-gray-600 mt-1">
            Started {{ formatTimestamp(session.startedAt) }}
          </p>
        </div>
        <div class="flex items-center space-x-4">
          <div class="text-right">
            <p class="text-sm text-gray-600">Status</p>
            <p :class="['text-lg font-semibold', getStatusColor(session.status)]">
              {{ session.status.toUpperCase() }}
            </p>
          </div>
          <div class="text-right">
            <p class="text-sm text-gray-600">Agents</p>
            <p class="text-lg font-semibold text-gray-900">
              {{ agents.length }}
            </p>
          </div>
          <div class="text-right">
            <p class="text-sm text-gray-600">Messages</p>
            <p class="text-lg font-semibold text-gray-900">
              {{ messages.length }}
            </p>
          </div>
        </div>
      </div>

      <!-- Module Override Alert -->
      <div
        v-if="session.moduleOverride"
        class="card border-l-4 border-severity-high bg-bg-high p-4 mb-6"
        role="alert"
      >
        <div class="flex items-start">
          <svg
            class="w-5 h-5 text-severity-high mr-3 mt-0.5"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fill-rule="evenodd"
              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
              clip-rule="evenodd"
            />
          </svg>
          <div class="flex-1">
            <h3 class="text-sm font-semibold text-gray-900 mb-1">
              Module Override
            </h3>
            <p class="text-sm text-gray-700 mb-2">
              {{ session.moduleOverride.reason }}
            </p>
            <div class="flex items-center space-x-4 text-xs">
              <div>
                <span class="text-gray-600">Module Assessment:</span>
                <span :class="['ml-1 font-semibold', getSeverityTextColor(session.moduleOverride.moduleAssessment)]">
                  {{ session.moduleOverride.moduleAssessment.toUpperCase() }}
                </span>
              </div>
              <div>
                <span class="text-gray-600">Overridden Functions:</span>
                <span class="ml-1 font-semibold">
                  {{ session.moduleOverride.overriddenFunctions.length }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Content Grid -->
    <div class="flex-1 grid grid-cols-2 gap-6 overflow-auto">
      <!-- Agent Flow -->
      <div class="card p-6">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">Agent Flow</h3>

        <div v-if="agents.length === 0" class="text-center py-12 text-gray-500">
          <svg
            class="w-12 h-12 mx-auto mb-4 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
            />
          </svg>
          <p class="text-sm">No agents spawned yet</p>
        </div>

        <div v-else class="space-y-3">
          <div
            v-for="agent in agents"
            :key="agent.id"
            :class="[
              'card border-l-4 p-4',
              getAgentBorderColor(agent.status)
            ]"
            role="article"
            :aria-label="`Agent ${agent.role}`"
          >
            <div class="flex items-start justify-between mb-2">
              <div class="flex items-center space-x-2">
                <span class="text-2xl">🤖</span>
                <div>
                  <h4 class="font-semibold text-gray-900">{{ agent.role }}</h4>
                  <p class="text-xs text-gray-600">{{ agent.id }}</p>
                </div>
              </div>
              <span
                :class="[
                  'badge',
                  agent.status === 'active' ? 'bg-green-100 text-green-800' :
                  agent.status === 'completed' ? 'bg-gray-100 text-gray-800' :
                  agent.status === 'failed' ? 'bg-red-100 text-red-800' :
                  'bg-yellow-100 text-yellow-800'
                ]"
              >
                {{ agent.status }}
              </span>
            </div>
            <div class="text-sm text-gray-600">
              <p>Messages: {{ agent.messageCount }}</p>
              <p class="text-xs mt-1">{{ formatTimestamp(agent.createdAt) }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Message Feed -->
      <div class="card p-6 flex flex-col">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">Message Feed</h3>

        <div v-if="messages.length === 0" class="flex-1 flex items-center justify-center text-gray-500">
          <div class="text-center">
            <svg
              class="w-12 h-12 mx-auto mb-4 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
              />
            </svg>
            <p class="text-sm">No messages yet</p>
          </div>
        </div>

        <div v-else class="flex-1 overflow-y-auto space-y-3">
          <div
            v-for="message in messages"
            :key="message.id"
            class="border-l-4 border-primary bg-gray-50 p-3 rounded"
            role="article"
          >
            <div class="flex items-center justify-between mb-2">
              <div class="flex items-center space-x-2 text-sm">
                <span class="font-semibold text-gray-900">{{ message.fromAgent }}</span>
                <svg class="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fill-rule="evenodd"
                    d="M12.293 5.293a1 1 0 011.414 0l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-2.293-2.293a1 1 0 010-1.414z"
                    clip-rule="evenodd"
                  />
                </svg>
                <span class="text-gray-600">{{ message.toAgent }}</span>
              </div>
              <span class="text-xs text-gray-500">
                {{ formatTime(message.timestamp) }}
              </span>
            </div>
            <p class="text-sm text-gray-700 line-clamp-2">{{ message.content }}</p>
            <button
              v-if="message.content !== message.fullContent"
              class="text-xs text-primary hover:text-purple-700 mt-1"
              @click="expandMessage(message.id)"
            >
              Show more
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div
      v-if="!session"
      class="flex items-center justify-center h-full text-gray-500"
    >
      <div class="text-center">
        <svg
          class="w-20 h-20 mx-auto mb-4 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
          />
        </svg>
        <p class="text-lg font-medium mb-2">No file selected</p>
        <p class="text-sm">Select a file from the queue to view orchestration details</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useOrchestrationStore } from '@/stores/orchestration'
import type { Severity } from '@/types'

const props = defineProps<{
  sessionId: string | null
}>()

const store = useOrchestrationStore()

// Computed
const session = computed(() => {
  if (!props.sessionId) return null
  return store.sessions.get(props.sessionId) || null
})

const agents = computed(() => store.agents)
const messages = computed(() => store.messages)

// Methods
function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`

  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h ago`

  return date.toLocaleDateString()
}

function formatTime(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString()
}

function getStatusColor(status: string): string {
  const colors = {
    running: 'text-status-analyzing',
    completed: 'text-status-complete',
    failed: 'text-status-failed'
  }
  return colors[status as keyof typeof colors] || 'text-gray-600'
}

function getAgentBorderColor(status: string): string {
  const colors = {
    active: 'border-green-500',
    completed: 'border-gray-400',
    failed: 'border-red-500',
    spawning: 'border-yellow-500'
  }
  return colors[status as keyof typeof colors] || 'border-gray-300'
}

function getSeverityTextColor(severity: Severity): string {
  const colors = {
    critical: 'text-severity-critical',
    high: 'text-severity-high',
    medium: 'text-severity-medium',
    low: 'text-severity-low'
  }
  return colors[severity]
}

function expandMessage(messageId: string) {
  // TODO: Implement message expansion modal
  console.log('Expand message:', messageId)
}
</script>
