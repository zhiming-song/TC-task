<script setup>
const props = defineProps({
  card: { type: Object, required: true },
  selected: { type: Boolean, default: false },
})

const emit = defineEmits(['select'])
</script>

<template>
  <article class="ticket-card" :class="{ selected }">
    <div class="ticket-head">
      <span class="ticket-icon">🎫</span>
      <div>
        <strong>{{ card.title }}</strong>
        <span>{{ card.destination }} · {{ card.category }}</span>
      </div>
      <span class="mode-badge">{{ card.realtime ? '实时' : 'Mock' }}</span>
    </div>

    <div class="ticket-info">
      <div><span>建议游玩</span><strong>{{ card.duration_hours }}小时</strong></div>
      <div><span>{{ card.travelers }}人合计</span><strong>¥{{ card.total_price_yuan }}</strong></div>
      <div class="price"><span>每人票价</span><strong>¥{{ card.unit_price_yuan }}</strong></div>
    </div>

    <div class="opening">{{ card.opening_hours }}</div>

    <div class="ticket-action">
      <span :class="{ limited: card.inventory_status === '紧张' }">
        {{ card.realtime ? '余' : 'Mock余量' }} {{ card.remaining_inventory }} · {{ card.inventory_status }}
      </span>
      <div>
        <button :class="{ active: selected }" type="button" @click="emit('select')">
          {{ selected ? '✓ 已选择' : '选择此门票' }}
        </button>
        <a :href="card.booking_url" target="_blank" rel="noopener noreferrer">{{ card.cta_label }} ›</a>
      </div>
    </div>
  </article>
</template>

<style scoped>
.ticket-card {
  overflow: hidden;
  border: 1px solid #dfe5f1;
  border-top: 3px solid #ef8c34;
  border-radius: 14px;
  color: #20232a;
  background: #fff;
  box-shadow: 0 6px 20px rgba(38, 56, 92, 0.07);
}

.ticket-card.selected {
  border-color: #27a65a;
  box-shadow: 0 0 0 2px rgba(39, 166, 90, 0.13), 0 8px 22px rgba(38, 56, 92, 0.09);
}

.ticket-head {
  padding: 11px 13px;
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) auto;
  align-items: center;
  gap: 9px;
}

.ticket-icon {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: #fff4e8;
  font-size: 18px;
}

.ticket-head div { min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.ticket-head strong { overflow: hidden; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.ticket-head div span { color: #8b93a3; font-size: 10px; }
.mode-badge { padding: 3px 7px; border-radius: 10px; color: #9a6700; background: #fff5cc; font-size: 10px; }

.ticket-info {
  padding: 10px 13px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  border-top: 1px solid #edf0f5;
  background: #fafbfc;
}

.ticket-info div { display: flex; flex-direction: column; gap: 2px; }
.ticket-info span { color: #9298a3; font-size: 9px; }
.ticket-info strong { font-size: 12px; }
.ticket-info .price { align-items: flex-end; }
.ticket-info .price strong { color: #f05a29; font-size: 15px; }
.opening { padding: 7px 13px; overflow: hidden; color: #858c98; font-size: 9px; text-overflow: ellipsis; white-space: nowrap; }

.ticket-action {
  padding: 9px 11px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  border-top: 1px solid #edf0f5;
}

.ticket-action > span { padding: 3px 6px; border-radius: 9px; color: #168444; background: #eaf8ef; font-size: 9px; }
.ticket-action > span.limited { color: #b96a00; background: #fff3da; }
.ticket-action div { display: flex; align-items: center; gap: 6px; }
.ticket-action button, .ticket-action a { padding: 5px 8px; border-radius: 13px; font-family: inherit; font-size: 10px; text-decoration: none; }
.ticket-action button { border: 1px solid #cad3e3; color: #536174; background: #fff; cursor: pointer; }
.ticket-action button.active { border-color: #27a65a; color: #168444; background: #eaf8ef; font-weight: 600; }
.ticket-action a { color: #fff; background: #ef8c34; }
</style>
