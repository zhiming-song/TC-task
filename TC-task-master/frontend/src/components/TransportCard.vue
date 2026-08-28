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
  return `${hours}时${rest ? `${rest}分` : ''}`
})
// 火车展示单人单程价，航班展示单人往返总价
const priceText = computed(() => {
  const unit = Number(props.card.unit_price_yuan || 0)
  return isTrain.value ? `¥${unit}` : `¥${unit * 2}`
})
const priceLabel = computed(() => (isTrain.value ? '单人单程' : '往返总价'))
</script>

<template>
  <article class="transport-card" :class="[card.transport_type, { selected, recommended }]" @click="emit('select')">
    <header class="rec-head">
      <span class="rec-num">{{ numberText }}</span>
      <strong class="rec-reason">{{ reason }}</strong>
      <span v-if="recommended" class="rec-best">AI推荐</span>
    </header>

    <div class="route-block">
      <div class="route-row">
        <span class="leg-tag">{{ isTrain ? '单程' : '往返' }}</span>
        <span class="route-date">{{ card.departure_date }}</span>
        <strong class="dep-time">{{ card.departure_time }}</strong>
        <span class="duration">{{ durationText }}</span>
        <strong class="arr-time">{{ card.arrival_time }}</strong>
      </div>
      <div class="route-stations">
        <span>{{ card.origin }}</span>
        <span class="service-no">{{ card.service_label }}</span>
        <span>{{ card.destination }}</span>
      </div>
    </div>

    <div class="price-block">
      <span class="price-label">{{ priceLabel }}</span>
      <strong class="price">{{ priceText }}</strong>
      <span class="seat">{{ card.seat_class }}</span>
      <a
        class="book-btn"
        :href="card.booking_url"
        target="_blank"
        rel="noopener noreferrer"
        :title="card.cta_label"
      >订</a>
    </div>
  </article>
</template>

<style scoped>
.transport-card {
  overflow: hidden;
  border: 1px solid #e4e8ee;
  border-radius: 12px;
  color: #20232a;
  background: #fff;
  box-shadow: 0 4px 14px rgba(38, 56, 92, 0.05);
  cursor: pointer;
}

.transport-card.selected {
  border-color: #27a65a;
  box-shadow: 0 0 0 2px rgba(39, 166, 90, 0.13), 0 6px 18px rgba(38, 56, 92, 0.08);
}

.transport-card.recommended {
  border-color: #ff8a00;
  box-shadow: 0 0 0 2px rgba(255, 138, 0, 0.14), 0 6px 18px rgba(255, 138, 0, 0.08);
}

.rec-best {
  flex: 0 0 auto;
  padding: 2px 7px;
  border-radius: 9px;
  color: #fff;
  background: linear-gradient(135deg, #ff8a00, #ff5e2d);
  font-size: 10px;
}

.rec-head {
  padding: 11px 13px 9px;
  display: flex;
  align-items: center;
  gap: 7px;
}

.rec-num {
  flex: 0 0 auto;
  color: #ff5e2d;
  font-size: 15px;
}

.rec-reason {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  font-weight: 600;
}

.route-block {
  padding: 4px 13px 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.route-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.leg-tag {
  flex: 0 0 auto;
  padding: 2px 7px;
  border-radius: 9px;
  color: #8a6a00;
  background: #fff6dd;
  font-size: 10px;
}

.route-date {
  color: #8d94a0;
  font-size: 11px;
}

.dep-time,
.arr-time {
  font-size: 18px;
  line-height: 1.1;
}

.duration {
  flex: 1;
  color: #9aa1ab;
  font-size: 11px;
  text-align: center;
}

.route-stations {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: #677184;
  font-size: 11px;
}

.service-no {
  flex: 1;
  color: #a4abb5;
  font-size: 10px;
  text-align: center;
}

.price-block {
  padding: 10px 13px;
  display: flex;
  align-items: flex-end;
  justify-content: flex-end;
  gap: 6px;
  border-top: 1px solid #f0f2f6;
  background: #fafbfd;
}

.price-label {
  align-self: center;
  color: #9298a3;
  font-size: 10px;
}

.price {
  color: #f05a29;
  font-size: 19px;
}

.seat {
  align-self: center;
  color: #8d94a0;
  font-size: 11px;
}

.book-btn {
  margin-left: 4px;
  padding: 6px 14px;
  border-radius: 14px;
  color: #fff;
  background: linear-gradient(135deg, #ff8a00, #ff5e2d);
  font-size: 12px;
  font-weight: 600;
  text-decoration: none;
}
</style>
