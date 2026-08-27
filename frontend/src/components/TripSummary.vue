<script setup>
import { ref, computed, reactive } from 'vue'

const props = defineProps({
  sections: {
    type: Array,
    required: true,
  },
  tripInfo: {
    type: Object,
    default: () => ({
      title: '国庆上海冲冲冲',
      origin: '北京',
      destination: '上海',
      dates: '10.01 - 10.03',
      travelers: 5,
      groupName: '国庆上海冲冲冲',
    }),
  },
  aiSummary: {
    type: String,
    default: '已分析聊天记录 · 小北要迪士尼 · 程程想外滩 · Evan省预算',
  },
})

const emit = defineEmits(['select-section-item', 'confirm', 'defer'])

// 群友颜色映射
const userColors = {
  林一: '#FF8A1F', Evan: '#2E7BE6', 小北: '#7C5CFC',
  程程: '#00B86C', Dora: '#FF5E94',
}
const userShort = { 林一: '林', Evan: 'E', 小北: '北', 程程: '程', Dora: 'D' }
const allUsers = ['林一', 'Evan', '小北', '程程', 'Dora']

// 当前用户投票（用于追踪本地交互）
const myVotes = reactive({
  transport: null,
  hotel: null,
  ticket: null,
})

// 投票状态（key = section key, value = array of voter names）
const voteState = reactive({
  transport: ['小北', 'Dora'],  // flight-A 已有2票
  hotel: ['林一', 'Evan'],       // hotel-B 已有2票
  ticket: ['小北', 'Dora', '林一'], // ticket-1 已有3票
})

// 更新投票数据（供外部调用）
function updateVoteData(sectionKey, cardId, voters) {
  voteState[sectionKey] = voters || []
}

// 暴露给父组件
defineExpose({ updateVoteData })

// 是否锁定（AI已确认）
function isLocked(section) {
  return section.selectedIds && section.selectedIds.length > 0
}

// 是否已选（基于当前用户投票）
function isSelected(section, card) {
  return myVotes[section.key] === card.id
}

// 获取卡片已投票的人
function getVoters(section, card) {
  if (section.key === 'transport') {
    return voteState.transport
  }
  if (section.key === 'hotel') {
    return voteState.hotel
  }
  if (section.key === 'ticket') {
    return voteState.ticket
  }
  return []
}

// 获取某卡片的投票数
function getVoteCount(section, card) {
  return getVoters(section, card).length
}

// 获取总投票数
const totalVoted = computed(() => {
  const all = [...voteState.transport, ...voteState.hotel, ...voteState.ticket]
  return new Set(all).size
})

// 卡片标题
function cardTitle(card) {
  return card.title || card.name || card.attraction_name || card.service_label || card.id
}

// 交通详情
function getTransportDetail(card) {
  const parts = []
  if (card.departure_time) parts.push(card.departure_time)
  if (card.arrival_time) parts.push(card.arrival_time)
  if (card.duration_minutes) {
    const h = Math.floor(card.duration_minutes / 60)
    const m = card.duration_minutes % 60
    parts.push(`${h}h${m > 0 ? m + 'm' : ''}`)
  }
  if (card.flight_type) parts.push(card.flight_type)
  if (card.seat_class) parts.push(card.seat_class)
  return parts.join(' · ')
}

// 酒店详情
function getHotelSpec(card) {
  const parts = []
  if (card.room_type) parts.push(card.room_type)
  if (card.room_size) parts.push(card.room_size)
  if (card.bed_type) parts.push(card.bed_type)
  parts.push(`可入住${card.capacity || 2}人`)
  return parts.join(' · ')
}

// 景点详情
function getTicketDetail(card) {
  const parts = []
  if (card.category) parts.push(card.category)
  if (card.duration_hours) parts.push(`建议${card.duration_hours}小时`)
  if (card.opening_hours) parts.push(card.opening_hours)
  return parts.join(' · ')
}

// 处理卡片点击
function handleCardClick(section, card) {
  if (isLocked(section)) return
  handleVote(section, card)
}

// 处理投票
function handleVote(section, card) {
  if (isLocked(section)) return
  
  // 切换投票
  if (myVotes[section.key] === card.id) {
    // 取消投票
    myVotes[section.key] = null
  } else {
    // 投票
    myVotes[section.key] = card.id
  }
  
  // 通知父组件
  emit('select-section-item', { sectionKey: section.key, cardId: myVotes[section.key] })
}

