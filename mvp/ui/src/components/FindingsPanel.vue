<template>
  <div class="flex flex-col h-full">
    <!-- Header (always visible) -->
    <div
      class="flex items-center justify-between px-6 py-3 border-b border-gray-200 cursor-pointer hover:bg-gray-50"
      @click="$emit('toggle')"
      @keydown.enter="$emit('toggle')"
      @keydown.space.prevent="$emit('toggle')"
      tabindex="0"
      role="button"
      :aria-expanded="expanded"
      aria-controls="findings-content"
    >
      <div class="flex items-center space-x-4">
        <h3 class="text-lg font-semibold text-gray-900">
          Findings ({{ totalFindings }})
        </h3>

        <!-- Severity Summary -->
        <div class="flex items-center space-x-4 text-sm">
          <div
            v-for="severity in severities"
            :key="severity"
            class="flex items-center space-x-1.5"
          >
            <span :class="['severity-dot', severity]" :aria-label="`${severity} severity`" />
            <span :class="['font-medium', getSeverityColor(severity)]">
              {{ severity.charAt(0).toUpperCase() + severity.slice(1) }}
            </span>
            <span class="text-gray-600">
              ({{ findingsBySeverity[severity].length }})
            </span>
          </div>
        </div>
      </div>

      <!-- Toggle Icon -->
      <svg
        :class="[
          'w-5 h-5 text-gray-600 transition-transform duration-200',
          expanded ? 'rotate-180' : ''
        ]"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M19 9l-7 7-7-7"
        />
      </svg>
    </div>

    <!-- Content (collapsible) -->
    <div
      v-if="expanded"
      id="findings-content"
      class="flex-1 overflow-y-auto p-6"
      role="region"
      aria-label="Findings details"
    >
      <div v-if="totalFindings === 0" class="text-center py-12 text-gray-500">
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
            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <p class="text-lg font-medium mb-1">No findings yet</p>
        <p class="text-sm">Start analyzing files to see findings here</p>
      </div>

      <div v-else class="space-y-6">
        <!-- Group by Severity -->
        <div
          v-for="severity in severities"
          :key="severity"
          v-show="findingsBySeverity[severity].length > 0"
        >
          <!-- Severity Header -->
          <button
            :class="[
              'w-full flex items-center justify-between p-3 rounded-lg mb-3',
              getSeverityBgClass(severity)
            ]"
            @click="toggleSeverity(severity)"
            :aria-expanded="expandedSeverities.has(severity)"
            :aria-controls="`findings-${severity}`"
          >
            <div class="flex items-center space-x-3">
              <span :class="['severity-dot', severity]" />
              <span :class="['font-semibold text-sm uppercase', getSeverityColor(severity)]">
                {{ severity }}
              </span>
              <span :class="['text-sm', getSeverityColor(severity)]">
                ({{ findingsBySeverity[severity].length }})
              </span>
            </div>
            <svg
              :class="[
                'w-5 h-5 transition-transform duration-200',
                getSeverityColor(severity),
                expandedSeverities.has(severity) ? 'rotate-180' : ''
              ]"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </button>

          <!-- Findings List -->
          <div
            v-show="expandedSeverities.has(severity)"
            :id="`findings-${severity}`"
            class="space-y-3"
          >
            <div
              v-for="finding in findingsBySeverity[severity]"
              :key="finding.id"
              :class="[
                'card border-l-4 p-4',
                getSeverityBorderClass(severity)
              ]"
              role="article"
              :aria-label="`${severity} finding`"
            >
              <!-- Finding Header -->
              <div class="flex items-start justify-between mb-2">
                <div class="flex-1">
                  <div class="flex items-center space-x-2 mb-1">
                    <span
                      :class="[
                        'badge text-xs',
                        getTypeBadgeClass(finding.type)
                      ]"
                    >
                      {{ finding.type }}
                    </span>
                    <span
                      v-if="finding.function_name"
                      class="text-xs text-gray-600"
                    >
                      in {{ finding.function_name }}()
                    </span>
                  </div>
                  <p class="text-sm font-medium text-gray-900">
                    {{ finding.description }}
                  </p>
                </div>
                <button
                  class="text-gray-400 hover:text-gray-600 ml-2"
                  @click="toggleFindingExpansion(finding.id)"
                  :aria-expanded="expandedFindings.has(finding.id)"
                  :aria-label="expandedFindings.has(finding.id) ? 'Collapse details' : 'Expand details'"
                >
                  <svg
                    class="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      :d="expandedFindings.has(finding.id)
                        ? 'M5 15l7-7 7 7'
                        : 'M19 9l-7 7-7-7'"
                    />
                  </svg>
                </button>
              </div>

              <!-- Finding Details -->
              <div class="text-xs text-gray-600 space-y-1">
                <div class="flex items-center space-x-4">
                  <span class="flex items-center space-x-1">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                      />
                    </svg>
                    <span>{{ finding.file_path.split('/').pop() }}</span>
                  </span>
                  <span v-if="finding.line_number" class="flex items-center space-x-1">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14"
                      />
                    </svg>
                    <span>Line {{ finding.line_number }}</span>
                  </span>
                  <span class="flex items-center space-x-1">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                      />
                    </svg>
                    <span>{{ finding.agent_id }}</span>
                  </span>
                </div>
              </div>

              <!-- Expanded Details -->
              <div
                v-if="expandedFindings.has(finding.id)"
                class="mt-3 pt-3 border-t border-gray-200"
              >
                <div v-if="finding.suggested_fix" class="mb-3">
                  <p class="text-xs font-semibold text-gray-700 mb-1">Suggested Fix:</p>
                  <div class="bg-gray-50 p-3 rounded text-xs text-gray-800 font-mono">
                    {{ finding.suggested_fix }}
                  </div>
                </div>

                <div v-if="finding.complexity" class="mb-3">
                  <p class="text-xs font-semibold text-gray-700 mb-1">Complexity:</p>
                  <div class="flex items-center space-x-2">
                    <div class="flex-1 bg-gray-200 rounded-full h-2">
                      <div
                        :class="[
                          'h-2 rounded-full transition-all duration-300',
                          finding.complexity > 15 ? 'bg-red-500' :
                          finding.complexity > 10 ? 'bg-yellow-500' :
                          'bg-green-500'
                        ]"
                        :style="{ width: `${Math.min(finding.complexity * 5, 100)}%` }"
                      />
                    </div>
                    <span class="text-xs font-medium">{{ finding.complexity }}</span>
                  </div>
                </div>

                <div class="flex space-x-2">
                  <button class="btn-secondary text-xs py-1 px-3">
                    View in Editor
                  </button>
                  <button class="btn-secondary text-xs py-1 px-3">
                    Apply Fix
                  </button>
                  <button class="btn-secondary text-xs py-1 px-3">
                    Dismiss
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useOrchestrationStore } from '@/stores/orchestration'
import type { Severity, FindingType } from '@/types'

