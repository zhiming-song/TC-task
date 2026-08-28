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
const tierLabel = computed(() => ({
  economic: '经济型',
  balanced: '舒适型',
  comfort: '品质型',
}[props.card.tier] || '酒店'))
</script>

<template>
  <article class="hotel-card" :class="{ selected, recommended }" @click="emit('select')">
    <header class="rec-head">
      <span class="rec-num">{{ numberText }}</span>
      <strong class="rec-reason">{{ reason }}</strong>
      <span v-if="recommended" class="rec-best">AI推荐</span>
    </header>

    <div class="hotel-main">
      <img
        v-if="card.image_url"
        class="hotel-img"
        :src="card.image_url"
        :alt="card.title"
        loading="lazy"
      />

      <div class="hotel-info">
        <strong class="hotel-name">{{ card.title }}</strong>
        <span class="hotel-meta">{{ card.location }} · {{ tierLabel }} · 评分 {{ card.rating }}</span>
        <span class="hotel-stay">{{ card.checkin_date }} 入住 · {{ card.checkout_date }} 离店 · {{ card.rooms }}间 × {{ card.nights }}晚</span>
      </div>

      <div class="price-block">
        <span class="price-label">参考价</span>
        <strong class="price">¥{{ card.unit_price_yuan }}</strong>
        <span class="per-night">每间每晚</span>
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
.hotel-card {
  overflow: hidden;
  border: 1px solid #e4e8ee;
  border-radius: 12px;
  color: #20232a;
  background: #fff;
  box-shadow: 0 4px 14px rgba(38, 56, 92, 0.05);
  cursor: pointer;
}

.hotel-card.selected {
  border-color: #27a65a;
  box-shadow: 0 0 0 2px rgba(39, 166, 90, 0.13), 0 6px 18px rgba(38, 56, 92, 0.08);
}

.hotel-card.recommended {
  border-color: #ff8a00;
  box-shadow: 0 0 0 2px rgba(255, 138, 0, 0.14), 0 6px 18px rgba(255, 138, 0, 0.08);
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

.rec-best {
  flex: 0 0 auto;
  padding: 2px 7px;
  border-radius: 9px;
  color: #fff;
  background: linear-gradient(135deg, #ff8a00, #ff5e2d);
  font-size: 10px;
}

.hotel-main {
  padding: 4px 13px 11px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 10px;
}

.hotel-img {
  width: 74px;
  height: 56px;
  flex: 0 0 74px;
  border-radius: 8px;
  object-fit: cover;
  background: #f2f4f7;
}

.hotel-info {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.hotel-name {
  font-size: 14px;
  font-weight: 600;
}

.hotel-meta {
  color: #8d94a0;
  font-size: 11px;
}

.hotel-stay {
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
.per-night {
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
