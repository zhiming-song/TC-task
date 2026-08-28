<script setup>
import { computed } from 'vue'

const props = defineProps({
  card: {
    type: Object,
    required: true,
  },
  selected: {
    type: Boolean,
    default: false,
  },
  recommended: {
    type: Boolean,
    default: false,
  },
  index: {
    type: Number,
    default: 1,
  },
  reason: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['select'])

const CIRCLED = ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩']
const isTrain = computed(() => props.card.transport_type === 'train')
const numberText = computed(() => CIRCLED[props.index - 1] || String(props.index))

const durationText = computed(() => {
  const minutes = Number(props.card.duration_minutes || 0)
  if (!minutes) return '待查询'
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return `${hours}小时${rest ? `${rest}分` : ''}`
})

// 火车展示单人单程价，航班展示单人往返总价
const priceText = computed(() => {
  const unit = Number(props.card.unit_price_yuan || 0)
  return isTrain.value ? `¥${unit}` : `¥${unit * 2}`
})
const priceLabel = computed(() => (isTrain.value ? '单人单程' : '往返总价'))
</script>

<template>
  <article
    class="transport-card"
    :class="[card.transport_type, { selected, recommended }]"
    @click="emit('select')"
  >
    <header class="rec-head">
        <span class="rec-num">{{ numberText }}</span>
        <div class="transport-name">
          <span class="transport-icon">{{ isTrain ? '🚄' : '✈️' }}</span>
          <div>
            <strong>{{ isTrain ? '火车票方案' : '机票方案' }}</strong>
            <span>{{ card.title }} · {{ card.service_label }}</span>
          </div>
        </div>
        <strong class="rec-reason">{{ reason }}</strong>
        <span v-if="recommended" class="rec-best">AI推荐</span>
      </header>

    <div class="route-line">
      <div>
        <strong>{{ card.departure_time || card.origin }}</strong>
        <span>{{ card.origin }} · {{ card.departure_date }}</span>
      </div>
      <div class="route-arrow">
        <span>{{ durationText }}</span>
        <i></i>
      </div>
      <div class="destination">
        <strong>{{ card.arrival_time || card.destination }}</strong>
        <span>{{ card.destination }} · 返 {{ card.return_date }}</span>
      </div>
    </div>

    <div class="inventory-line">
      <span>{{ card.seat_class }}</span>
      <span :class="{ limited: card.inventory_status === '紧张' }">
        余 {{ card.remaining_inventory }} · {{ card.inventory_status }}
      </span>
    </div>

    <div class="card-metrics">
      <div>
        <span>方案</span>
        <strong>{{ isTrain ? '高铁往返' : '航班往返' }}</strong>
      </div>
      <div>
        <span>{{ card.travelers }}人往返</span>
        <strong>¥{{ card.total_price_yuan }}</strong>
      </div>
      <div class="price">
        <span>{{ priceLabel }}</span>
        <strong>{{ priceText }}</strong>
      </div>
    </div>

    <div class="card-action">
      <span>{{ card.bookable ? '可携带当前条件进入预订' : '需在同程重新确认班次与价格' }}</span>
      <div class="action-buttons">
        <button class="select-button" :class="{ active: selected }" type="button" @click.stop="emit('select')">
          {{ selected ? '✓ 已选择' : '选择此方案' }}
        </button>
        <a :href="card.booking_url" target="_blank" rel="noopener noreferrer">
          {{ card.cta_label }}
          <b>›</b>
        </a>
      </div>
    </div>
  </article>
</template>

<style scoped>
.transport-card {
  overflow: hidden;
  border: 1px solid #dfe5f1;
  border-radius: 14px;
  color: #20232a;
  background: #fff;
  box-shadow: 0 6px 20px rgba(38, 56, 92, 0.07);
  cursor: pointer;
}

.transport-card.train {
  border-top: 3px solid #4278ed;
}

.transport-card.flight {
  border-top: 3px solid #7357df;
}

.transport-card.selected {
  border-color: #27a65a;
  box-shadow: 0 0 0 2px rgba(39, 166, 90, 0.13), 0 8px 22px rgba(38, 56, 92, 0.09);
}

.transport-card.recommended {
  border-color: #f0a020;
  box-shadow: 0 0 0 2px rgba(240, 160, 32, 0.15), 0 8px 22px rgba(38, 56, 92, 0.09);
}

.rec-best {
  flex: 0 0 auto;
  padding: 4px 10px;
  border-radius: 12px;
  color: #fff;
  background: linear-gradient(135deg, #f0a020, #f5c842);
  font-size: 11px;
  font-weight: 600;
}

.rec-head {
  padding: 12px 13px 9px;
  display: flex;
  align-items: center;
  gap: 9px;
}

.rec-num {
  flex: 0 0 auto;
  color: #f05a29;
  font-size: 15px;
}

.rec-reason {
  flex: 1;
  min-width: 0;
  color: #8b93a3;
  font-size: 10px;
  font-weight: 400;
  text-align: right;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.transport-name {
  display: flex;
  align-items: center;
  gap: 9px;
  flex: 1;
  min-width: 0;
}

.transport-icon {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: #f0f5ff;
  font-size: 18px;
}

.flight .transport-icon {
  background: #f4f0ff;
}

.transport-name div {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.transport-name strong {
  font-size: 14px;
}

.transport-name div span {
  color: #8b93a3;
  font-size: 10px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.route-line {
  padding: 4px 16px 9px;
  display: grid;
  grid-template-columns: 1fr 74px 1fr;
  align-items: center;
}

.route-line > div:not(.route-arrow) {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.route-line strong {
  font-size: 18px;
}

.route-line span {
  color: #8d94a0;
  font-size: 10px;
}

.destination {
  align-items: flex-end;
}

.route-arrow {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.route-arrow i {
  position: relative;
  width: 54px;
  height: 1px;
  background: #b8c2d3;
}

.route-arrow i::after {
  content: '';
  position: absolute;
  right: -1px;
  top: -3px;
  width: 6px;
  height: 6px;
  border-top: 1px solid #b8c2d3;
  border-right: 1px solid #b8c2d3;
  transform: rotate(45deg);
}

.inventory-line {
  padding: 0 13px 9px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #677184;
  font-size: 10px;
}

.inventory-line span:last-child {
  padding: 3px 7px;
  border-radius: 10px;
  color: #168444;
  background: #eaf8ef;
}

.inventory-line span.limited {
  color: #b96a00;
  background: #fff3da;
}

.card-metrics {
  padding: 10px 13px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  border-top: 1px solid #edf0f5;
  background: #fafbfc;
}

.card-metrics div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.card-metrics span {
  color: #9298a3;
  font-size: 9px;
}

.card-metrics strong {
  font-size: 12px;
}

.card-metrics .price {
  align-items: flex-end;
}

.card-metrics .price strong {
  color: #f05a29;
  font-size: 15px;
}

.card-action {
  padding: 9px 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  border-top: 1px solid #edf0f5;
}

.card-action > span {
  min-width: 0;
  overflow: hidden;
  color: #9a9fa8;
  font-size: 9px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.action-buttons {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 6px;
}

.select-button {
  padding: 5px 9px;
  border: 1px solid #cad3e3;
  border-radius: 14px;
  color: #536174;
  background: #fff;
  font-family: inherit;
  font-size: 11px;
  cursor: pointer;
}

.select-button.active {
  border-color: #27a65a;
  color: #168444;
  background: #eaf8ef;
  font-weight: 600;
}

.card-action a {
  flex: 0 0 auto;
  padding: 6px 10px;
  border-radius: 14px;
  color: #fff;
  background: #4f72e8;
  font-size: 11px;
  font-weight: 600;
  text-decoration: none;
}

.flight .card-action a {
  background: #6d57d9;
}

.card-action b {
  margin-left: 3px;
  font-size: 15px;
  line-height: 10px;
}

@media (max-width: 560px) {
  .card-action {
    align-items: center;
  }

  .rec-head {
    flex-wrap: wrap;
  }

  .rec-reason {
    flex-basis: 100%;
    text-align: left;
  }
}
</style>