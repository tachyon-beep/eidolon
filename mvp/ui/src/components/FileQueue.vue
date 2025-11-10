<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="p-4 border-b border-gray-200">
      <h2 class="text-lg font-semibold text-gray-900">File Queue</h2>
      <p class="text-sm text-gray-600 mt-1">
        {{ totalFiles }} file{{ totalFiles !== 1 ? 's' : '' }}
        <span v-if="activeCount > 0" class="text-status-analyzing">
          ({{ activeCount }} active)
        </span>
      </p>
    </div>

    <!-- Filter Tabs -->
    <div class="px-4 pt-3 pb-2 border-b border-gray-100">
      <div class="flex space-x-2" role="tablist">
        <button
          v-for="tab in tabs"
          :key="tab.value"
          :class="[
            'px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
            currentFilter === tab.value
              ? 'bg-primary text-white'
              : 'text-gray-600 hover:bg-gray-100'
          ]"
          :aria-selected="currentFilter === tab.value"
          role="tab"
          @click="currentFilter = tab.value"
        >
          {{ tab.label }} ({{ tab.count }})
        </button>
      </div>
    </div>

    <!-- File List -->
    <div class="flex-1 overflow-y-auto p-4 space-y-3" role="list">
      <div
        v-for="file in filteredFiles"
        :key="file.id"
        :class="[
          'card card-hover p-4 animate-slide-in',
          currentSessionId === file.id ? 'ring-2 ring-primary' : ''
        ]"
        role="listitem"
        tabindex="0"
        @click="selectFile(file.id)"
        @keydown.enter="selectFile(file.id)"
        @keydown.space.prevent="selectFile(file.id)"
      >
        <!-- File Header -->
        <div class="flex items-start justify-between mb-2">
          <div class="flex items-center space-x-2 flex-1 min-w-0">
            <span :class="['status-dot', file.status]" :aria-label="`Status: ${file.status}`" />
            <h3 class="font-medium text-gray-900 truncate" :title="file.filename">
              {{ file.filename }}
            </h3>
          </div>
          <span
            v-if="file.findings.length > 0"
            :class="[
              'badge',
              getWorstSeverityClass(file.findings)
            ]"
            :aria-label="`${file.findings.length} findings`"
          >
            {{ file.findings.length }}
          </span>
        </div>

        <!-- Progress Bar -->
        <div
          v-if="file.status === 'analyzing'"
          class="w-full bg-gray-200 rounded-full h-1.5 mb-2"
          role="progressbar"
          :aria-valuenow="file.progress"
          aria-valuemin="0"
          aria-valuemax="100"
        >
          <div
            class="bg-status-analyzing h-1.5 rounded-full transition-all duration-300"
            :style="{ width: `${file.progress}%` }"
          />
        </div>

        <!-- Findings Summary -->
        <div v-if="file.findings.length > 0" class="flex items-center space-x-3 text-xs">
          <span
            v-for="severity in severities"
            :key="severity"
            :class="['flex items-center space-x-1', getSeverityColor(severity)]"
          >
            <span :class="['severity-dot', severity]" :aria-label="`${severity} severity`" />
            <span>{{ getSeverityCount(file.findings, severity) }}</span>
          </span>
        </div>

        <!-- Timestamp -->
        <div class="text-xs text-gray-500 mt-2">
          <span v-if="file.startedAt">
            {{ formatTimestamp(file.startedAt) }}
          </span>
          <span v-if="file.error" class="text-red-600 ml-2">
            Error: {{ file.error }}
          </span>
        </div>
      </div>

      <!-- Empty State -->
      <div
        v-if="filteredFiles.length === 0"
        class="text-center py-12 text-gray-500"
      >
        <svg
          class="w-16 h-16 mx-auto mb-4 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        <p class="text-sm">No files {{ currentFilter === 'all' ? '' : currentFilter }}</p>
        <p class="text-xs mt-1">Upload a file to get started</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useOrchestrationStore } from '@/stores/orchestration'
import type { Finding, Severity } from '@/types'

const emit = defineEmits<{
  selectFile: [fileId: string]
}>()

const store = useOrchestrationStore()
const currentFilter = ref<'all' | 'analyzing' | 'complete' | 'failed'>('all')

const severities: Severity[] = ['critical', 'high', 'medium', 'low']

// Computed
const totalFiles = computed(() => store.files.length)
const activeCount = computed(() => store.activeFiles.length)
const currentSessionId = computed(() => store.currentSessionId)

const tabs = computed(() => [
  { label: 'All', value: 'all' as const, count: store.files.length },
  { label: 'Active', value: 'analyzing' as const, count: store.activeFiles.length },
  { label: 'Complete', value: 'complete' as const, count: store.completedFiles.length },
  { label: 'Failed', value: 'failed' as const, count: store.failedFiles.length }
])

const filteredFiles = computed(() => {
  if (currentFilter.value === 'all') {
    return store.files
  }
  return store.files.filter(f => f.status === currentFilter.value)
})

// Methods
function selectFile(fileId: string) {
  emit('selectFile', fileId)
}

function getSeverityCount(findings: Finding[], severity: Severity): number {
  return findings.filter(f => f.severity === severity).length
}

function getWorstSeverityClass(findings: Finding[]): string {
  if (findings.some(f => f.severity === 'critical')) return 'badge-critical'
  if (findings.some(f => f.severity === 'high')) return 'badge-high'
  if (findings.some(f => f.severity === 'medium')) return 'badge-medium'
  return 'badge-low'
}

function getSeverityColor(severity: Severity): string {
  const colors = {
    critical: 'text-severity-critical',
    high: 'text-severity-high',
    medium: 'text-severity-medium',
    low: 'text-severity-low'
  }
  return colors[severity]
}

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`

  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h ago`

  return date.toLocaleDateString()
}
</script>
