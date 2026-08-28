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
  variant: {
    type: String,
    default: '',
  },
  welcomeText: {
    type: String,
    default: '',
  },
  initialContext: {
    type: String,
    default: '',
  },
})

const isDeeptrip = computed(() => props.variant === 'deeptrip')

const messages = ref([])
const input = ref('')
const loading = ref(false)
const listEl = ref(null)
const starters = [
  '我想规划一次多人旅行',
  '帮我整理这段群聊里的出行需求',
  '北京出发去上海，5人，玩3天',
]

// 导入流程：AI 首次回复视为必要信息整理完成，展示「确认」按钮
const isImportFlow = computed(() => props.initialMessage.trim() !== '')
const infoOrganized = ref(false)
const infoConfirmed = ref(false)
const canConfirmInfo = computed(
  () => isImportFlow.value && infoOrganized.value && !infoConfirmed.value && !loading.value,
)

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

async function send(contextContent = '') {
  const text = input.value.trim()
  if (!text || loading.value) return false

  const normalizedContext = typeof contextContent === 'string' ? contextContent : ''
  messages.value.push({ role: 'user', content: text, apiContent: normalizedContext || text })
  input.value = ''
  return runJob()
}

async function runJob() {
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
      if (job.cards?.length) messages.value[index].cards = job.cards
      if (job.status === 'failed') throw new Error(job.error || '生成失败')
      completed = job.status === 'completed'
      if (!completed) await new Promise((resolve) => setTimeout(resolve, 400))
    }
    if (isImportFlow.value && !infoOrganized.value) infoOrganized.value = true
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

async function confirmTripInfo() {
  if (loading.value || infoConfirmed.value) return
  infoConfirmed.value = true
  const confirmText = '信息确认无误，请开始推荐交通方案'
  input.value = confirmText
  await nextTick()
  const succeeded = await send(confirmText)
  if (!succeeded) infoConfirmed.value = false
}

/**
 * 拆分助手回复中的结构化标记：
 * - 以「◎ 」开头的行 → 可点击的查询选项；
 * - 以「【推荐方案ID】」开头的行 → 系统标记（AI 选中的最佳方案 id），不展示给用户。
 *
 * @param {string} content 助手回复原文。
 * @return {{ chips: string[], recommendedId: string, body: string }} 选项、推荐方案 id 与去标记后的正文。
 */
function splitMeta(content) {
  const chips = []
  const body = []
  let recommendedId = ''
  for (const line of content.split('\n')) {
    const trimmed = line.trim()
    if (trimmed.startsWith('【推荐方案ID】')) {
      const match = trimmed.match(/^【推荐方案ID】\s*(\S+)\s*$/)
      if (match) recommendedId = match[1]
      continue
    }
    const chipMatch = trimmed.match(/^◎\s*(.+)$/)
    if (chipMatch) chips.push(chipMatch[1])
    else body.push(line)
  }
  return { chips, recommendedId, body: body.join('\n') }
}

function metaParts(msg) {
  return splitMeta(msg.content)
}

function isRecommendedCard(card, msg) {
  const recommendedId = metaParts(msg).recommendedId
  if (!recommendedId) return false
  return (card.id || '').split(':').pop() === recommendedId
}

async function runChip(chipText) {
  if (loading.value) return
  input.value = chipText
  await nextTick()
  send(chipText)
}

function transportReason(card, list) {
  if (list.length < 2) return '推荐方案'
  const lowest = Math.min(...list.map((item) => Number(item.unit_price_yuan) || Number.MAX_SAFE_INTEGER))
  const earliest = list.map((item) => item.departure_time || '99:99').sort()[0]
  const fastest = Math.min(...list.map((item) => Number(item.duration_minutes) || Number.MAX_SAFE_INTEGER))
  if (Number(card.unit_price_yuan) === lowest) return '票价最低，预算友好'
  if (card.departure_time === earliest) return '出发最早，上午就到'
  if (Number(card.duration_minutes) === fastest) return '全程最快，省时省心'
  return '性价比均衡'
}

function hotelReason(card, list) {
  if (list.length < 2) return '推荐酒店'
  const lowest = Math.min(...list.map((item) => Number(item.unit_price_yuan) || Number.MAX_SAFE_INTEGER))
  const best = Math.max(...list.map((item) => Number(item.rating) || 0))
  if (Number(card.unit_price_yuan) === lowest) return '价格最低，预算友好'
  if (Number(card.rating) === best) return '口碑最佳，品质有保障'
  return '位置均衡，出行方便'
}

