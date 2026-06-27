<script setup>
import { ref, inject, nextTick, watch } from 'vue'

const ws = inject('ws')
const chatHistory = inject('chatHistory')
const username = inject('username')

const newMessage = ref('')
const messagesContainer = ref(null)

// Auto-scroll on new message
watch(chatHistory, async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}, { deep: true })

function sendMessage() {
  const text = newMessage.value.trim()
  if (!text) return
  
  if (ws.value?.readyState === WebSocket.OPEN) {
    ws.value.send(JSON.stringify({ type: 'chat', text }))
    newMessage.value = ''
  }
}
</script>

<template>
  <div class="chat-sidebar">
    <div class="chat-header">
      <h3>Live Chat</h3>
      <span class="user-badge">{{ username }}</span>
    </div>
    
    <div class="messages" ref="messagesContainer">
      <div v-if="chatHistory.length === 0" class="no-messages">
        Say hi to start the party!
      </div>
      
      <div 
        v-for="(msg, index) in chatHistory" 
        :key="index"
        class="message"
        :class="{ 'own-message': msg.username === username }"
      >
        <span class="msg-user" v-if="msg.username !== username">{{ msg.username }}</span>
        <div class="msg-bubble">{{ msg.text }}</div>
      </div>
    </div>
    
    <div class="chat-input">
      <input 
        v-model="newMessage" 
        type="text" 
        placeholder="Type a message..." 
        @keyup.enter="sendMessage"
      />
      <button class="btn-primary send-btn" @click="sendMessage">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
          <path d="M15.854.146a.5.5 0 0 1 .11.54l-5.819 14.547a.75.75 0 0 1-1.329.124l-3.178-4.995L.643 7.184a.75.75 0 0 1 .124-1.33L15.314.037a.5.5 0 0 1 .54.11ZM6.636 10.07l2.761 4.338L14.13 2.576 6.636 10.07Zm6.787-8.201L1.591 6.602l4.339 2.76 7.494-7.493Z"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.chat-sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--glass-bg);
}

.chat-header {
  padding: 15px;
  border-bottom: 1px solid var(--glass-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-header h3 {
  font-size: 1.1rem;
  margin: 0;
}

.user-badge {
  font-size: 0.75rem;
  background: rgba(255, 255, 255, 0.1);
  padding: 4px 8px;
  border-radius: 12px;
  color: #cbd5e1;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 15px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.no-messages {
  text-align: center;
  color: #64748b;
  font-style: italic;
  margin-top: 20px;
}

.message {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  max-width: 85%;
}

.own-message {
  align-self: flex-end;
  align-items: flex-end;
}

.msg-user {
  font-size: 0.75rem;
  color: #94a3b8;
  margin-bottom: 4px;
  margin-left: 4px;
}

.msg-bubble {
  background: rgba(255, 255, 255, 0.1);
  padding: 8px 12px;
  border-radius: 12px;
  border-bottom-left-radius: 2px;
  font-size: 0.9rem;
  line-height: 1.4;
}

.own-message .msg-bubble {
  background: var(--primary-color);
  border-radius: 12px;
  border-bottom-right-radius: 2px;
}

.chat-input {
  display: flex;
  padding: 15px;
  gap: 10px;
  border-top: 1px solid var(--glass-border);
}

.chat-input input {
  flex: 1;
  border-radius: 20px;
  padding: 10px 15px;
}

.send-btn {
  border-radius: 50%;
  width: 40px;
  height: 40px;
  padding: 0;
  display: flex;
  justify-content: center;
  align-items: center;
}
</style>
