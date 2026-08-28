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
      <strong class="rec-reason">{{ reason || card.title }}</strong>
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
        <span class="hotel-stay">
          {{ card.checkin_date }} 入住 · {{ card.checkout_date }} 离店 · {{ card.rooms }}间 × {{ card.nights }}晚
        </span>
        <span class="hotel-stock" :class="{ limited: card.inventory_status === '紧张' }">
          余 {{ card.remaining_inventory }} 间 · {{ card.inventory_status }}
        </span>
      </div>

      <div class="price-block">
        <span class="price-label">参考价</span>
        <div class="price-stack">
          <strong class="price">¥{{ card.unit_price_yuan }}</strong>
          <span class="per-night">每间每晚</span>
        </div>
        <span class="total-price">合计 ¥{{ card.total_price_yuan }}</span>
        <a
          class="book-btn"
          :href="card.booking_url"
          target="_blank"
          rel="noopener noreferrer"
          :title="card.cta_label"
          @click.stop
        >订</a>
      </div>
    </div>

    <div class="hotel-actions">
      <button
        class="select-btn"
        :class="{ active: selected }"
        type="button"
        @click.stop="emit('select')"
      >
        {{ selected ? '✓ 已选择' : '选择此酒店' }}
      </button>
      <a
        class="cta-link"
        :href="card.booking_url"
        target="_blank"
        rel="noopener noreferrer"
        @click.stop
      >{{ card.cta_label }} ›</a>
    </div>
  </article>
</template>

<style scoped>
.hotel-card {
  overflow: hidden;
  border: 1px solid #e4e8ee;
  border-top: 3px solid #19a777;
  border-radius: 12px;
  color: #20232a;
  background: #fff;
  box-shadow: 0 4px 14px rgba(38, 56, 92, 0.05);
  cursor: pointer;
}

.hotel-card.selected {
  border-color: #27a65a;
  box-shadow: 0 0 0 2px rgba(39, 166, 90, 0.13), 0 8px 22px rgba(38, 56, 92, 0.09);
}

.hotel-card.recommended {
  border-color: #ff8a00;
  box-shadow: 0 0 0 2px rgba(255, 138, 0, 0.14), 0 8px 22px rgba(38, 56, 92, 0.09);
}

.rec-head {
  padding: 11px 13px 9px;
  display: flex;
  align-items: center;
  gap: 7px;
  border-bottom: 1px solid #edf0f5;
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
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
  padding: 11px 13px;
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.hotel-img {
  width: 74px;
  height: 74px;
  flex: 0 0 74px;
  border-radius: 8px;
  object-fit: cover;
  background: #f2f4f7;
}

.hotel-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
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

.hotel-stock {
  align-self: flex-start;
  padding: 2px 7px;
  border-radius: 9px;
  color: #168444;
  background: #eaf8ef;
  font-size: 10px;
  margin-top: 2px;
}

.hotel-stock.limited {
  color: #b96a00;
  background: #fff3da;
}

.price-block {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.price-label,
.per-night,
.total-price {
  color: #9298a3;
  font-size: 10px;
}

.price-stack {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.price {
  color: #f05a29;
  font-size: 19px;
  font-weight: 700;
}

.total-price {
  color: #f05a29;
  font-weight: 600;
}

.book-btn {
  margin-top: 4px;
  padding: 6px 14px;
  border-radius: 14px;
  color: #fff;
  background: linear-gradient(135deg, #ff8a00, #ff5e2d);
  font-size: 12px;
  font-weight: 600;
  text-decoration: none;
}

.hotel-actions {
  padding: 8px 13px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  border-top: 1px solid #edf0f5;
  background: #fafbfc;
}

.select-btn {
  padding: 5px 12px;
  border: 1px solid #cad3e3;
  border-radius: 13px;
  color: #536174;
  background: #fff;
  font-family: inherit;
  font-size: 11px;
  cursor: pointer;
}

.select-btn.active {
  border-color: #27a65a;
  color: #168444;
  background: #eaf8ef;
  font-weight: 600;
}

.cta-link {
  padding: 5px 12px;
  border-radius: 13px;
  color: #fff;
  background: #19a777;
  font-size: 11px;
  font-weight: 600;
  text-decoration: none;
}
</style>