// 确认投票
function confirmVote() {
  emit('confirm')
}

// 稍后决定
function deferDecision() {
  emit('defer')
}

// 计算节省金额
function getSavings(original, current) {
  if (!original || !current) return 0
  return Math.round(original - current)
}

// 服务标签颜色
function getServiceClass(svc) {
  if (svc.includes('确认') || svc.includes('免押')) return 'svc-orange'
  if (svc.includes('提前') || svc.includes('含早') || svc.includes('含餐')) return 'svc-blue'
  if (svc.includes('取消') || svc.includes('退')) return 'svc-gray'
  return 'svc-green'
}
</script>

<template>
  <div class="summary-page">
    <!-- 标题区 -->
    <div class="header">
      <h1 class="header-title">{{ tripInfo.title }}</h1>
      <p class="header-subtitle">AI 综合分析群聊偏好，给出最佳方案推荐</p>
      <div class="header-meta">
        <div class="header-meta-item">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="4" width="18" height="18" rx="2"/>
            <line x1="16" y1="2" x2="16" y2="6"/>
            <line x1="8" y1="2" x2="8" y2="6"/>
            <line x1="3" y1="10" x2="21" y2="10"/>
          </svg>
          {{ tripInfo.dates }}
        </div>
        <div class="header-meta-item">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
            <circle cx="9" cy="7" r="4"/>
          </svg>
          {{ tripInfo.travelers }} 人出行
        </div>
        <div class="header-meta-item">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
            <circle cx="12" cy="10" r="3"/>
          </svg>
          {{ tripInfo.origin }} → {{ tripInfo.destination }}
        </div>
      </div>
    </div>

    <!-- 群友条 -->
    <div class="people-bar">
      <div class="people-left">
        <div class="people-avatars">
          <div class="people-avatar p1">林</div>
          <div class="people-avatar p2">E</div>
          <div class="people-avatar p3">北</div>
          <div class="people-avatar p4">程</div>
          <div class="people-avatar p5">D</div>
        </div>
        <span class="people-text">来自 <strong>{{ tripInfo.groupName }}</strong> 群</span>
      </div>
      <span class="people-text vote-status">投票中 {{ totalVoted }}/{{ tripInfo.travelers }}</span>
    </div>

    <!-- AI 综合说明 -->
    <div class="ai-summary">
      <div class="ai-summary-icon">AI</div>
      <div class="ai-summary-text">{{ aiSummary }}</div>
    </div>

    <!-- 各模块 -->
    <template v-for="section in sections" :key="section.key">

      <!-- 交通模块 -->
      <div v-if="section.key === 'transport' && section.cards.length" class="module">
        <div class="module-title">
          <div class="module-title-text">
            <svg class="module-title-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z"/>
            </svg>
            交通 · {{ section.cards.length }} 个方案
          </div>
          <div class="module-filter">综合考虑时间和价格</div>
        </div>

        <div
          v-for="card in section.cards"
          :key="card.id"
          class="trans"
          :class="{ selected: isSelected(section, card), locked: isLocked(section) }"
          @click="handleCardClick(section, card)"
        >
          <div v-if="isSelected(section, card) && card.recommended" class="selected-tag">{{ isLocked(section) ? '已确认' : 'AI 推' }}</div>
          <div v-else-if="isSelected(section, card)" class="selected-tag">{{ isLocked(section) ? '已确认' : '已选' }}</div>
          <div class="trans-icon">
            <svg v-if="card.transport_type === 'train'" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="4" y="3" width="16" height="16" rx="2"/>
              <path d="M4 11h16"/>
              <path d="M12 3v8"/>
              <path d="m8 19-2 3"/>
              <path d="m18 22-2-3"/>
            </svg>
            <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z"/>
            </svg>
          </div>
          <div class="trans-info">
            <div class="trans-name">{{ cardTitle(card) }}</div>
            <div class="trans-detail">
              {{ getTransportDetail(card) }} · {{ card.origin }} → {{ card.destination }}
            </div>
          </div>
          <div class="trans-right">
            <div class="trans-price-block">
              <div v-if="card.original_price_yuan && Number(card.original_price_yuan) > Number(card.unit_price_yuan)" class="trans-price-original">
                ¥{{ card.original_price_yuan }}
              </div>
              <div class="trans-price-num">¥{{ card.unit_price_yuan }}<small>起</small></div>
            </div>
            <!-- 投票栏 -->
            <div class="vote-bar compact">
              <div class="vote-voters">
                <div
                  v-for="(voter, idx) in allUsers"
                  :key="idx"
                  class="vote-voter"
                  :class="{ empty: !getVoters(section, card).includes(voter) }"
                  :style="getVoters(section, card).includes(voter) ? { background: userColors[voter] } : {}"
                >{{ userShort[voter] }}</div>
              </div>
              <div class="vote-count">{{ getVoteCount(section, card) }}票</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 酒店模块 -->
      <div v-if="section.key === 'hotel' && section.cards.length" class="module">
        <div class="module-title">
          <div class="module-title-text">
            <svg class="module-title-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 21h18"/>
              <path d="M5 21V7l8-4v18"/>
              <path d="M19 21V11l-6-4"/>
            </svg>
            酒店 · {{ section.cards.length }} 个方案
          </div>
          <div class="module-filter">AI 综合偏好推荐</div>
        </div>

        <div
          v-for="card in section.cards"
          :key="card.id"
          class="room"
          :class="{ selected: isSelected(section, card), locked: isLocked(section) }"
          @click="handleCardClick(section, card)"
        >
          <div v-if="isSelected(section, card) && card.recommended" class="selected-tag">{{ isLocked(section) ? '已确认' : 'AI 推' }}</div>
          <div v-else-if="isSelected(section, card)" class="selected-tag">{{ isLocked(section) ? '已确认' : '已选' }}</div>
          <div class="room-top">
            <div class="room-img">
              <img
                :src="`https://picsum.photos/seed/${card.id}/200/200`"
                :alt="cardTitle(card)"
                loading="lazy"
              />
              <span class="room-img-tag">{{ card.image_count || 4 }} 图</span>
            </div>
            <div class="room-info">
              <h3 class="room-name">{{ cardTitle(card) }}</h3>
              <div class="room-spec">{{ getHotelSpec(card) }}</div>
              <div class="room-cancel">{{ card.cancel_policy || '入住前可免费取消' }}</div>
              <div class="room-services">
                <span v-for="svc in (card.services || ['立即确认', '免押金'])" :key="svc" class="room-service" :class="getServiceClass(svc)">{{ svc }}</span>
              </div>
            </div>
          </div>
          <div class="room-bottom">
            <div class="room-promo">
              <span v-if="card.distance_km" class="room-promo-tag">距景区 {{ card.distance_km }}km</span>
              <span class="room-promo-tag">{{ card.rating || 4.5 }} 分</span>
            </div>
            <div class="room-price-block">
              <div v-if="card.original_price_yuan && Number(card.original_price_yuan) > Number(card.unit_price_yuan)" class="room-price-original">
                ¥{{ card.original_price_yuan }}
              </div>
              <div class="room-price-main">
                <span class="room-price"><small>¥</small>{{ card.unit_price_yuan }}</span>
                <span v-if="card.original_price_yuan && Number(card.original_price_yuan) > Number(card.unit_price_yuan)" class="room-price-saved">已优惠 ¥{{ getSavings(card.original_price_yuan, card.unit_price_yuan) }}</span>
              </div>
              <div class="room-price-unit">/晚</div>
            </div>
          </div>
          <!-- 投票栏 -->
          <div class="vote-bar">
            <div class="vote-left">
              <div class="vote-voters">
                <div
                  v-for="(voter, idx) in allUsers"
                  :key="idx"
                  class="vote-voter"
                  :class="{ empty: !getVoters(section, card).includes(voter) }"
                  :style="getVoters(section, card).includes(voter) ? { background: userColors[voter] } : {}"
                >{{ userShort[voter] }}</div>
              </div>
              <div class="vote-count"><strong>{{ getVoteCount(section, card) }}</strong>人投票</div>
            </div>
            <button class="vote-btn" :class="{ voted: isSelected(section, card) }" @click.stop="handleVote(section, card)">
              {{ isSelected(section, card) ? '已投' : '投票' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 景点门票模块 -->
      <div v-if="section.key === 'ticket' && section.cards.length" class="module">
        <div class="module-title">
          <div class="module-title-text">
            <svg class="module-title-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M2 9V6a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v3a2 2 0 1 0 0 6v3a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-3a2 2 0 1 0 0-6z"/>
            </svg>
            景区门票 · {{ section.cards.length }} 个方案
          </div>
          <div class="module-filter">已选高性价比</div>
        </div>

        <div
          v-for="card in section.cards"
          :key="card.id"
          class="ticket"
          :class="{ selected: isSelected(section, card), locked: isLocked(section) }"
          @click="handleCardClick(section, card)"
        >
          <div class="ticket-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M2 9V6a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v3a2 2 0 1 0 0 6v3a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-3a2 2 0 1 0 0-6z"/>
            </svg>
          </div>
          <div class="ticket-info">
            <div class="ticket-name">{{ cardTitle(card) }}</div>
            <div class="ticket-detail">{{ getTicketDetail(card) }}</div>
          </div>
          <div class="ticket-right">
            <div class="ticket-price-block">
              <div v-if="card.original_price_yuan && Number(card.original_price_yuan) > Number(card.unit_price_yuan)" class="ticket-price-original">
                ¥{{ card.original_price_yuan }}
              </div>
              <div class="ticket-price-num">¥{{ card.unit_price_yuan }}<small>起</small></div>
            </div>
            <!-- 投票栏 -->
            <div class="vote-bar compact">
              <div class="vote-voters">
                <div
                  v-for="(voter, idx) in allUsers"
                  :key="idx"
                  class="vote-voter"
                  :class="{ empty: !getVoters(section, card).includes(voter) }"
                  :style="getVoters(section, card).includes(voter) ? { background: userColors[voter] } : {}"
                >{{ userShort[voter] }}</div>
              </div>
              <div class="vote-count">{{ getVoteCount(section, card) }}票</div>
            </div>
          </div>
        </div>
      </div>

    </template>

    <!-- 底部操作栏 -->
    <div class="action-bar">
      <button class="btn-cancel" @click="deferDecision">稍后决定</button>
      <button class="btn-primary" @click="confirmVote">投票确认</button>
    </div>
  </div>
</template>

<style scoped>
/* ============ 变量 ============ */
.summary-page {
  --tc-orange: #FF6B1A;
  --tc-orange-dark: #E5570D;
  --tc-orange-soft: #FFF1E8;
  --tc-red: #FF4D4F;
  --tc-green: #00B576;
  --tc-green-soft: #E5F8EF;

  --u-林一: #FF8A1F;
  --u-Evan: #2E7BE6;
  --u-小北: #7C5CFC;
  --u-程程: #00B86C;
  --u-Dora: #FF5E94;

  --text-1: #1A1A1A;
  --text-2: #5A5A5A;
  --text-3: #999999;
  --text-4: #BFBFBF;
  --line: #EEEEEE;
  --line-soft: #F5F5F5;
  --bg: #F6F6F6;

  font-family: 'Outfit', -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
  background: var(--bg);
  color: var(--text-1);
  font-size: 14px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  min-height: 100vh;
  padding-bottom: 90px;
}

/* ============ 标题区 ============ */
.header {
  background: #fff;
  padding: 12px 16px 16px;
  border-bottom: 1px solid var(--line);
}
.header-title {
  font-size: 19px;
  font-weight: 700;
  color: var(--text-1);
  margin: 0 0 4px;
  line-height: 1.3;
}
.header-subtitle {
  font-size: 12.5px;
  color: var(--text-2);
  margin: 0;
}
.header-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 10px;
  font-size: 12px;
  color: var(--text-2);
  flex-wrap: wrap;
}
.header-meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* ============ 群友条 ============ */
.people-bar {
  background: #fff;
  margin: 8px 12px 0;
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.people-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.people-avatars { display: flex; align-items: center; }
.people-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  color: #fff;
  margin-left: -6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  border: 1.5px solid #fff;
}
.people-avatar:first-child { margin-left: 0; }
.p1 { background: var(--u-林一); }
.p2 { background: var(--u-Evan); }
.p3 { background: var(--u-小北); }
.p4 { background: var(--u-程程); }
.p5 { background: var(--u-Dora); }
.people-text { font-size: 12px; color: var(--text-2); }
.people-text strong { color: var(--text-1); font-weight: 600; }
.vote-status { color: var(--tc-orange); font-weight: 600; }

/* ============ AI 说明 ============ */
.ai-summary {
  background: #fff;
  margin: 8px 12px 0;
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  color: var(--text-2);
}
.ai-summary-icon {
  width: 18px;
  height: 18px;
  background: var(--tc-orange);
  color: #fff;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  font-weight: 800;
  flex-shrink: 0;
}
.ai-summary-text strong { color: var(--text-1); font-weight: 600; }

/* ============ 模块 ============ */
.module {
  background: #fff;
  margin: 8px 12px 0;
  border-radius: 8px;
  padding: 14px;
}
.module-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-1);
  margin: 0 0 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.module-title-text {
  display: flex;
  align-items: center;
  gap: 6px;
}
.module-title-icon {
  width: 18px;
  height: 18px;
  color: var(--tc-orange);
}
.module-filter {
  font-size: 12px;
  color: var(--text-2);
  font-weight: 400;
}

