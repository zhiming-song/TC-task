<script setup>
import { computed, nextTick, ref } from 'vue'

const emit = defineEmits(['import-chat'])
const draft = ref('')
const messageListEl = ref(null)
const members = [
  { name: '林一', avatar: '林', color: '#ff9a45' },
  { name: 'Evan', avatar: 'E', color: '#5b8ff9' },
  { name: '小北', avatar: '北', color: '#8b6cf0' },
  { name: '程程', avatar: '程', color: '#31b49c' },
  { name: 'Dora', avatar: 'D', color: '#eb6ca4' },
]
const activeMemberName = ref('林一')
const activeMember = computed(() => members.find((member) => member.name === activeMemberName.value) || members[0])

const messages = ref([
  { id: 1, sender: '林一', avatar: '林', color: '#ff9a45', text: '今年国庆从北京去上海玩吧，我们正好5个人', time: '20:16', mine: true, selected: true },
  { id: 2, sender: 'Evan', avatar: 'E', color: '#5b8ff9', text: '高铁吧，飞机延误怕了，而且大家还能坐一起', time: '20:17', selected: true },
  { id: 3, sender: '小北', avatar: '北', color: '#8b6cf0', text: '我要去迪士尼乐园！！这个必须安排', time: '20:18', selected: true },
  { id: 4, sender: '程程', avatar: '程', color: '#31b49c', text: '住外滩附近吧，晚上可以散步看夜景', time: '20:20', selected: true },
  { id: 5, sender: 'Dora', avatar: 'D', color: '#eb6ca4', text: '我想住迪士尼附近，第二天不用起太早', time: '20:21', selected: true },
  { id: 6, sender: 'Evan', avatar: 'E', color: '#5b8ff9', text: '虹桥火车站附近也方便，返程不用赶', time: '20:23', selected: true },
  { id: 7, sender: '林一', avatar: '林', color: '#ff9a45', text: '那就10月1号出发，3号回来，3天2晚', time: '20:25', mine: true, selected: true },
  { id: 8, sender: '程程', avatar: '程', color: '#31b49c', text: '人均最好不要超过3000元', time: '20:26', selected: true },
])

const selectedMessages = computed(() => messages.value.filter((message) => message.selected))
const allSelected = computed(() => selectedMessages.value.length === messages.value.length)

function toggleMessage(id) {
  const message = messages.value.find((item) => item.id === id)
  if (message) message.selected = !message.selected
}

function toggleAll() {
  const nextValue = !allSelected.value
  messages.value.forEach((message) => {
    message.selected = nextValue
  })
}

function importToAssistant() {
  if (!selectedMessages.value.length) return

  const transcript = selectedMessages.value
    .map((message) => `[${message.time}] ${message.sender}：${message.text}`)
    .join('\n')

  const content = `我从微信群聊导入了${selectedMessages.value.length}条出行讨论，请先整理必要行程信息，不要开始搜索，等我确认后再规划。\n\n【群聊记录】\n${transcript}\n\n请只整理和确认开始规划所必需的信息：出行人数、日期、出发城市、目的城市、预算，以及确实影响行程的儿童或房间信息；不要输出任何群友偏好、偏好归因、偏好冲突或偏好表格；无法确定的必要信息请一次只追问一个。`

  emit('import-chat', { content, count: selectedMessages.value.length })
}

async function sendGroupMessage() {
  const text = draft.value.trim()
  if (!text) return
  const now = new Date()
  const time = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
  messages.value.push({
    id: Date.now(),
    sender: activeMember.value.name,
    avatar: activeMember.value.avatar,
    color: activeMember.value.color,
    text,
    time,
    selected: true,
  })
  draft.value = ''
  await nextTick()
  if (messageListEl.value) messageListEl.value.scrollTop = messageListEl.value.scrollHeight
}

function onComposerKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendGroupMessage()
  }
}
</script>