function ticketReason(card, list) {
  if (list.length < 2) return '推荐景点'
  const cheapest = Math.min(...list.map((item) => Number(item.unit_price_yuan) || Number.MAX_SAFE_INTEGER))
  const longest = Math.max(...list.map((item) => Number(item.duration_hours) || 0))
  if (Number(card.unit_price_yuan) === cheapest) return '票价最低，性价比高'
  if (Number(card.duration_hours) === longest) return '可玩最久，内容充实'
  return '人气必去，经典之选'
}

function selectTransport(msg, card) {
  if (loading.value || msg.selectionConfirmed) return
  msg.selectedCardId = card.id
}

function transportCards(msg) {
  return msg.cards?.filter((card) => card.type === 'transport_offer') || []
}

function trainCards(msg) {
  return transportCards(msg).filter((card) => card.transport_type === 'train')
}

function flightCards(msg) {
  return transportCards(msg).filter((card) => card.transport_type === 'flight')
}

function hotelCards(msg) {
  return msg.cards?.filter((card) => card.type === 'hotel_offer') || []
}

function ticketCards(msg) {
  return msg.cards?.filter((card) => card.type === 'ticket_offer') || []
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
    // 未选择具体方案也可以进入下一项，按 AI 推荐继续
    const anyCard = msg.cards?.find((card) => card.type === 'transport_offer')
    msg.selectionConfirmed = true
    input.value = '无需指定交通方案，请直接进入酒店推荐'
    const context = `行程ID：${anyCard?.trip_id || ''}。交通方案未明确选择，请直接搜索并推荐酒店候选，结合群聊分歧挑出3家并给出推荐理由。`
    await nextTick()
    const succeeded = await send(context)
    if (!succeeded) msg.selectionConfirmed = false
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
  if (!succeeded) msg.selectionConfirmed = false
}

async function continueWithHotel(msg) {
  if (loading.value || msg.hotelSelectionConfirmed) return
  const selected = hotelCards(msg).find((card) => card.id === msg.selectedHotelId)
  if (!selected) {
    // 未选择具体酒店也可以进入下一项，按 AI 推荐继续
    const anyCard = msg.cards?.find((card) => card.type === 'hotel_offer')
    msg.hotelSelectionConfirmed = true
    input.value = '酒店无需指定，请直接进入景点门票推荐'
    const context = `行程ID：${anyCard?.trip_id || ''}。酒店未明确选择，请直接推荐景点和门票候选。`
    await nextTick()
    const succeeded = await send(context)
    if (!succeeded) msg.hotelSelectionConfirmed = false
    return
  }

  msg.hotelSelectionConfirmed = true
  await saveTripSelection(selected.trip_id, 'hotel', selected)
  input.value = `我已选择酒店方案：${selected.title}；位置：${selected.location}，入住 ${selected.checkin_date}，离店 ${selected.checkout_date}，${selected.rooms} 间房，共 ${selected.nights} 晚，总价 ¥${selected.total_price_yuan}。请基于以上已选交通和酒店方案执行景点/门票推荐。`
  const context = `行程ID：${selected.trip_id}。已选择酒店完整数据：${JSON.stringify(selected)}。现在只进入下一项，请推荐景点和门票候选。`
  await nextTick()
  const succeeded = await send(context)
  if (!succeeded) msg.hotelSelectionConfirmed = false
}

async function continueWithTicket(msg) {
  if (loading.value || msg.ticketSelectionConfirmed) return
  const selected = ticketCards(msg).filter((card) => msg.selectedTicketIds?.includes(card.id))
  if (!selected.length) return

  msg.ticketSelectionConfirmed = true
  await Promise.all(selected.map((item) => saveTripSelection(item.trip_id, 'ticket', item)))
  const productNames = selected.map((card) => card.title).join('、')
  input.value = `我选择${productNames}，请记录产品选择并继续生成行程草案。`
  const context = `行程ID：${selected[0].trip_id}。已选择门票完整数据：${JSON.stringify(selected)}。请记录选择，并根据已确认信息继续生成行程草案；缺少必要信息时一次只追问一个。`
  await nextTick()
  const succeeded = await send(context)
  if (!succeeded) msg.ticketSelectionConfirmed = false
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
  const instructions = props.initialContext.trim()
  // 指令仅发给后端，不展示在用户消息气泡中
  messages.value.push({
    role: 'user',
    content: imported,
    apiContent: instructions ? `${imported}\n\n${instructions}` : imported,
  })
  await nextTick()
  runJob()
})
</script>

