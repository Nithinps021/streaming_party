<script setup>
import { ref, inject, watch, onMounted, onUnmounted, computed } from 'vue'

const ws = inject('ws')
const isAdmin = inject('isAdmin')
const roomState = inject('roomState')

const videoRef = ref(null)
const isUpdatingFromRemote = ref(false)

const videoSrc = computed(() => {
  return roomState.value?.video_url || ''
})

// Watch for state changes from server to update video element
watch(roomState, (newState, oldState) => {
  if (!newState || !videoRef.value) return
  
  isUpdatingFromRemote.value = true
  
  // Sync time if difference is greater than 1 second
  const timeDiff = Math.abs(videoRef.value.currentTime - newState.current_time)
  if (timeDiff > 1.0) {
    videoRef.value.currentTime = newState.current_time
  }
  
  // Sync play state
  if (newState.is_playing && videoRef.value.paused) {
    videoRef.value.play().catch(e => console.log('Autoplay prevented', e))
  } else if (!newState.is_playing && !videoRef.value.paused) {
    videoRef.value.pause()
  }
  
  setTimeout(() => {
    isUpdatingFromRemote.value = false
  }, 100)
}, { deep: true })

// Local events to send to server
function handlePlay() {
  if (!isAdmin.value || isUpdatingFromRemote.value) return
  if (ws.value?.readyState === WebSocket.OPEN) {
    ws.value.send(JSON.stringify({ type: 'play', time: videoRef.value.currentTime }))
  }
}

function handlePause() {
  if (!isAdmin.value || isUpdatingFromRemote.value) return
  if (ws.value?.readyState === WebSocket.OPEN) {
    ws.value.send(JSON.stringify({ type: 'pause', time: videoRef.value.currentTime }))
  }
}

function handleSeek() {
  if (!isAdmin.value || isUpdatingFromRemote.value) return
  if (ws.value?.readyState === WebSocket.OPEN) {
    ws.value.send(JSON.stringify({ type: 'seek', time: videoRef.value.currentTime }))
  }
}

// Keep in sync periodically if viewer
let syncInterval;
onMounted(() => {
  if (!isAdmin.value) {
    syncInterval = setInterval(() => {
      if (ws.value?.readyState === WebSocket.OPEN) {
        ws.value.send(JSON.stringify({ type: 'sync_request' }))
      }
    }, 5000)
  }
})

onUnmounted(() => {
  if (syncInterval) clearInterval(syncInterval)
})
</script>

<template>
  <div class="video-wrapper glass-panel">
    <div v-if="!roomState?.video_url" class="no-video">
      Waiting for video source...
    </div>
    <video
      v-else
      ref="videoRef"
      class="video-element"
      :src="videoSrc"
      :controls="isAdmin"
      referrerpolicy="no-referrer"
      @play="handlePlay"
      @pause="handlePause"
      @seeked="handleSeek"
    ></video>
    
    <div v-if="!isAdmin" class="viewer-overlay">
      <p class="overlay-text">Admin is controlling playback</p>
    </div>
  </div>
</template>

<style scoped>
.video-wrapper {
  position: relative;
  width: 100%;
  max-width: 1000px;
  aspect-ratio: 16 / 9;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #000;
}

.video-element {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.no-video {
  color: #94a3b8;
}

.viewer-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(transparent, rgba(0,0,0,0.8));
  padding: 10px;
  text-align: center;
  pointer-events: none; /* Allows clicking video if needed, but no controls are shown */
}

.overlay-text {
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.875rem;
  letter-spacing: 1px;
}
</style>
