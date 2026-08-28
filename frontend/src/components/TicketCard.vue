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
    <img
      v-if="card.image_url"
      class="ticket-img"
      :src="card.image_url"
      :alt="card.attraction_name || card.title"
      loading="lazy"
    />

    <header class="rec-head">
      <span class="rec-num">{{ numberText }}</span>
      <strong class="rec-reason">{{ reason }}</strong>
      <span v-if="recommended" class="rec-best">AI推荐</span>
    </header>

    <div class="ticket-main">
      <div class="ticket-info">
        <strong class="ticket-name">{{ card.title }}</strong>
        <span class="ticket-meta">{{ card.destination }} · {{ card.category }}</span>
        <span class="ticket-meta">建议游玩 {{ card.duration_hours }}小时 · {{ card.travelers }}人合计 ¥{{ card.total_price_yuan }}</span>
        <span class="ticket-open">{{ card.opening_hours }}</span>
        <span
          v-if="card.remaining_inventory !== undefined"
          class="ticket-inventory"
          :class="{ limited: card.inventory_status === '紧张' }"
        >
          余 {{ card.remaining_inventory }} · {{ card.inventory_status }}
        </span>
      </div>

      <div class="price-block">
        <span class="price-label">每人票价</span>
        <strong class="price">¥{{ card.unit_price_yuan }}</strong>
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

    <div class="ticket-action">
      <button
        :class="{ active: selected }"
        type="button"
        @click.stop="emit('select')"
      >
        {{ selected ? '✓ 已选择' : '选择此门票' }}
      </button>
      <a
        :href="card.booking_url"
        target="_blank"
        rel="noopener noreferrer"
        @click.stop
      >{{ card.cta_label }} ›</a>
    </div>
  </article>
</template>

<style scoped>
.ticket-card {
  overflow: hidden;
  border: 1px solid #e4e8ee;
  border-top: 3px solid #ef8c34;
  border-radius: 14px;
  color: #20232a;
  background: #fff;
  box-shadow: 0 6px 20px rgba(38, 56, 92, 0.07);
  cursor: pointer;
  transition: box-shadow 0.18s ease, border-color 0.18s ease;
}

.ticket-card:hover {
  box-shadow: 0 8px 22px rgba(38, 56, 92, 0.1);
}

.ticket-card.selected {
  border-color: #27a65a;
  box-shadow: 0 0 0 2px rgba(39, 166, 90, 0.13), 0 8px 22px rgba(38, 56, 92, 0.09);
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
  border-bottom: 1px solid #edf0f5;
}

.rec-num {
  flex: 0 0 auto;
  color: #ff5e2d;
  font-size: 15px;
  font-weight: 700;
}

.rec-reason {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  font-size: 13px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rec-best {
  flex: 0 0 auto;
  padding: 3px 9px;
  border-radius: 10px;
  color: #fff;
  background: linear-gradient(135deg, #ff8a00, #ff5e2d);
  font-size: 10px;
  font-weight: 600;
}

.ticket-main {
  padding: 10px 13px 11px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.ticket-info {
  min-width: 0;
  flex: 1;
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

.ticket-inventory {
  align-self: flex-start;
  padding: 3px 7px;
  border-radius: 9px;
  color: #168444;
  background: #eaf8ef;
  font-size: 10px;
  margin-top: 4px;
}

.ticket-inventory.limited {
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

.price-label {
  color: #9298a3;
  font-size: 10px;
}

.price {
  color: #f05a29;
  font-size: 19px;
  font-weight: 700;
  line-height: 1;
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
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.book-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(255, 138, 0, 0.3);
}

.ticket-action {
  padding: 9px 13px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  border-top: 1px solid #edf0f5;
  background: #fafbfc;
}

.ticket-action button,
.ticket-action a {
  padding: 5px 12px;
  border-radius: 13px;
  font-family: inherit;
  font-size: 11px;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.15s ease;
}

.ticket-action button {
  border: 1px solid #cad3e3;
  color: #536174;
  background: #fff;
}

.ticket-action button:hover {
  border-color: #27a65a;
  color: #168444;
}

.ticket-action button.active {
  border-color: #27a65a;
  color: #168444;
  background: #eaf8ef;
  font-weight: 600;
}

.ticket-action a {
  color: #fff;
  background: #ef8c34;
}

.ticket-action a:hover {
  background: #ff8a00;
}
</style>