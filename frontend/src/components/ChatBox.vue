<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { createChatJob, pollChatJob, saveTripSelection } from '../api/agent'
import HotelCard from './HotelCard.vue'
import TicketCard from './TicketCard.vue'
import TransportCard from './TransportCard.vue'

const props = defineProps({
  initialMessage: {
    type: String,
    default: '',
  },
  showOrderButton: {
    type: Boolean,
    default: false,
  },
})
const emit = defineEmits(['open-summary'])

const messages = ref([])
const input = ref('')
const loading = ref(false)
const listEl = ref(null)
const confirmedTransportId = ref('')
const confirmedHotelId = ref('')
const confirmedTicketIds = ref([])
const summaryVisible = ref(false)
const summaryLinkVisible = ref(false)
const summaryDraft = ref({ transport: '', hotel: '', ticket: [] })
const starters = [
  '我想规划一次多人旅行',
  '帮我整理这段群聊里的出行需求',
  '北京出发去上海，5人，玩3天',
]

function formatMessage(content) {
  const escaped = content
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;')

  const lines = escaped.split('\n')
  const output = []
  const inline = (line) => line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  const cells = (line) => line.slice(1, -1).split('|').map((cell) => inline(cell.trim()))

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index]
    const nextLine = lines[index + 1] || ''
    if (/^\|.*\|$/.test(line.trim()) && /^\|[\s|:\-]+\|$/.test(nextLine.trim())) {
      const headers = cells(line.trim())
      const rows = []
      index += 2
      while (index < lines.length && /^\|.*\|$/.test(lines[index].trim())) {
        rows.push(cells(lines[index].trim()))
        index += 1
      }
      index -= 1
      output.push(`<div class="md-table-wrap"><table><thead><tr>${headers.map((cell) => `<th>${cell}</th>`).join('')}</tr></thead><tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`)
      continue
    }

    const withBold = inline(line)
    if (withBold.startsWith('### ')) output.push(`<h4>${withBold.slice(4)}</h4>`)
    else if (withBold.startsWith('## ')) output.push(`<h3>${withBold.slice(3)}</h3>`)
    else if (withBold.startsWith('# ')) output.push(`<h2>${withBold.slice(2)}</h2>`)
    else if (withBold.startsWith('- ')) output.push(`<div class="md-list">• ${withBold.slice(2)}</div>`)
    else if (/^\d+\. /.test(withBold)) output.push(`<div class="md-list">${withBold}</div>`)
    else if (/^---+$/.test(withBold.trim())) output.push('<hr>')
    else output.push(withBold ? `<div>${withBold}</div>` : '<div class="md-gap"></div>')
  }

  return output.join('')
}

async function scrollToBottom() {
  await nextTick()
  if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
}

/**
 * 提取可展示的请求失败信息。
 *
 * @param {unknown} error 请求过程抛出的异常。
 * @return {string} 可直接展示给用户的错误信息。
 */
function getErrorMessage(error) {
  if (error instanceof Error && error.message) return error.message
  if (typeof error === 'string' && error.trim()) return error
  return '请求失败，请检查网络连接后重试。'
}

