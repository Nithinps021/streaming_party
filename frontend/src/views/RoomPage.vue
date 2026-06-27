<script setup>
import { ref, onMounted, onUnmounted, provide } from 'vue'
import { useRouter } from 'vue-router'
import VideoPlayer from '../components/VideoPlayer.vue'
import ChatSidebar from '../components/ChatSidebar.vue'

const props = defineProps({
  id: { type: String, required: true }
})

const API_BASE = import.meta.env.VITE_API_URL || window.location.origin
const WS_BASE = API_BASE.replace(/^http/, 'ws')

const router = useRouter()
const ws = ref(null)
const isConnected = ref(false)
const isAdmin = ref(false)
const roomState = ref(null)
const chatHistory = ref([])
const error = ref(null)

const username = ref('User_' + Math.floor(Math.random() * 1000))

// Provide WebSocket context to child components
provide('ws', ws)
provide('isAdmin', isAdmin)
provide('roomState', roomState)
provide('chatHistory', chatHistory)
provide('username', username)

onMounted(async () => {
  // Validate room first
  try {
    const res = await fetch(`${API_BASE}/api/room/${props.id}`)
    if (!res.ok) {
      error.value = "Room not found or expired."
      return
    }
  } catch (err) {
    error.value = "Could not connect to server."
    return
  }

  // Connect WebSocket
  const adminToken = localStorage.getItem(`admin_token_${props.id}`) || ''
  const wsUrl = `${WS_BASE}/ws/${props.id}?admin_token=${adminToken}&username=${username.value}`
  
  ws.value = new WebSocket(wsUrl)
  
  ws.value.onopen = () => {
    isConnected.value = true
  }
  
  ws.value.onmessage = (event) => {
    const data = JSON.parse(event.data)
    
    if (data.type === 'init') {
      roomState.value = data.state
      chatHistory.value = data.chat_history
      isAdmin.value = data.is_admin
    } else if (data.type === 'sync') {
      roomState.value = data.state
    } else if (data.type === 'play' || data.type === 'pause' || data.type === 'seek') {
      // Force update state based on admin action
      roomState.value = {
        ...roomState.value,
        is_playing: data.type === 'play' || (data.type === 'seek' ? roomState.value.is_playing : false),
        current_time: data.time !== undefined ? data.time : roomState.value.current_time
      }
    } else if (data.type === 'chat') {
      chatHistory.value.push(data.message)
    }
  }
  
  ws.value.onclose = () => {
    isConnected.value = false
    if (!error.value) error.value = "Disconnected from server."
  }
})

onUnmounted(() => {
  if (ws.value) {
    ws.value.close()
  }
})

function copyLink() {
  navigator.clipboard.writeText(window.location.href)
  alert('Link copied!')
}

let oauthToken = null;
let tokenRefreshTimer = null;

let tokenClient = null;

function handleAuthClick() {
  if (oauthToken) {
    createPicker();
    return;
  }
  
  if (!tokenClient) {
    tokenClient = google.accounts.oauth2.initTokenClient({
      client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID,
      scope: 'https://www.googleapis.com/auth/drive.readonly',
      callback: (tokenResponse) => {
        if (tokenResponse.error !== undefined) {
          throw tokenResponse;
        }
        oauthToken = tokenResponse.access_token;
        createPicker();
        
        if (tokenRefreshTimer) clearInterval(tokenRefreshTimer);
        tokenRefreshTimer = setInterval(() => {
          tokenClient.requestAccessToken({ prompt: '' });
        }, 3000000);
      },
    });
  }
  
  tokenClient.requestAccessToken();
}

function createPicker() {
  const view = new google.picker.DocsView(google.picker.ViewId.DOCS);
  view.setIncludeFolders(true);
  view.setSelectFolderEnabled(false);
  
  // Extract Project Number from Client ID (it's the first part before the dash)
  const appId = import.meta.env.VITE_GOOGLE_CLIENT_ID.split('-')[0];
  
  const picker = new google.picker.PickerBuilder()
    .addView(view)
    .setOAuthToken(oauthToken)
    .setDeveloperKey(import.meta.env.VITE_GOOGLE_API_KEY)
    .setAppId(appId)
    .setCallback(pickerCallback)
    .build();
  picker.setVisible(true);
}

function pickerCallback(data) {
  if (data.action === google.picker.Action.PICKED) {
    const doc = data.docs[0];
    const fileId = doc.id;
    // Route through backend proxy which handles Google Drive auth server-side
    const url = `${API_BASE}/api/stream/${props.id}/${fileId}`;

    // Send video URL + access token so backend can authenticate with Google Drive
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({
        type: 'change_video',
        url,
        access_token: oauthToken
      }));
    }
  }
}

// Load Picker API
onMounted(() => {
  // Try loading gapi picker, handle async load
  const loadGapi = setInterval(() => {
    if (window.gapi) {
      gapi.load('picker', () => {});
      clearInterval(loadGapi);
    }
  }, 100);
})
</script>

<template>
  <div v-if="error" class="error-screen">
    <div class="glass-panel error-panel">
      <h2>Oops!</h2>
      <p>{{ error }}</p>
      <button class="btn-primary mt-4" @click="router.push('/')">Go Home</button>
    </div>
  </div>
  
  <div v-else-if="!isConnected" class="loading-screen">
    <div class="spinner"></div>
    <p>Connecting to room...</p>
  </div>
  
  <div v-else class="room-layout">
    <header class="room-header glass-panel">
      <div class="header-info">
        <h2>StreamParty <span v-if="isAdmin" class="badge">Admin</span></h2>
        <span class="room-id">Room: {{ id }}</span>
      </div>
      <div class="header-actions" style="display: flex; gap: 10px;">
        <button v-if="isAdmin" class="btn-primary btn-sm" @click="handleAuthClick" style="background: #10b981;">Choose Movie from Drive</button>
        <button class="btn-primary btn-sm" @click="copyLink">Share Link</button>
      </div>
    </header>
    
    <main class="room-content">
      <div class="video-container">
        <VideoPlayer />
      </div>
      <div class="chat-container glass-panel">
        <ChatSidebar />
      </div>
    </main>
  </div>
</template>

<style scoped>
.error-screen, .loading-screen {
  height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 1rem;
}

.error-panel {
  padding: 2rem;
  text-align: center;
}

.mt-4 {
  margin-top: 1rem;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid rgba(255, 255, 255, 0.1);
  border-left-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.room-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  padding: 1rem;
  gap: 1rem;
}

.room-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  border-radius: 12px;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.badge {
  background-color: var(--primary-color);
  font-size: 0.75rem;
  padding: 2px 6px;
  border-radius: 4px;
  vertical-align: middle;
}

.room-id {
  color: #94a3b8;
  font-family: monospace;
}

.btn-sm {
  padding: 8px 16px;
  font-size: 0.875rem;
}

.room-content {
  display: flex;
  flex: 1;
  gap: 1rem;
  min-height: 0; /* Important for flex children to scroll */
}

.video-container {
  flex: 3;
  display: flex;
  justify-content: center;
  align-items: center;
}

.chat-container {
  flex: 1;
  min-width: 300px;
  max-width: 400px;
  display: flex;
  flex-direction: column;
  border-radius: 12px;
  overflow: hidden;
}

@media (max-width: 768px) {
  .room-content {
    flex-direction: column;
  }
  .chat-container {
    flex: none;
    height: 400px;
    max-width: 100%;
  }
}
</style>