<template>
  <div class="chat">
    <div ref="listEl" class="list">
      <div v-if="!messages.length && !isDeeptrip" class="empty">
        <strong>把群聊记录或出行想法发给我</strong>
        <span>我会依次确认人数、日期、城市和偏好，再规划交通、酒店、景点与ABC方案。</span>
        <div class="starter-list">
          <button v-for="text in starters" :key="text" class="starter" @click="useStarter(text)">
            {{ text }}
          </button>
        </div>
        <small>价格与库存以预订时为准。</small>
      </div>

      <div v-if="welcomeText" class="row assistant">
        <div class="message-stack">
          <div class="bubble">{{ welcomeText }}</div>
        </div>
      </div>

      <div v-for="(msg, i) in messages" :key="i" class="row" :class="msg.role">
        <div class="message-stack">
          <div v-if="isDeeptrip && !msg.content" class="dt-status">{{ msg.progress || '正在规划行程' }}</div>
          <div v-else class="bubble" :class="{ 'typing-bubble': !msg.content }">
            <div v-if="msg.content" class="message-rich" v-html="formatMessage(metaParts(msg).body)"></div>
            <span v-else class="typing">{{ msg.progress || '思考中…' }}</span>
          </div>
          <div v-if="msg.content && metaParts(msg).chips.length" class="chip-list">
            <button
              v-for="chip in metaParts(msg).chips"
              :key="chip"
              class="query-chip"
              type="button"
              :disabled="loading"
              @click="runChip(chip)"
            >
              ◎ {{ chip }}
            </button>
          </div>
          <div v-if="trainCards(msg).length" class="card-section-title">
            <strong>高铁方案</strong>
            <span>{{ trainCards(msg).length }} 个方案可对比</span>
          </div>
          <div v-if="trainCards(msg).length" class="train-list">
            <TransportCard
              v-for="(card, i) in trainCards(msg)"
              :key="card.id"
              :card="card"
              :index="i + 1"
              :reason="transportReason(card, trainCards(msg))"
              :recommended="isRecommendedCard(card, msg)"
              :selected="msg.selectedCardId === card.id"
              @select="selectTransport(msg, card)"
            />
          </div>

          <div v-if="flightCards(msg).length" class="card-section-title">
            <strong>航班方案</strong>
            <span>横向滑动查看 {{ flightCards(msg).length }} 个方案</span>
          </div>
          <div v-if="flightCards(msg).length" class="flight-scroll">
            <div v-for="(card, i) in flightCards(msg)" :key="card.id" class="flight-cell">
              <TransportCard
                :card="card"
                :index="i + 1"
                :reason="transportReason(card, flightCards(msg))"
                :recommended="isRecommendedCard(card, msg)"
                :selected="msg.selectedCardId === card.id"
                @select="selectTransport(msg, card)"
              />
            </div>
          </div>
          <p v-if="transportCards(msg).length" class="ai-disclaimer">内容由程心AI生成，仅供参考</p>
          <div v-if="transportCards(msg).length" class="choice-bar">
            <span v-if="msg.selectedCardId">
              {{ msg.selectionConfirmed ? '已提交所选交通方案' : '已选择一个交通方案' }}
            </span>
            <span v-else>未选择将按 AI 推荐继续</span>
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
            <strong>酒店推荐</strong>
            <span>{{ hotelCards(msg).length }} 家酒店可对比</span>
          </div>
          <div v-if="hotelCards(msg).length" class="hotel-list">
            <HotelCard
              v-for="(card, i) in hotelCards(msg)"
              :key="card.id"
              :card="card"
              :index="i + 1"
              :reason="hotelReason(card, hotelCards(msg))"
              :recommended="isRecommendedCard(card, msg)"
              :selected="msg.selectedHotelId === card.id"
              @select="selectHotel(msg, card)"
            />
          </div>
          <div v-if="hotelCards(msg).length" class="choice-bar">
            <span v-if="msg.selectedHotelId">
              {{ msg.hotelSelectionConfirmed ? '已提交所选酒店' : '已选择一个酒店方案' }}
            </span>
            <span v-else>未选择将按 AI 推荐继续</span>
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

          <div v-if="ticketCards(msg).length" class="card-section-title">
            <strong>景点门票库存候选</strong>
            <span>{{ ticketCards(msg).length }} 个产品可对比</span>
          </div>
          <div v-if="ticketCards(msg).length" class="offer-grid">
            <TicketCard
              v-for="(card, i) in ticketCards(msg)"
              :key="card.id"
              :card="card"
              :index="i + 1"
              :reason="ticketReason(card, ticketCards(msg))"
              :recommended="isRecommendedCard(card, msg)"
              :selected="msg.selectedTicketIds?.includes(card.id)"
              @select="selectTicket(msg, card)"
            />
          </div>
          <div v-if="ticketCards(msg).length" class="choice-bar">
            <span v-if="msg.selectedTicketIds?.length">
              {{ msg.ticketSelectionConfirmed ? '已提交所选门票' : `已选择 ${msg.selectedTicketIds.length} 个门票产品` }}
            </span>
            <span v-else>请先选择一个门票产品</span>
            <button
              class="next-button"
              type="button"
              :disabled="loading || !msg.selectedTicketIds?.length || msg.ticketSelectionConfirmed"
              @click="continueWithTicket(msg)"
            >
              {{ msg.ticketSelectionConfirmed ? '已生成下一步' : '生成行程' }}
              <b v-if="!msg.ticketSelectionConfirmed">›</b>
            </button>
          </div>
        </div>
      </div>

      <div v-if="canConfirmInfo" class="row assistant">
        <div class="message-stack">
          <div class="confirm-bar">
            <button
              class="confirm-btn"
              :class="{ 'dt-brand': isDeeptrip }"
              type="button"
              @click="confirmTripInfo"
            >
              确认，开始推荐交通
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="isDeeptrip" class="composer dt-composer">
      <button class="dt-collect" type="button">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 3.5l2.7 5.5 6 .9-4.4 4.2 1.1 6-5.4-2.9-5.4 2.9 1.1-6L3.3 9.9l6-.9z" />
        </svg>
        <span>当前收藏</span>
      </button>
      <textarea
        v-model="input"
        rows="1"
        placeholder="发消息或按住说话."
        :disabled="loading"
        @keydown="onKeydown"
      ></textarea>
      <button class="dt-send" type="button" :disabled="loading || !input.trim()" @click="send()" aria-label="发送">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 19V5M6 11l6-6 6 6" />
        </svg>
      </button>
    </div>

    <div v-else class="composer">
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
  </div>