<template>
  <section class="wechat-page">
    <header class="wx-header">
      <button class="nav-icon" aria-label="返回">‹</button>
      <div class="group-title">
        <strong>国庆上海冲冲冲（5）</strong>
        <span>选择要导入的聊天记录</span>
      </div>
      <button class="nav-icon more" aria-label="更多">•••</button>
    </header>

    <div class="import-tip">
      <span class="ai-mark">✦</span>
      <div>
        <strong>程星AI 可以帮大家整理方案</strong>
        <span>勾选旅行相关消息，一键提取每个人的意见</span>
      </div>
    </div>

    <main ref="messageListEl" class="message-list">
      <div class="date-separator">8月26日 晚上</div>

      <article
        v-for="message in messages"
        :key="message.id"
        class="message-row"
        :class="{ mine: message.sender === activeMemberName, selected: message.selected }"
      >
        <button
          class="select-dot"
          :class="{ checked: message.selected }"
          :aria-label="message.selected ? '取消选择' : '选择消息'"
          @click="toggleMessage(message.id)"
        >
          <span>✓</span>
        </button>

        <div class="avatar" :style="{ background: message.color }">{{ message.avatar }}</div>

        <div class="message-content" @click="toggleMessage(message.id)">
          <span class="sender">{{ message.sender }}</span>
          <div class="message-bubble">{{ message.text }}</div>
          <small>{{ message.time }}</small>
        </div>
      </article>
    </main>

    <footer class="import-footer">
      <div class="selection-summary">
        <div class="selection-left">
          <button class="select-all" @click="toggleAll">
            <span class="mini-check" :class="{ checked: allSelected }">✓</span>
            {{ allSelected ? '取消全选' : '全选' }}
          </button>
          <span>已选 {{ selectedMessages.length }} 条</span>
        </div>
        <button class="compact-import" :disabled="!selectedMessages.length" @click="importToAssistant">
          <span class="spark">✦</span>
          导入AI
        </button>
      </div>
      <div class="role-switcher" aria-label="选择当前聊天角色">
        <span>我扮演</span>
        <button
          v-for="member in members"
          :key="member.name"
          type="button"
          class="role-chip"
          :class="{ active: activeMemberName === member.name }"
          @click="activeMemberName = member.name"
        >
          <i :style="{ background: member.color }">{{ member.avatar }}</i>
          {{ member.name }}
        </button>
      </div>
      <div class="group-composer">
        <textarea
          v-model="draft"
          rows="1"
          placeholder="发消息…"
          @keydown="onComposerKeydown"
        ></textarea>
        <button class="send-button" :disabled="!draft.trim()" @click="sendGroupMessage">发送</button>
      </div>
    </footer>
  </section>
</template>

<style scoped>
button {
  font: inherit;
}

.wechat-page {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  color: #191919;
  background: #ededed;
}

.wx-header {
  min-height: 68px;
  padding: calc(10px + var(--safe-top)) 14px 10px;
  display: grid;
  grid-template-columns: 40px 1fr 40px;
  align-items: center;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  background: rgba(247, 247, 247, 0.96);
  backdrop-filter: blur(18px);
  z-index: 2;
}

.nav-icon {
  width: 38px;
  height: 38px;
  border: 0;
  padding: 0;
  color: #111;
  background: transparent;
  font-size: 34px;
  line-height: 32px;
  cursor: pointer;
}

.nav-icon.more {
  font-size: 17px;
  letter-spacing: 1px;
}