async function send(contextContent = '', suppressCards = false) {
  const text = input.value.trim()
  if (!text || loading.value) return

  const normalizedContext = typeof contextContent === 'string' ? contextContent : ''
  messages.value.push({ role: 'user', content: text, apiContent: normalizedContext || text })
  input.value = ''
  loading.value = true

  // 发给后端的历史（不含即将占位的空回复），保留选项流转的结构化上下文
  const payload = messages.value.map(({ role, content, apiContent }) => ({
    role,
    content: apiContent || content,
  }))

  messages.value.push({ role: 'assistant', content: '', cards: [] })
  const index = messages.value.length - 1
  await scrollToBottom()

  try {
    const { job_id: jobId } = await createChatJob(payload)
    let shown = 0
    let completed = false
    while (!completed) {
      const job = await pollChatJob(jobId)
      if (job.progress && !job.reply) messages.value[index].progress = job.progress
      if (job.reply.length > shown) {
        for (const char of job.reply.slice(shown)) {
          messages.value[index].content += char
          shown += 1
          await new Promise((resolve) => setTimeout(resolve, 18))
        }
      }
      if (!suppressCards && job.cards?.length) messages.value[index].cards = job.cards
      if (job.status === 'failed') throw new Error(job.error || '生成失败')
      completed = job.status === 'completed'
      if (!completed) await new Promise((resolve) => setTimeout(resolve, 400))
    }
    return true
  } catch (err) {
    const errorMessage = getErrorMessage(err)
    messages.value[index].content = errorMessage.includes('Content Exists Risk')
      ? '本次请求未通过服务安全校验，请重试或换一种表述。'
      : `出错了：${errorMessage}`
    return false
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

function useStarter(text) {
  if (loading.value) return
  input.value = text
  send()
}

function selectTransport(msg, card) {
  if (loading.value) return
  msg.selectedCardId = card.id
}

function transportCards(msg) {
  return msg.cards?.filter((card) => card.type === 'transport_offer') || []
}

function hotelCards(msg) {
  return msg.cards?.filter((card) => card.type === 'hotel_offer') || []
}

function ticketCards(msg) {
  return msg.cards?.filter((card) => card.type === 'ticket_offer') || []
}

function canShowTickets(msg, index) {
  if (!ticketCards(msg).length) return false
  return messages.value.slice(0, index).some((item) => item.hotelSelectionConfirmed)
}

function allCardsByType(type) {
  const cards = []
  const seen = new Set()
  for (const msg of messages.value) {
    for (const card of msg.cards || []) {
      if (card.type !== type || seen.has(card.id)) continue
      seen.add(card.id)
      cards.push(card)
    }
  }
  return cards
}

const summarySections = computed(() => [
  {
    key: 'transport',
    title: '交通',
    cards: allCardsByType('transport_offer'),
    selectedIds: confirmedTransportId.value ? [confirmedTransportId.value] : (summaryDraft.value.transport ? [summaryDraft.value.transport] : []),
    locked: Boolean(confirmedTransportId.value),
  },
  {
    key: 'hotel',
    title: '酒店',
    cards: allCardsByType('hotel_offer'),
    selectedIds: confirmedHotelId.value ? [confirmedHotelId.value] : (summaryDraft.value.hotel ? [summaryDraft.value.hotel] : []),
    locked: Boolean(confirmedHotelId.value),
  },
  {
    key: 'ticket',
    title: '景点门票',
    cards: allCardsByType('ticket_offer'),
    selectedIds: confirmedTicketIds.value.length ? confirmedTicketIds.value : summaryDraft.value.ticket,
    locked: confirmedTicketIds.value.length > 0,
  },
])

function handleSummarySelect({ sectionKey, cardId }) {
  const section = summarySections.value.find((item) => item.key === sectionKey)
  if (!section || section.locked) return
  if (sectionKey === 'ticket') {
    summaryDraft.value.ticket = summaryDraft.value.ticket.includes(cardId)
      ? summaryDraft.value.ticket.filter((id) => id !== cardId)
      : [...summaryDraft.value.ticket, cardId]
    return
  }
  summaryDraft.value[sectionKey] = cardId
}

function selectedContext(label) {
  const source = [...messages.value].reverse().find((item) => item.apiContent?.includes(label))?.apiContent || ''
  const start = source.indexOf(label)
  if (start < 0) return null
  const jsonStart = source.indexOf('{', start)
  if (jsonStart < 0) return null
  try {
    return JSON.parse(source.slice(jsonStart, source.indexOf('。', jsonStart)))
  } catch {
    return null
  }
}

function selectHotel(msg, card) {
  if (loading.value || msg.hotelSelectionConfirmed) return
  msg.selectedHotelId = card.id
}

function selectTicket(msg, card) {
  if (loading.value || msg.ticketSelectionConfirmed) return
  const selectedIds = msg.selectedTicketIds || []
  msg.selectedTicketIds = selectedIds.includes(card.id)
    ? selectedIds.filter((id) => id !== card.id)
    : [...selectedIds, card.id]
}

async function continueWithTransport(msg) {
  if (loading.value || msg.selectionConfirmed) return
  const selected = msg.cards?.find((card) => card.id === msg.selectedCardId)
  if (!selected) {
    input.value = '未选择交通方案，进入下一项。请基于已确认的行程信息继续执行酒店推荐。'
    const succeeded = await send('未选择交通候选。现在只进入下一项，请直接搜索并展示多个酒店库存候选；如缺少必要行程信息，请一次只追问一个问题。')
    if (succeeded) msg.selectionConfirmed = true
    return
  }

  const transportName = selected.transport_type === 'train' ? '火车票方案' : '机票方案'
  const latestUserMessage = [...messages.value].reverse().find((item) => item.role === 'user')
  const importedChat = messages.value.find(
    (item) => item.role === 'user' && item.content.includes('【群聊记录】'),
  )
  const lodgingHints = importedChat?.content
    .split('\n')
    .filter((line) => /住|酒店|外滩|迪士尼附近|火车站附近/.test(line))
    .slice(0, 5)
    .join('；')
  const visibleMessage = `我已选择交通方案：${selected.title || transportName}；${selected.origin} → ${selected.destination}，去程 ${selected.departure_date} ${selected.departure_time} 出发，${selected.arrival_time} 到达，返程 ${selected.return_date}，总价 ¥${selected.total_price_yuan}（${selected.travelers} 人）。请基于以上已选交通方案执行酒店推荐。`
  const compactContext = [
    `行程ID：${selected.trip_id}。`,
    `已确认行程：${selected.origin}往返${selected.destination}，`,
    `${selected.departure_date}出发，${selected.return_date}返回，${selected.travelers}位出行人。`,
    `已选交通完整数据：${JSON.stringify(selected)}。`,
    latestUserMessage?.content ? `组织者最近确认：${latestUserMessage.content}。` : '',
    lodgingHints ? `群聊住宿偏好摘要：${lodgingHints}。` : '',
    `已选择${transportName}。现在只进入下一项，请直接搜索并展示多个酒店库存候选，不要再次追问住宿区域；如果没有区域偏好就使用热门商圈。`,
  ].join('')

  msg.selectionConfirmed = true
  await saveTripSelection(selected.trip_id, 'transport', selected)
  input.value = visibleMessage
  await nextTick()
  const succeeded = await send(compactContext)
  if (succeeded) confirmedTransportId.value = selected.id
  if (!succeeded) msg.selectionConfirmed = false
}

async function continueWithHotel(msg) {
  if (loading.value || msg.hotelSelectionConfirmed) return
  const selected = hotelCards(msg).find((card) => card.id === msg.selectedHotelId)
  if (!selected) {
    input.value = '未选择酒店方案，进入下一项。请基于已确认的行程信息继续执行景点/门票推荐。'
    const succeeded = await send('未选择酒店候选。现在只进入下一项，请推荐景点和门票候选；如缺少必要行程信息，请一次只追问一个问题。')
    if (succeeded) msg.hotelSelectionConfirmed = true
    return
  }

  msg.hotelSelectionConfirmed = true
  await saveTripSelection(selected.trip_id, 'hotel', selected)
  input.value = `我已选择酒店方案：${selected.title}；位置：${selected.location}，入住 ${selected.checkin_date}，离店 ${selected.checkout_date}，${selected.rooms} 间房，共 ${selected.nights} 晚，总价 ¥${selected.total_price_yuan}。请基于以上已选交通和酒店方案执行景点/门票推荐。`
  const context = `行程ID：${selected.trip_id}。已选择酒店完整数据：${JSON.stringify(selected)}。现在只进入下一项，请推荐景点和门票候选。`
  await nextTick()
  const succeeded = await send(context)
  if (succeeded) confirmedHotelId.value = selected.id
  if (!succeeded) msg.hotelSelectionConfirmed = false
}

async function continueWithTicket(msg) {
  if (loading.value || msg.ticketSelectionConfirmed) return
  const selected = ticketCards(msg).filter((card) => msg.selectedTicketIds?.includes(card.id))
  if (!selected.length) {
    const tripId = ticketCards(msg)[0]?.trip_id || ''
    input.value = '未选择门票，进入下一项。请生成旅行计划汇总。'
    const succeeded = await send(`行程ID：${tripId}。未选择门票候选。请基于已确认信息生成旅行计划汇总；未选择的交通、酒店、景点门票不要写成已确认项目。`, true)
    if (succeeded) {
      msg.ticketSelectionConfirmed = true
      confirmedTicketIds.value = []
      summaryLinkVisible.value = true
      appendSummaryLink()
    }
    return
  }

  msg.ticketSelectionConfirmed = true
  await Promise.all(selected.map((item) => saveTripSelection(item.trip_id, 'ticket', item)))
  const productNames = selected.map((card) => card.title).join('、')
  const hotel = selectedContext('已选择酒店完整数据：')
  const hotelSummary = hotel ? `已选酒店：${hotel.title}，${hotel.location}，${hotel.checkin_date}至${hotel.checkout_date}，${hotel.rooms}间房，总价¥${hotel.total_price_yuan}。` : ''
  input.value = `我已选择门票：${productNames}。${hotelSummary}请基于以上已选交通、酒店和门票方案生成完整行程草案。`
  const context = `行程ID：${selected[0].trip_id}。已选择门票完整数据：${JSON.stringify(selected)}。${hotel ? `已选择酒店完整数据：${JSON.stringify(hotel)}。` : ''}请记录全部选择，并根据已确认信息继续生成行程草案；缺少必要信息时一次只追问一个。`
  await nextTick()
  const succeeded = await send(context, true)
  if (succeeded) {
    confirmedTicketIds.value = selected.map((card) => card.id)
    summaryLinkVisible.value = true
    appendSummaryLink()
  }
  if (!succeeded) msg.ticketSelectionConfirmed = false
}

function openSummaryFromLink() {
  emit('open-summary', summarySections.value)
}

function appendSummaryLink() {
  const message = [...messages.value].reverse().find((item) => item.role === 'assistant' && item.content)
  if (message) message.summaryLink = true
}

function onKeydown(event) {
  // Enter 发送，Shift+Enter 换行
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    send()
  }
}

onMounted(async () => {
  const imported = props.initialMessage.trim()
  if (!imported) return
  input.value = imported
  await nextTick()
  send()
})
</script>

<template>
  <div class="chat">
    <div ref="listEl" class="list">
      <div v-if="!messages.length" class="empty">
        <strong>把群聊记录或出行想法发给我</strong>
        <span>我会依次确认人数、日期、城市和偏好，再规划交通、酒店、景点与ABC方案。</span>
        <div class="starter-list">
          <button v-for="text in starters" :key="text" class="starter" @click="useStarter(text)">
            {{ text }}
          </button>
        </div>
      </div>

      <div v-for="(msg, i) in messages" :key="i" class="row" :class="msg.role">
        <div class="message-stack">
          <div class="bubble" :class="{ 'typing-bubble': !msg.content }">
            <div v-if="msg.content" class="message-rich" v-html="formatMessage(msg.content)"></div>
            <span v-if="!msg.content" class="typing">{{ msg.progress || '' }}</span>
          </div>
          <div v-if="summaryLinkVisible && i === messages.length - 1" class="summary-link-message">
            <p>根据上面的选择，为你生成一份旅行计划汇总页面。</p>
            <a href="#trip-summary" @click.prevent="openSummaryFromLink">旅行计划汇总</a>
          </div>
          <div v-if="transportCards(msg).length" class="card-section-title">
            <strong>交通库存候选</strong>
            <span>{{ transportCards(msg).length }} 个方案可对比</span>
          </div>
          <div v-if="transportCards(msg).length" class="offer-grid">
            <TransportCard
              v-for="card in transportCards(msg)"
              :key="card.id"
              :card="card"
              :selected="msg.selectedCardId === card.id"
              @select="selectTransport(msg, card)"
            />
          </div>
          <div v-if="transportCards(msg).length" class="choice-bar">
            <span v-if="msg.selectedCardId">
              {{ msg.selectionConfirmed ? '已提交所选交通方案' : '已选择一个交通方案' }}
            </span>
            <span v-else>请先选择一个交通方案</span>
            <button
              class="next-button"
              type="button"
              :disabled="loading || msg.selectionConfirmed"
              @click="continueWithTransport(msg)"
            >
              {{ msg.selectionConfirmed ? '已进入下一项' : '进入下一项' }}
              <b v-if="!msg.selectionConfirmed">›</b>
            </button>
          </div>

          <div v-if="hotelCards(msg).length" class="card-section-title">
            <strong>酒店库存候选</strong>
            <span>{{ hotelCards(msg).length }} 个方案可对比</span>
          </div>
          <div v-if="hotelCards(msg).length" class="offer-grid">
            <HotelCard
              v-for="card in hotelCards(msg)"
              :key="card.id"
              :card="card"
              :selected="msg.selectedHotelId === card.id"
              @select="selectHotel(msg, card)"
            />
          </div>
          <div v-if="hotelCards(msg).length" class="choice-bar">
            <span v-if="msg.selectedHotelId">
              {{ msg.hotelSelectionConfirmed ? '已提交所选酒店' : '已选择一个酒店方案' }}
            </span>
            <span v-else>请先选择一个酒店方案</span>
            <button
              class="next-button"
              type="button"
              :disabled="loading || msg.hotelSelectionConfirmed"
              @click="continueWithHotel(msg)"
            >
              {{ msg.hotelSelectionConfirmed ? '已进入下一项' : '进入下一项' }}
              <b v-if="!msg.hotelSelectionConfirmed">›</b>
            </button>
          </div>

          <div v-if="canShowTickets(msg, i)" class="card-section-title">
            <strong>景点门票库存候选</strong>
            <span>{{ ticketCards(msg).length }} 个产品可对比</span>
          </div>
          <div v-if="canShowTickets(msg, i)" class="offer-grid">
            <TicketCard
              v-for="card in ticketCards(msg)"
              :key="card.id"
              :card="card"
              :selected="msg.selectedTicketIds?.includes(card.id)"
              @select="selectTicket(msg, card)"
            />
          </div>
          <div v-if="canShowTickets(msg, i) && !msg.ticketSelectionConfirmed" class="choice-bar">
            <span v-if="msg.selectedTicketIds?.length">
              {{ msg.ticketSelectionConfirmed ? '已提交所选门票' : `已选择 ${msg.selectedTicketIds.length} 个门票产品` }}
            </span>
            <span v-else>请先选择一个门票产品</span>
            <button
              class="next-button"
              type="button"
              :disabled="loading || msg.ticketSelectionConfirmed"
              @click="continueWithTicket(msg)"
            >
              {{ msg.ticketSelectionConfirmed ? '已进行汇总' : '进行汇总' }}
              <b v-if="!msg.ticketSelectionConfirmed">›</b>
            </button>
          </div>
        </div>
      </div>

    </div>

    <div class="composer">
      <textarea
        v-model="input"
        rows="1"
        placeholder="粘贴群聊或描述行程，Enter 发送"
        :disabled="loading"
        @keydown="onKeydown"
      ></textarea>
      <button class="primary send-button" :disabled="loading || !input.trim()" @click="send()">
        {{ loading ? '生成中' : '发送' }}
      </button>
    </div>
    <button v-if="props.showOrderButton" class="order-button" type="button">下单</button>
  </div>
</template>

<style scoped>
.chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.summary-link-message {
  margin: 0 8px;
  padding: 12px 14px;
  border-radius: 10px;
  background: var(--assistant-bubble);
  color: var(--text);
  font-size: 14px;
  line-height: 1.6;
}

.summary-link-message p {
  margin: 0 0 6px;
}

.summary-link-message a {
  color: var(--primary);
  text-decoration: underline;
  cursor: pointer;
}

.order-button {
  width: calc(100% - 28px);
  height: 44px;
  margin: 10px 14px 14px;
  border: 0;
  border-radius: 6px;
  color: #fff;
  background: var(--primary);
  font-size: 15px;
  cursor: pointer;
}

.list {
  flex: 1;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  padding: 20px 22px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.empty {
  margin: auto;
  color: var(--text-muted);
  font-size: 13px;
  max-width: 520px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 10px;
  line-height: 1.6;
}

.empty strong {
  color: var(--text);
  font-size: 17px;
}

.starter-list {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
  margin-top: 4px;
}

.starter {
  padding: 7px 11px;
  color: var(--primary);
  background: #f5f7ff;
  border-color: #dce3ff;
  font-size: 12px;
}

.row {
  display: flex;
}

.row.user {
  justify-content: flex-end;
}

.message-stack {
  max-width: 76%;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.row.user .message-stack {
  align-items: flex-end;
}

.row.assistant .message-stack {
  width: 100%;
  max-width: 94%;
}

.bubble {
  max-width: 100%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.row.user .bubble {
  background: var(--user-bubble);
  color: #fff;
}

.row.assistant .bubble {
  background: var(--assistant-bubble);
}

.row.assistant .bubble.typing-bubble {
  width: fit-content;
  min-width: 82px;
  align-self: flex-start;
  padding: 9px 13px;
}

.card-section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.card-section-title strong {
  font-size: 13px;
}

.card-section-title span {
  color: var(--text-muted);
  font-size: 11px;
}

.offer-grid {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(2, minmax(260px, 1fr));
  gap: 10px;
}

.choice-bar {
  width: 100%;
  min-height: 44px;
  padding: 8px 10px 8px 13px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid #e1e6ef;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 4px 14px rgba(38, 56, 92, 0.05);
}

.choice-bar span {
  color: var(--text-muted);
  font-size: 12px;
}

.next-button {
  flex: 0 0 auto;
  padding: 7px 13px;
  border: 0;
  border-radius: 8px;
  color: #fff;
  background: #20a05a;
  font-size: 12px;
}

.next-button b {
  margin-left: 4px;
  font-size: 15px;
}

.typing {
  color: var(--text-muted);
}

.message-rich :deep(h2),
.message-rich :deep(h3),
.message-rich :deep(h4) {
  margin: 10px 0 5px;
  line-height: 1.35;
}

.message-rich :deep(h2) {
  font-size: 17px;
}

.message-rich :deep(h3) {
  font-size: 15px;
}

.message-rich :deep(h4) {
  font-size: 14px;
}

.message-rich :deep(.md-list) {
  padding-left: 2px;
}

.message-rich :deep(.md-gap) {
  height: 8px;
}

.message-rich :deep(hr) {
  margin: 10px 0;
  border: 0;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
}

.message-rich :deep(.md-table-wrap) {
  margin: 8px 0;
  overflow-x: auto;
}

.message-rich :deep(table) {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.message-rich :deep(th),
.message-rich :deep(td) {
  padding: 6px 7px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  text-align: left;
  vertical-align: top;
}

.message-rich :deep(th) {
  background: rgba(255, 255, 255, 0.6);
  white-space: nowrap;
}

.composer {
  border-top: 1px solid var(--border);
  padding: 12px 22px 16px;
  padding-bottom: calc(12px + var(--safe-bottom));
  display: flex;
  align-items: flex-end;
  gap: 10px;
  background: var(--panel);
}

textarea {
  flex: 1;
  min-width: 0;
  min-height: 42px;
  max-height: 112px;
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 10px 12px;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.5;
  resize: none;
  outline: none;
}

textarea:focus {
  border-color: var(--primary);
}

button {
  border-radius: 8px;
  padding: 7px 18px;
  font-size: 13px;
  cursor: pointer;
  border: 1px solid transparent;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.primary {
  background: var(--primary);
  color: #fff;
}

.send-button {
  flex: 0 0 auto;
  min-width: 72px;
  height: 42px;
  padding: 0 18px;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .list {
    padding: 16px 14px;
    gap: 12px;
  }

  .message-stack {
    max-width: 82%;
  }

  .row.assistant .message-stack {
    max-width: 100%;
  }

  .bubble {
    font-size: 15px;
  }

  .offer-grid {
    grid-template-columns: 1fr;
  }

  .choice-bar {
    min-height: 48px;
  }

  .composer {
    padding: 10px 14px;
    padding-bottom: calc(10px + var(--safe-bottom));
    /* 键盘弹起时表单不被遮挡 */
    background: var(--panel);
  }

  textarea {
    font-size: 16px; /* 16px 可避免 iOS 聚焦时自动放大 */
  }

  button {
    padding: 10px 20px;
    font-size: 14px;
  }

  .send-button {
    min-width: 64px;
    height: 42px;
    padding: 0 14px;
  }
}
</style>
