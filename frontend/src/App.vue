<script setup>
import { onMounted, ref } from 'vue'
import ChatBox from './components/ChatBox.vue'
import GroupChatImport from './components/GroupChatImport.vue'
import { fetchHealth } from './api/agent'

const status = ref({ online: false, model: '未连接', keyReady: false })
const screen = ref('group')
const importedMessage = ref('')
const importedContext = ref('')
const importedCount = ref(0)

function openAssistant(payload) {
  importedMessage.value = payload.content
  importedContext.value = payload.context || ''
  importedCount.value = payload.count
  screen.value = 'assistant'
}

function backToGroup() {
  screen.value = 'group'
  importedMessage.value = ''
  importedContext.value = ''
  importedCount.value = 0
}

onMounted(async () => {
  try {
    const data = await fetchHealth()
    status.value = {
      online: data.status === 'ok',
      model: data.model,
      keyReady: data.api_key_configured,
    }
  } catch {
    status.value = { online: false, model: '后端未启动', keyReady: false }
  }
})
</script>

<template>
  <GroupChatImport v-if="screen === 'group'" class="group-shell" @import-chat="openAssistant" />

  <div v-else class="shell">
    <header class="header">
      <button class="back-button" aria-label="返回群聊" @click="backToGroup">‹</button>
      <div>
        <h1>程星AI · 智能行程助手</h1>
        <p class="subtitle">已导入 {{ importedCount }} 条群聊记录 · 正在整理</p>
      </div>
      <div class="status">
        <span class="dot" :class="{ online: status.online }"></span>
        <span>{{ status.model }}</span>
      </div>
    </header>

    <p v-if="status.online && !status.keyReady" class="warning">
      后端未检测到 API Key，请在 agent-backend/.env 中配置 DEEPSEEK_API_KEY
    </p>

    <ChatBox :initial-message="importedMessage" :initial-context="importedContext" />
  </div>
</template>

<style scoped>
.shell {
  width: 100%;
  max-width: 840px;
  height: 100%;
  max-height: 900px;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.group-shell {
  width: 100%;
  max-width: 480px;
  height: 100%;
  max-height: 900px;
  border: 1px solid var(--border);
  border-radius: 14px;
  box-shadow: 0 16px 50px rgba(33, 38, 52, 0.08);
}

.header {
  padding: 18px 22px;
  padding-top: calc(18px + var(--safe-top));
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.back-button {
  width: 34px;
  height: 34px;
  flex: 0 0 34px;
  padding: 0;
  border: 0;
  color: var(--text);
  background: transparent;
  font-size: 30px;
  line-height: 30px;
  cursor: pointer;
}

h1 {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
}

.subtitle {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--text-muted);
}

.status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted);
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #d0d3d8;
}

.dot.online {
  background: #22c55e;
}

.warning {
  margin: 0;
  padding: 9px 22px;
  font-size: 12px;
  color: #92400e;
  background: #fef3c7;
}

/* 移动端：占满全屏，去掉卡片边框与内边距，头部更紧凑 */
@media (max-width: 768px) {
  .shell {
    max-width: none;
    max-height: none;
    height: 100dvh;
    border: none;
    border-radius: 0;
  }

  .group-shell {
    max-width: none;
    max-height: none;
    height: 100dvh;
    border: none;
    border-radius: 0;
    box-shadow: none;
  }

  .header {
    padding: 12px 16px;
    padding-top: calc(12px + var(--safe-top));
  }

  h1 {
    font-size: 16px;
  }

  .subtitle {
    display: none;
  }

  .warning {
    padding: 8px 16px;
  }
}
</style>