defineProps<{
  expanded: boolean
}>()

defineEmits<{
  toggle: []
}>()

const store = useOrchestrationStore()
const expandedSeverities = ref(new Set<Severity>(['critical', 'high']))
const expandedFindings = ref(new Set<string>())

const severities: Severity[] = ['critical', 'high', 'medium', 'low']

// Computed
const totalFindings = computed(() => store.findings.length)
const findingsBySeverity = computed(() => store.findingsBySeverity)

// Methods
function toggleSeverity(severity: Severity) {
  if (expandedSeverities.value.has(severity)) {
    expandedSeverities.value.delete(severity)
  } else {
    expandedSeverities.value.add(severity)
  }
}

function toggleFindingExpansion(findingId: string) {
  if (expandedFindings.value.has(findingId)) {
    expandedFindings.value.delete(findingId)
  } else {
    expandedFindings.value.add(findingId)
  }
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

function getSeverityBgClass(severity: Severity): string {
  const classes = {
    critical: 'bg-bg-critical hover:bg-red-200',
    high: 'bg-bg-high hover:bg-yellow-200',
    medium: 'bg-bg-medium hover:bg-green-200',
    low: 'bg-bg-low hover:bg-blue-200'
  }
  return classes[severity]
}

function getSeverityBorderClass(severity: Severity): string {
  const classes = {
    critical: 'border-severity-critical',
    high: 'border-severity-high',
    medium: 'border-severity-medium',
    low: 'border-severity-low'
  }
  return classes[severity]
}

function getTypeBadgeClass(type: FindingType): string {
  const classes = {
    bug: 'bg-red-100 text-red-800',
    security: 'bg-purple-100 text-purple-800',
    performance: 'bg-yellow-100 text-yellow-800',
    style: 'bg-blue-100 text-blue-800',
    complexity: 'bg-orange-100 text-orange-800'
  }
  return classes[type]
}
</script>