.group-title {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.group-title strong {
  font-size: 16px;
  font-weight: 600;
}

.group-title span {
  color: #8b8b8b;
  font-size: 11px;
}

.import-tip {
  margin: 12px 14px 2px;
  padding: 11px 13px;
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid #dce6ff;
  border-radius: 12px;
  background: linear-gradient(135deg, #ffffff 0%, #f2f6ff 100%);
  box-shadow: 0 3px 12px rgba(68, 102, 200, 0.06);
}

.ai-mark {
  width: 34px;
  height: 34px;
  flex: 0 0 34px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  color: #fff;
  background: linear-gradient(135deg, #5e7df8, #7357df);
  font-size: 18px;
}

.import-tip div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.import-tip strong {
  font-size: 13px;
}

.import-tip div span {
  color: #7a8292;
  font-size: 11px;
}

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 14px 28px;
  -webkit-overflow-scrolling: touch;
}

.date-separator {
  margin: 10px 0 18px;
  color: #a5a5a5;
  font-size: 11px;
  text-align: center;
}

.message-row {
  margin-bottom: 17px;
  display: grid;
  grid-template-columns: 26px 38px minmax(0, 1fr);
  align-items: start;
  gap: 9px;
}

.message-row.mine {
  grid-template-columns: 26px minmax(0, 1fr) 38px;
}

.message-row.mine .select-dot {
  grid-column: 1;
}

.message-row.mine .avatar {
  grid-column: 3;
}

.message-row.mine .message-content {
  grid-column: 2;
  grid-row: 1;
  justify-self: end;
  width: fit-content;
  align-items: flex-end;
}

.select-dot {
  width: 22px;
  height: 22px;
  margin-top: 23px;
  padding: 0;
  border: 1.5px solid #b8b8b8;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: transparent;
  background: transparent;
  cursor: pointer;
  transition: 0.18s ease;
}

.select-dot.checked,
.mini-check.checked {
  border-color: #07c160;
  color: #fff;
  background: #07c160;
}

.select-dot span {
  font-size: 13px;
  transform: translateY(-0.5px);
}

.avatar {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 5px;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.05);
}

.message-content {
  max-width: 82%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  cursor: pointer;
}

.sender {
  margin-bottom: 4px;
  color: #7e7e7e;
  font-size: 11px;
}

.message-bubble {
  position: relative;
  padding: 9px 11px;
  border-radius: 5px;
  background: #fff;
  font-size: 14px;
  line-height: 1.52;
  word-break: break-word;
  box-shadow: 0 1px 1px rgba(0, 0, 0, 0.025);
}

.message-row.mine .message-bubble {
  background: #95ec69;
}

.message-content small {
  margin-top: 3px;
  color: #b3b3b3;
  font-size: 9px;
}

.import-footer {
  padding: 12px 14px calc(10px + var(--safe-bottom));
  border-top: 1px solid rgba(0, 0, 0, 0.07);
  background: rgba(250, 250, 250, 0.97);
  backdrop-filter: blur(18px);
}

.selection-summary {
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #888;
  font-size: 11px;
}

.selection-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.select-all {
  padding: 0;
  border: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  color: #555;
  background: transparent;
  cursor: pointer;
}

.mini-check {
  width: 17px;
  height: 17px;
  border: 1px solid #aaa;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: transparent;
  font-size: 10px;
}

.compact-import {
  min-height: 32px;
  padding: 0 13px;
  border: 0;
  border-radius: 16px;
  color: #fff;
  background: linear-gradient(135deg, #5c78f2, #7256dc);
  box-shadow: 0 4px 10px rgba(84, 91, 220, 0.2);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.compact-import:disabled {
  opacity: 0.45;
  box-shadow: none;
  cursor: not-allowed;
}

.spark {
  margin-right: 4px;
}

.role-switcher {
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 5px;
  overflow-x: auto;
  scrollbar-width: none;
  white-space: nowrap;
}

.role-switcher::-webkit-scrollbar {
  display: none;
}

.role-switcher > span {
  flex: 0 0 auto;
  margin-right: 2px;
  color: #888;
  font-size: 11px;
}

.role-chip {
  min-height: 28px;
  padding: 3px 7px 3px 4px;
  border: 1px solid #dedede;
  border-radius: 14px;
  display: flex;
  align-items: center;
  gap: 4px;
  color: #666;
  background: #fff;
  font-size: 11px;
  cursor: pointer;
}

.role-chip i {
  width: 20px;
  height: 20px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: #fff;
  font-size: 10px;
  font-style: normal;
}

.role-chip.active {
  border-color: #07c160;
  color: #078f49;
  background: #effbf4;
  box-shadow: inset 0 0 0 1px rgba(7, 193, 96, 0.08);
}

.group-composer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: end;
  gap: 8px;
}

.group-composer textarea {
  width: 100%;
  min-height: 38px;
  max-height: 88px;
  padding: 8px 10px;
  border: 1px solid #dedede;
  border-radius: 8px;
  outline: none;
  resize: none;
  color: #222;
  background: #fff;
  font-family: inherit;
  font-size: 14px;
  line-height: 20px;
}

.group-composer textarea:focus {
  border-color: #b8b8b8;
}

.send-button {
  height: 38px;
  padding: 0 14px;
  border: 0;
  border-radius: 7px;
  color: #fff;
  background: #07c160;
  font-size: 13px;
  cursor: pointer;
}

.send-button:disabled {
  opacity: 0.42;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .wechat-page {
    height: 100dvh;
  }
}
</style>
