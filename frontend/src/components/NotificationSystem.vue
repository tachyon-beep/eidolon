<template>
  <Teleport to="body">
    <div class="notifications" aria-live="polite">
      <TransitionGroup name="notification">
        <div
          v-for="notif in notifications"
          :key="notif.id"
          :class="['notification', `type-${notif.type}`]"
          role="alert"
          :aria-label="notif.message"
        >
          <div class="notification-icon">
            {{ icons[notif.type] }}
          </div>
          <div class="notification-content">
            <div class="notification-message">{{ notif.message }}</div>
            <button
              v-if="notif.action"
              class="notification-action"
              @click="handleAction(notif)"
            >
              {{ notif.action }}
            </button>
          </div>
          <button
            class="notification-close"
            @click="removeNotification(notif.id)"
            aria-label="Dismiss notification"
          >
            ✕
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'

const notifications = ref([])
let nextId = 1

const icons = {
  success: '✓',
  error: '⚠',
  warning: '⚠',
  info: 'ⓘ'
}

function addNotification(message, type = 'info', options = {}) {
  const id = nextId++
  const notification = {
    id,
    message,
    type,
    action: options.action,
    callback: options.callback,
    duration: options.duration || 5000
  }

  notifications.value.push(notification)

  // Auto-remove after duration
  if (notification.duration > 0) {
    setTimeout(() => {
      removeNotification(id)
    }, notification.duration)
  }

  return id
}

function removeNotification(id) {
  const index = notifications.value.findIndex(n => n.id === id)
  if (index > -1) {
    notifications.value.splice(index, 1)
  }
}

function handleAction(notif) {
  if (notif.callback) {
    notif.callback()
  }
  removeNotification(notif.id)
}

// Expose methods for use in parent
defineExpose({
  addNotification,
  removeNotification,
  success: (msg, opts) => addNotification(msg, 'success', opts),
  error: (msg, opts) => addNotification(msg, 'error', opts),
  warning: (msg, opts) => addNotification(msg, 'warning', opts),
  info: (msg, opts) => addNotification(msg, 'info', opts)
})
</script>

<style scoped>
.notifications {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 400px;
}

.notification {
  display: flex;
  align-items: start;
  gap: 12px;
  padding: 16px;
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
  min-width: 300px;
}

.notification-icon {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: bold;
  border-radius: 50%;
}

.type-success {
  border-left: 3px solid #5de585;
}

.type-success .notification-icon {
  color: #5de585;
  background: rgba(93, 229, 133, 0.1);
}

.type-error {
  border-left: 3px solid #e55d5d;
}

.type-error .notification-icon {
  color: #e55d5d;
  background: rgba(229, 93, 93, 0.1);
}

.type-warning {
  border-left: 3px solid #e5a55d;
}

.type-warning .notification-icon {
  color: #e5a55d;
  background: rgba(229, 165, 93, 0.1);
}

.type-info {
  border-left: 3px solid #5d9de5;
}

.type-info .notification-icon {
  color: #5d9de5;
  background: rgba(93, 157, 229, 0.1);
}

.notification-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.notification-message {
  font-size: 14px;
  color: #e0e0e0;
  line-height: 1.5;
}

.notification-action {
  align-self: flex-start;
  padding: 6px 12px;
  background: #00d4aa;
  color: #000;
  border: none;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.notification-action:hover {
  background: #00ffcc;
}

.notification-close {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  color: #666;
  font-size: 16px;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
}

.notification-close:hover {
  background: #2a2a2a;
  color: #ccc;
}

/* Transition animations */
.notification-enter-active,
.notification-leave-active {
  transition: all 0.3s ease;
}

.notification-enter-from {
  opacity: 0;
  transform: translateX(100px);
}

.notification-leave-to {
  opacity: 0;
  transform: translateX(100px) scale(0.8);
}

/* Responsive */
@media (max-width: 640px) {
  .notifications {
    top: 10px;
    right: 10px;
    left: 10px;
    max-width: none;
  }

  .notification {
    min-width: unset;
  }
}
</style>
