<template>
  <div class="h-screen flex flex-col bg-gray-50">
    <!-- Header -->
    <header class="bg-white border-b border-gray-200 shadow-sm">
      <div class="px-6 py-4 flex items-center justify-between">
        <div class="flex items-center space-x-4">
          <h1 class="text-2xl font-bold text-primary">Eidolon Orchestrator</h1>
          <div class="flex items-center space-x-2">
            <span
              :class="[
                'w-2 h-2 rounded-full',
                wsConnected ? 'bg-green-500' : 'bg-red-500'
              ]"
              :aria-label="wsConnected ? 'Connected' : 'Disconnected'"
            />
            <span class="text-sm text-gray-600">
              {{ wsConnected ? 'Connected' : 'Disconnected' }}
            </span>
          </div>
        </div>

        <div class="flex items-center space-x-4">
          <!-- Status Badge -->
          <div class="flex items-center space-x-2 text-sm">
            <span class="text-gray-600">Status:</span>
            <span
              :class="[
                'badge',
                orchestratorStatus.status === 'running'
                  ? 'bg-green-100 text-green-800'
                  : 'bg-gray-100 text-gray-800'
              ]"
            >
              {{ orchestratorStatus.status }}
            </span>
          </div>

          <!-- Actions -->
          <button
            class="btn-secondary text-sm"
            @click="handleClearAll"
            :aria-label="'Clear all data'"
          >
            Clear All
          </button>
          <button
            class="btn-primary text-sm"
            @click="showUploadModal = true"
            :aria-label="'Upload file for analysis'"
          >
            Upload File
          </button>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <div class="flex-1 flex overflow-hidden">
      <!-- Left Sidebar: File Queue -->
      <aside
        class="w-80 bg-white border-r border-gray-200 flex flex-col"
        role="complementary"
        aria-label="File queue"
      >
        <FileQueue @select-file="handleSelectFile" />
      </aside>

      <!-- Main Panel: Orchestration View -->
      <main class="flex-1 flex flex-col overflow-hidden" role="main">
        <!-- Orchestration Visualization -->
        <div class="flex-1 overflow-auto p-6">
          <OrchestrationView :session-id="currentSessionId" />
        </div>

        <!-- Bottom Panel: Findings -->
        <div
          :class="[
            'border-t border-gray-200 bg-white transition-all duration-300',
            findingsPanelExpanded ? 'h-80' : 'h-14'
          ]"
          role="region"
          aria-label="Findings panel"
        >
          <FindingsPanel
            :expanded="findingsPanelExpanded"
            @toggle="findingsPanelExpanded = !findingsPanelExpanded"
          />
        </div>
      </main>
    </div>

    <!-- Upload Modal -->
    <FileUploadModal
      v-if="showUploadModal"
      @close="showUploadModal = false"
      @upload="handleFileUpload"
    />

    <!-- Error Toast -->
    <div
      v-if="wsError"
      class="fixed bottom-4 right-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg shadow-lg"
      role="alert"
      aria-live="polite"
    >
      <div class="flex items-center space-x-2">
        <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path
            fill-rule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
            clip-rule="evenodd"
          />
        </svg>
        <span class="font-medium">{{ wsError }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useOrchestrationStore } from '@/stores/orchestration'
import FileQueue from '@/components/FileQueue.vue'
import OrchestrationView from '@/components/OrchestrationView.vue'
import FindingsPanel from '@/components/FindingsPanel.vue'
import FileUploadModal from '@/components/FileUploadModal.vue'

const store = useOrchestrationStore()

// Reactive state
const findingsPanelExpanded = ref(true)
const showUploadModal = ref(false)

// Computed
const wsConnected = computed(() => store.wsConnected)
const wsError = computed(() => store.wsError)
const orchestratorStatus = computed(() => store.orchestratorStatus)
const currentSessionId = computed(() => store.currentSessionId)

// Lifecycle
onMounted(() => {
  store.connectWebSocket()
})

onUnmounted(() => {
  store.disconnectWebSocket()
})

// Methods
function handleSelectFile(fileId: string) {
  store.selectFile(fileId)
}

function handleClearAll() {
  if (confirm('Are you sure you want to clear all data?')) {
    store.clearAll()
  }
}

async function handleFileUpload(file: File, options?: { complexityThreshold: number; maxParallelAgents: number }) {
  // Modal handles upload/analysis directly, this is just for cleanup
  // Analysis is already started by the modal via axios
  console.log('File upload completed:', file.name)

  try {
    // Modal already closed itself, nothing to do here
  } catch (error) {
    console.error('Failed to upload and analyze file:', error)
    // Error will be shown via wsError in the store if WebSocket fails
  }
}
</script>
