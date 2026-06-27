<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const isLoading = ref(false)
const joinRoomId = ref('')

async function createRoom() {
  isLoading.value = true
  try {
    const res = await fetch('http://localhost:8000/api/room', { method: 'POST' })
    if (!res.ok) throw new Error('Failed to create room')
    const data = await res.json()
    
    // Save admin token for this room
    localStorage.setItem(`admin_token_${data.room_id}`, data.admin_token)
    
    router.push(`/room/${data.room_id}`)
  } catch (err) {
    console.error(err)
    alert('Failed to create room.')
  } finally {
    isLoading.value = false
  }
}

function joinRoom() {
  if (joinRoomId.value.trim()) {
    router.push(`/room/${joinRoomId.value.trim()}`)
  }
}
</script>

<template>
  <div class="landing-container">
    <div class="glass-panel hero-panel">
      <h1 class="title">StreamParty</h1>
      <p class="subtitle">Watch movies in perfect sync with your friends.</p>
      
      <div class="actions">
        <button class="btn-primary create-btn" @click="createRoom" :disabled="isLoading">
          {{ isLoading ? 'Creating...' : 'Create a Room' }}
        </button>
        
        <div class="divider"><span>OR</span></div>
        
        <div class="join-action">
          <input 
            v-model="joinRoomId" 
            type="text" 
            placeholder="Enter Room ID" 
            @keyup.enter="joinRoom"
          />
          <button class="btn-primary" @click="joinRoom" :disabled="!joinRoomId.trim()">
            Join
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.landing-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  padding: 20px;
}

.hero-panel {
  padding: 3rem;
  text-align: center;
  max-width: 500px;
  width: 100%;
}

.title {
  font-size: 3rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  background: -webkit-linear-gradient(45deg, #ffffff, #888888);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.subtitle {
  color: #94a3b8;
  margin-bottom: 2.5rem;
}

.actions {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.create-btn {
  font-size: 1.1rem;
  padding: 12px;
}

.divider {
  display: flex;
  align-items: center;
  color: #64748b;
  font-size: 0.875rem;
}

.divider::before, .divider::after {
  content: '';
  flex: 1;
  border-bottom: 1px solid var(--glass-border);
}

.divider span {
  padding: 0 10px;
}

.join-action {
  display: flex;
  gap: 10px;
}

.join-action input {
  flex: 1;
}
</style>
