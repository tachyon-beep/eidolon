<template>
  <nav class="top-nav">
    <div class="logo-section">
      <div class="logo">
        <div class="logo-icon">
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M16 4L26 10V22L16 28L6 22V10L16 4Z" stroke="url(#gradient1)" stroke-width="2" fill="none"/>
            <path d="M16 12L21 15V21L16 24L11 21V15L16 12Z" fill="url(#gradient2)"/>
            <circle cx="16" cy="16" r="2" fill="var(--amber-bright)"/>
            <defs>
              <linearGradient id="gradient1" x1="6" y1="4" x2="26" y2="28" gradientUnits="userSpaceOnUse">
                <stop stop-color="var(--amber-primary)"/>
                <stop offset="1" stop-color="var(--purple-soft)"/>
              </linearGradient>
              <linearGradient id="gradient2" x1="11" y1="12" x2="21" y2="24" gradientUnits="userSpaceOnUse">
                <stop stop-color="var(--electric-blue)" stop-opacity="0.4"/>
                <stop offset="1" stop-color="var(--purple-soft)" stop-opacity="0.2"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <div class="logo-text">
          <h1>EIDOLON</h1>
          <span class="tagline">recursive unity • made manifest</span>
        </div>
      </div>

      <div class="status-indicator">
        <div class="pulse-dot"></div>
        <span class="status-text">agents active</span>
      </div>
    </div>

    <div class="tabs">
      <router-link
        v-for="tab in tabs"
        :key="tab.path"
        :to="tab.path"
        class="tab"
        :class="{ active: isActive(tab.path) }"
      >
        <span class="tab-icon">{{ tab.icon }}</span>
        <span class="tab-name">{{ tab.name }}</span>
      </router-link>
    </div>
  </nav>
</template>

<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()

const tabs = [
  { name: 'Explore', path: '/explore', icon: '◈' },
  { name: 'Code', path: '/code', icon: '⟨⟩' },
  { name: 'Plan', path: '/plan', icon: '⬡' }
]

const isActive = (path) => {
  return route.path === path
}
</script>

<style scoped>
.top-nav {
  background: rgba(26, 26, 46, 0.7);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(167, 139, 250, 0.15);
  padding: 16px 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: relative;
  z-index: 100;
}

.top-nav::before {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg,
    transparent 0%,
    var(--purple-soft) 20%,
    var(--amber-primary) 50%,
    var(--purple-soft) 80%,
    transparent 100%
  );
  opacity: 0.3;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 32px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 14px;
}

.logo-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  animation: rotateGlow 8s ease-in-out infinite;
}

@keyframes rotateGlow {
  0%, 100% {
    filter: drop-shadow(0 0 8px var(--amber-glow));
    transform: rotate(0deg);
  }
  50% {
    filter: drop-shadow(0 0 12px var(--purple-glow));
    transform: rotate(180deg);
  }
}

.logo-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.logo-text h1 {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 4px;
  background: linear-gradient(135deg, var(--amber-primary), var(--amber-bright), var(--purple-soft));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.tagline {
  font-family: var(--font-display);
  font-size: 9px;
  color: var(--text-muted);
  font-weight: 400;
  letter-spacing: 1.5px;
  text-transform: lowercase;
  opacity: 0.7;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: rgba(6, 182, 212, 0.08);
  border: 1px solid rgba(6, 182, 212, 0.2);
  border-radius: 12px;
}

.pulse-dot {
  width: 6px;
  height: 6px;
  background: var(--cyan-active);
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
  box-shadow: 0 0 8px var(--cyan-active);
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.6;
    transform: scale(1.2);
  }
}

.status-text {
  font-size: 10px;
  font-weight: 500;
  color: var(--cyan-active);
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.tabs {
  display: flex;
  gap: 6px;
  background: rgba(30, 30, 52, 0.4);
  padding: 6px;
  border-radius: 12px;
  border: 1px solid rgba(167, 139, 250, 0.1);
}

.tab {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  color: var(--text-secondary);
  text-decoration: none;
  border-radius: 8px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.3px;
  position: relative;
  overflow: hidden;
}

.tab::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, var(--amber-glow), var(--purple-glow));
  opacity: 0;
  transition: opacity 0.3s;
}

.tab:hover::before {
  opacity: 1;
}

.tab:hover {
  color: var(--text-primary);
  transform: translateY(-1px);
}

.tab-icon {
  font-size: 16px;
  position: relative;
  z-index: 1;
}

.tab-name {
  position: relative;
  z-index: 1;
}

.tab.active {
  background: linear-gradient(135deg, var(--amber-primary), var(--amber-bright));
  color: var(--deep-space);
  box-shadow:
    0 0 20px var(--amber-glow),
    0 4px 12px rgba(0, 0, 0, 0.3);
  font-weight: 700;
}

.tab.active::before {
  opacity: 0;
}

.tab.active .tab-icon {
  animation: iconBounce 0.5s ease-out;
}

@keyframes iconBounce {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.2);
  }
}
</style>
