<script setup>
import { computed } from 'vue'

const props = defineProps({
  card: { type: Object, required: true },
  selected: { type: Boolean, default: false },
  recommended: { type: Boolean, default: false },
  index: { type: Number, default: 1 },
  reason: { type: String, default: '' },
})

const emit = defineEmits(['select'])

const CIRCLED = ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩']
const numberText = computed(() => CIRCLED[props.index - 1] || String(props.index))
</script>

<template>
  <article class="ticket-card" :class="{ selected, recommended }" @click="emit('select')">
    <img v-if="card.image_url" class="ticket-img" :src="card.image_url" :alt="card.attraction_name" loading="lazy" />

    <header class="rec-head">
      <span class="rec-num">{{ numberText }}</span>
      <strong class="rec-reason">{{ reason }}</strong>
      <span v-if="recommended" class="rec-best">AI推荐</span>
    </header>

    <div class="ticket-main">
      <div class="ticket-info">
        <strong class="ticket-name">{{ card.title }}</strong>
        <span class="ticket-meta">{{ card.destination }} · {{ card.category }} · 建议游玩 {{ card.duration_hours }}小时</span>
        <span class="ticket-open">{{ card.opening_hours }}</span>
      </div>

      <div class="price-block">
        <span class="price-label">{{ card.travelers }}人合计</span>
        <strong class="price">¥{{ card.unit_price_yuan }}</strong>
        <span class="per-person">每人票价</span>
        <a
          class="book-btn"
          :href="card.booking_url"
          target="_blank"
          rel="noopener noreferrer"
          :title="card.cta_label"
        >订</a>
      </div>
    </div>
  </article>
</template>

<style scoped>
.ticket-card {
  overflow: hidden;
  border: 1px solid #e4e8ee;
  border-radius: 12px;
  color: #20232a;
  background: #fff;
  box-shadow: 0 4px 14px rgba(38, 56, 92, 0.05);
  cursor: pointer;
}

.ticket-card.selected {
  border-color: #27a65a;
  box-shadow: 0 0 0 2px rgba(39, 166, 90, 0.13), 0 6px 18px rgba(38, 56, 92, 0.08);
}

.ticket-card.recommended {
  border-color: #ff8a00;
  box-shadow: 0 0 0 2px rgba(255, 138, 0, 0.14), 0 6px 18px rgba(255, 138, 0, 0.08);
}

.ticket-img {
  width: 100%;
  height: 130px;
  display: block;
  object-fit: cover;
  background: #f2f4f7;
}

.rec-head {
  padding: 10px 13px 8px;
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

.rec-best {
  flex: 0 0 auto;
  padding: 2px 7px;
  border-radius: 9px;
  color: #fff;
  background: linear-gradient(135deg, #ff8a00, #ff5e2d);
  font-size: 10px;
}

.ticket-main {
  padding: 2px 13px 11px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 10px;
}

.ticket-info {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.ticket-name {
  font-size: 14px;
  font-weight: 600;
}

.ticket-meta {
  color: #8d94a0;
  font-size: 11px;
}

.ticket-open {
  color: #a4abb5;
  font-size: 10px;
}

.price-block {
  flex: 0 0 auto;
  display: flex;
  align-items: flex-end;
  justify-content: flex-end;
  gap: 6px;
}

.price-label,
.per-person {
  align-self: center;
  color: #9298a3;
  font-size: 10px;
}

.price {
  color: #f05a29;
  font-size: 19px;
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
