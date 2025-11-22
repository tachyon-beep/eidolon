<template>
  <div class="agent-tree">
    <div v-if="hierarchy" class="tree-node">
      <TreeNode :node="hierarchy" />
    </div>
    <div v-else class="loading">Loading hierarchy...</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useCardStore } from '../stores/cardStore'
import TreeNode from './TreeNode.vue'

const props = defineProps({
  agentId: {
    type: String,
    required: true
  }
})

const cardStore = useCardStore()
const hierarchy = ref(null)

onMounted(async () => {
  hierarchy.value = await cardStore.getAgentHierarchy(props.agentId)
})
</script>

<style scoped>
.agent-tree {
  padding: 12px;
  background: #1a1a1a;
  border-radius: 6px;
}

.loading {
  color: #888;
  font-size: 13px;
}
</style>