</template>

<style scoped>
.chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
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

.chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.query-chip {
  padding: 7px 12px;
  border: 1px solid #ffb08c;
  border-radius: 16px;
  color: #e8541f;
  background: #fff;
  font-size: 12px;
  cursor: pointer;
}

.query-chip:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ai-disclaimer {
  margin: -2px 0 0;
  color: #a4abb5;
  font-size: 11px;
  text-align: center;
}

.train-list,
.hotel-list {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.flight-scroll {
  width: 100%;
  display: flex;
  gap: 10px;
  overflow-x: auto;
  padding-bottom: 6px;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: thin;
}

.flight-cell {
  flex: 0 0 244px;
  max-width: 78%;
}

.confirm-bar {
  display: flex;
  justify-content: center;
  padding: 2px 0;
}

.confirm-btn {
  padding: 9px 24px;
  border: 0;
  border-radius: 20px;
  color: #fff;
  background: var(--primary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}

.confirm-btn.dt-brand {
  background: #ff5e2d;
}

/* DeepTrip 风格 */
.dt-status {
  align-self: flex-start;
  color: #999;
  font-size: 12px;
}

.dt-composer {
  align-items: center;
  gap: 8px;
}

.dt-collect {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 4px 6px;
  border: 0;
  background: transparent;
  color: #666;
  font-size: 10px;
  cursor: pointer;
}

.dt-collect svg {
  width: 20px;
  height: 20px;
  fill: none;
  stroke: #ff8a00;
  stroke-width: 1.6;
  stroke-linejoin: round;
}

.dt-composer textarea {
  min-height: 36px;
  border-color: transparent;
  border-radius: 18px;
  background: #f2f2f2;
}

.dt-send {
  flex: 0 0 auto;
  width: 34px;
  height: 34px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: #fff;
  background: #ff5e2d;
}

.dt-send svg {
  width: 17px;
  height: 17px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.dt-send:disabled {
  opacity: 0.4;
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