/* ============ 交通卡片 ============ */
.trans {
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 8px;
  background: #fff;
  position: relative;
  transition: all 0.2s;
  cursor: pointer;
}
.trans:last-child { margin-bottom: 0; }
.trans.selected {
  border-color: var(--tc-orange);
  background: var(--tc-orange-soft);
}
.trans.locked { cursor: not-allowed; opacity: 0.85; }
.trans-icon {
  width: 36px;
  height: 36px;
  background: var(--tc-orange-soft);
  color: var(--tc-orange);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.trans.selected .trans-icon {
  background: var(--tc-orange);
  color: #fff;
}
.trans-info { flex: 1; min-width: 0; }
.trans-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-1);
  margin-bottom: 2px;
}
.trans-detail {
  font-size: 11.5px;
  color: var(--text-2);
}
.trans-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}
.trans-price-block {
  text-align: right;
}
.trans-price-original {
  text-decoration: line-through;
  color: var(--text-3);
  font-size: 11px;
  margin-bottom: 1px;
}
.trans-price-num {
  font-size: 18px;
  font-weight: 800;
  color: var(--tc-red);
  line-height: 1;
}
.trans-price-num small {
  font-size: 11px;
  font-weight: 600;
}

/* 选中标记 */
.selected-tag {
  position: absolute;
  top: -8px;
  left: 12px;
  background: var(--tc-orange);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 8px 8px 8px 2px;
}

