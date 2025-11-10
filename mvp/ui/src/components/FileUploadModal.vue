<template>
  <div
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
    @click.self="$emit('close')"
    role="dialog"
    aria-modal="true"
    aria-labelledby="upload-modal-title"
  >
    <div class="bg-white rounded-lg shadow-xl max-w-2xl w-full animate-fade-in">
      <!-- Header -->
      <div class="flex items-center justify-between p-6 border-b border-gray-200">
        <h2 id="upload-modal-title" class="text-2xl font-bold text-gray-900">
          Upload File for Analysis
        </h2>
        <button
          class="text-gray-400 hover:text-gray-600 transition-colors"
          @click="$emit('close')"
          aria-label="Close modal"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      <!-- Body -->
      <div class="p-6">
        <!-- Drag and Drop Zone -->
        <div
          :class="[
            'border-2 border-dashed rounded-lg p-12 text-center transition-colors',
            isDragging
              ? 'border-primary bg-purple-50'
              : 'border-gray-300 hover:border-gray-400'
          ]"
          @dragover.prevent="isDragging = true"
          @dragleave.prevent="isDragging = false"
          @drop.prevent="handleDrop"
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
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
          <p class="text-lg font-medium text-gray-900 mb-2">
            Drag and drop your Python file here
          </p>
          <p class="text-sm text-gray-600 mb-4">or</p>
          <label
            class="btn-primary cursor-pointer inline-block"
            for="file-input"
          >
            Browse Files
          </label>
          <input
            id="file-input"
            type="file"
            accept=".py"
            class="hidden"
            @change="handleFileSelect"
            aria-label="Select file"
          />
        </div>

        <!-- Selected File Info -->
        <div v-if="selectedFile" class="mt-6">
          <div class="card p-4 flex items-center justify-between">
            <div class="flex items-center space-x-3">
              <svg class="w-8 h-8 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              <div>
                <p class="font-medium text-gray-900">{{ selectedFile.name }}</p>
                <p class="text-sm text-gray-600">{{ formatFileSize(selectedFile.size) }}</p>
              </div>
            </div>
            <button
              class="text-gray-400 hover:text-red-600 transition-colors"
              @click="selectedFile = null"
              aria-label="Remove file"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        </div>

        <!-- Configuration -->
        <div v-if="selectedFile" class="mt-6 space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Complexity Threshold
            </label>
            <input
              v-model.number="config.complexityThreshold"
              type="range"
              min="5"
              max="20"
              step="1"
              class="w-full"
              aria-label="Complexity threshold"
            />
            <div class="flex justify-between text-xs text-gray-600 mt-1">
              <span>5 (Strict)</span>
              <span class="font-medium">{{ config.complexityThreshold }}</span>
              <span>20 (Lenient)</span>
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Max Parallel Agents
            </label>
            <select
              v-model.number="config.maxParallelAgents"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
              aria-label="Max parallel agents"
            >
              <option :value="3">3 agents</option>
              <option :value="5">5 agents (recommended)</option>
              <option :value="8">8 agents</option>
              <option :value="10">10 agents</option>
            </select>
          </div>
        </div>

        <!-- Error Message -->
        <div
          v-if="errorMessage"
          class="mt-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg"
          role="alert"
        >
          {{ errorMessage }}
        </div>

        <!-- Upload Progress -->
        <div v-if="uploading" class="mt-6">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-medium text-gray-700">Uploading...</span>
            <span class="text-sm text-gray-600">{{ uploadProgress }}%</span>
          </div>
          <div class="w-full bg-gray-200 rounded-full h-2">
            <div
              class="bg-primary h-2 rounded-full transition-all duration-300"
              :style="{ width: `${uploadProgress}%` }"
              role="progressbar"
              :aria-valuenow="uploadProgress"
              aria-valuemin="0"
              aria-valuemax="100"
            />
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="flex items-center justify-end space-x-3 p-6 border-t border-gray-200">
        <button
          class="btn-secondary"
          @click="$emit('close')"
          :disabled="uploading"
        >
          Cancel
        </button>
        <button
          class="btn-primary"
          @click="handleUpload"
          :disabled="!selectedFile || uploading"
        >
          {{ uploading ? 'Uploading...' : 'Start Analysis' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import axios from 'axios'

const emit = defineEmits<{
  close: []
  upload: [file: File]
}>()

// State
const isDragging = ref(false)
const selectedFile = ref<File | null>(null)
const uploading = ref(false)
const uploadProgress = ref(0)
const errorMessage = ref<string | null>(null)
const config = ref({
  complexityThreshold: 10,
  maxParallelAgents: 5
})

// Methods
function handleDrop(event: DragEvent) {
  isDragging.value = false
  const files = event.dataTransfer?.files

  if (files && files.length > 0) {
    const file = files[0]
    if (file.name.endsWith('.py')) {
      selectedFile.value = file
      errorMessage.value = null
    } else {
      errorMessage.value = 'Please select a Python (.py) file'
    }
  }
}

function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  const files = target.files

  if (files && files.length > 0) {
    const file = files[0]
    if (file.name.endsWith('.py')) {
      selectedFile.value = file
      errorMessage.value = null
    } else {
      errorMessage.value = 'Please select a Python (.py) file'
    }
  }
}

async function handleUpload() {
  if (!selectedFile.value) return

  uploading.value = true
  uploadProgress.value = 0
  errorMessage.value = null

  try {
    // Upload file
    const formData = new FormData()
    formData.append('file', selectedFile.value)

    const uploadResponse = await axios.post('/api/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total) {
          uploadProgress.value = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          )
        }
      }
    })

    // Start analysis
    const analyzeResponse = await axios.post('/api/analyze', {
      file_path: uploadResponse.data.file_path,
      complexity_threshold: config.value.complexityThreshold,
      max_parallel_agents: config.value.maxParallelAgents
    })

    console.log('Analysis started:', analyzeResponse.data)

    emit('upload', selectedFile.value)

    // Close modal after short delay to show success
    setTimeout(() => {
      emit('close')
    }, 500)
  } catch (error: any) {
    console.error('Upload error:', error)
    errorMessage.value = error.response?.data?.error || 'Failed to upload file'
  } finally {
    uploading.value = false
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
</script>
