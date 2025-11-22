<template>
  <aside class="left-dock">
    <div class="dock-icons">
      <router-link
        v-for="tab in tabs"
        :key="tab.path"
        :to="tab.path"
        class="dock-icon"
        :class="{ active: isActive(tab.path) }"
        :title="tab.name"
        @dragover.prevent
        @drop="handleDrop($event, tab.name)"
      >
        {{ tab.icon }}
      </router-link>
    </div>
  </aside>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { useCardStore } from '../stores/cardStore'

const route = useRoute()
const cardStore = useCardStore()

const tabs = [
  { name: 'Explore', path: '/explore', icon: '🔍' },
  { name: 'Code', path: '/code', icon: '💻' },
  { name: 'Plan', path: '/plan', icon: '📐' }
]

const isActive = (path) => {
  return route.path === path
}

const handleDrop = async (event, toTab) => {
  const cardId = event.dataTransfer.getData('cardId')
  const fromTab = event.dataTransfer.getData('fromTab')

  if (cardId && fromTab !== toTab) {
    await cardStore.routeCard(cardId, fromTab, toTab)
  }
}
</script>

<style scoped>
.left-dock {
  width: 60px;
  background: #0d0d0d;
  border-right: 1px solid #222;
  display: flex;
  flex-direction: column;
  padding: 12px 0;
}

.dock-icons {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
}

.dock-icon {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: #1a1a1a;
  text-decoration: none;
  font-size: 20px;
  transition: all 0.2s;
  cursor: pointer;
}

.dock-icon:hover {
  background: #252525;
  transform: scale(1.05);
}

.dock-icon.active {
  background: #00d4aa;
  box-shadow: 0 0 12px rgba(0, 212, 170, 0.3);
}

.dock-icon.drag-over {
  background: #00d4aa;
  transform: scale(1.1);
}
</style>
