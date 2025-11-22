<template>
  <div class="tree-node">
    <div class="node-content" @click="toggleExpand">
      <span class="expand-icon" v-if="node.children?.length > 0">
        {{ isExpanded ? '▼' : '▶' }}
      </span>
      <span class="node-scope" :class="`scope-${node.scope.toLowerCase()}`">
        {{ node.scope }}
      </span>
      <span class="node-target">{{ formatTarget(node.target) }}</span>
      <span class="node-stats">
        {{ node.findings_count }} findings • {{ node.cards_count }} cards
      </span>
      <span class="node-status" :class="`status-${node.status.toLowerCase()}`">
        {{ node.status }}
      </span>
    </div>

    <div v-if="isExpanded && node.children?.length > 0" class="node-children">
      <TreeNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
      />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  node: {
    type: Object,
    required: true
  }
})

const isExpanded = ref(true)

const toggleExpand = () => {
  isExpanded.value = !isExpanded.value
}

const formatTarget = (target) => {
  // Shorten long paths
  if (target.length > 50) {
    return '...' + target.slice(-47)
  }
  return target
}
</script>

<style scoped>
.tree-node {
  margin: 4px 0;
}

.node-content {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: #222;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.node-content:hover {
  background: #2a2a2a;
}

.expand-icon {
  font-size: 10px;
  color: #666;
  width: 12px;
}

.node-scope {
  font-size: 10px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 4px;
  text-transform: uppercase;
}

.scope-system {
  background: #2a1a1a;
  color: #e55d5d;
}

.scope-module {
  background: #1a2a2a;
  color: #5d9de5;
}

.scope-function {
  background: #1a2a1a;
  color: #5de585;
}

.node-target {
  flex: 1;
  font-size: 12px;
  font-family: monospace;
  color: #ccc;
}

.node-stats {
  font-size: 11px;
  color: #888;
}

.node-status {
  font-size: 10px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 4px;
}

.status-analyzing {
  background: #2a2a1a;
  color: #e5d55d;
}

.status-completed {
  background: #1a2a1a;
  color: #5de585;
}

.node-children {
  margin-left: 24px;
  padding-left: 12px;
  border-left: 2px solid #333;
}
</style>