/* ============ 酒店卡片 ============ */
.room {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 8px;
  background: #fff;
  position: relative;
  transition: all 0.2s;
  cursor: pointer;
}
.room:last-child { margin-bottom: 0; }
.room.selected {
  border-color: var(--tc-orange);
  background: var(--tc-orange-soft);
}
.room.locked { cursor: not-allowed; opacity: 0.85; }
.room-top {
  display: flex;
  gap: 10px;
}
.room-img {
  width: 92px;
  height: 92px;
  border-radius: 6px;
  flex-shrink: 0;
  background: var(--line-soft);
  position: relative;
  overflow: hidden;
}
.room-img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.room-img-tag {
  position: absolute;
  bottom: 4px;
  right: 4px;
  background: rgba(0,0,0,0.55);
  color: #fff;
  font-size: 9px;
  padding: 1px 5px;
  border-radius: 3px;
  font-weight: 600;
}
.room-info {
  flex: 1;
  min-width: 0;
}
.room-name {
  font-size: 14.5px;
  font-weight: 700;
  color: var(--text-1);
  margin: 0 0 4px;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-clamp: 2;
}
.room-spec {
  font-size: 12px;
  color: var(--text-2);
  margin-bottom: 4px;
}
.room-cancel {
  font-size: 11.5px;
  color: var(--text-2);
  margin-bottom: 6px;
}
.room-services {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.room-service {
  font-size: 10.5px;
  padding: 1px 5px;
  border-radius: 3px;
  font-weight: 500;
}
.svc-orange { color: var(--tc-orange); border: 0.5px solid var(--tc-orange); }
.svc-green { color: var(--tc-green); border: 0.5px solid var(--tc-green); }
.svc-blue { color: #2E7BE6; border: 0.5px solid #2E7BE6; }
.svc-gray { color: var(--text-2); border: 0.5px solid var(--text-4); }

.room-bottom {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--line);
}
.room-promo {
  display: flex;
  align-items: center;
  gap: 4px;
}
.room-promo-tag {
  font-size: 10px;
  color: var(--tc-red);
  border: 0.5px solid var(--tc-red);
  padding: 1px 4px;
  border-radius: 3px;
  font-weight: 600;
}
.room-price-block {
  text-align: right;
}
.room-price-original {
  text-decoration: line-through;
  color: var(--text-3);
  font-size: 12px;
  margin-right: 6px;
  display: inline;
}
.room-price-main {
  display: flex;
  align-items: baseline;
  justify-content: flex-end;
  gap: 6px;
}
.room-price {
  font-size: 22px;
  font-weight: 800;
  color: var(--tc-red);
  line-height: 1;
}
.room-price small { font-size: 12px; font-weight: 600; }
.room-price-saved {
  font-size: 11px;
  color: var(--tc-red);
}
.room-price-unit {
  font-size: 11px;
  color: var(--text-2);
  margin-top: 2px;
}

/* ============ 投票栏 ============ */
.vote-bar {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--line);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.vote-bar.compact {
  margin-top: 0;
  padding-top: 0;
  border-top: none;
}
.vote-left {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
}
.vote-voters { display: flex; align-items: center; }
.vote-voter {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  color: #fff;
  margin-left: -5px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  font-weight: 700;
  border: 1.5px solid #fff;
}
.vote-voter:first-child { margin-left: 0; }
.vote-voter.empty {
  background: #fff;
  border: 1.5px dashed var(--text-4);
  color: transparent;
}
.vote-count {
  font-size: 11.5px;
  color: var(--text-2);
  margin-left: 8px;
}
.vote-count strong {
  color: var(--tc-orange);
  font-size: 13px;
  font-weight: 800;
}
.vote-btn {
  padding: 5px 12px;
  border-radius: 14px;
  font-size: 12px;
  font-weight: 600;
  border: 0.5px solid var(--tc-orange);
  background: #fff;
  color: var(--tc-orange);
  cursor: pointer;
  font-family: inherit;
  transition: all 0.2s;
}
.vote-btn:active { transform: scale(0.95); }
.vote-btn.voted {
  background: var(--tc-orange);
  color: #fff;
}

/* ============ 门票卡片 ============ */
.ticket {
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 8px;
  background: #fff;
  position: relative;
  transition: all 0.2s;
  cursor: pointer;
}
.ticket:last-child { margin-bottom: 0; }
.ticket.selected {
  border-color: var(--tc-orange);
  background: var(--tc-orange-soft);
}
.ticket.locked { cursor: not-allowed; opacity: 0.85; }
.ticket-icon {
  width: 36px;
  height: 36px;
  background: var(--tc-orange-soft);
  color: var(--tc-orange);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.ticket.selected .ticket-icon {
  background: var(--tc-orange);
  color: #fff;
}
.ticket-info { flex: 1; min-width: 0; }
.ticket-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-1);
  margin-bottom: 2px;
}
.ticket-detail {
  font-size: 11.5px;
  color: var(--text-2);
}
.ticket-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}
.ticket-price-block {
  text-align: right;
}
.ticket-price-original {
  text-decoration: line-through;
  color: var(--text-3);
  font-size: 11px;
  margin-bottom: 1px;
}
.ticket-price-num {
  font-size: 18px;
  font-weight: 800;
  color: var(--tc-red);
  line-height: 1;
}
.ticket-price-num small {
  font-size: 11px;
  font-weight: 600;
}

/* ============ 底部操作栏 ============ */
.action-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  max-width: 420px;
  margin: 0 auto;
  background: #fff;
  border-top: 1px solid var(--line);
  padding: 10px 16px 22px;
  display: flex;
  align-items: center;
  gap: 10px;
  z-index: 10;
}
.btn-cancel {
  flex: 1;
  height: 44px;
  background: #fff;
  color: var(--text-2);
  border: 0.5px solid var(--text-4);
  border-radius: 22px;
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
}
.btn-primary {
  flex: 2;
  height: 44px;
  background: var(--tc-orange);
  color: #fff;
  border: none;
  border-radius: 22px;
  font-size: 14.5px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
}
.btn-cancel:active, .btn-primary:active {
  transform: scale(0.98);
}
</style>
