<script setup>
import { computed } from 'vue'

const props = defineProps({
  card: { type: Object, required: true },
  selected: { type: Boolean, default: false },
  recommended: { type: Boolean, default: false },
})

const emit = defineEmits(['select'])
const tierLabel = computed(() => ({
  economic: '经济型',
  balanced: '舒适型',
  comfort: '品质型',
}[props.card.tier] || '酒店'))
</script>

<template>
  <article class="hotel-card" :class="{ selected, recommended }">
    <div class="hotel-head">
      <span class="hotel-icon">🏨</span>
      <div>
        <strong>{{ card.title }}</strong>
        <span>{{ card.location }} · {{ tierLabel }}</span>
      </div>
      <span v-if="recommended" class="recommended-badge">★ 推荐</span>
    </div>

    <div class="stay-line">
      <div><span>入住</span><strong>{{ card.checkin_date }}</strong></div>
      <i></i>
      <div><span>离店</span><strong>{{ card.checkout_date }}</strong></div>
    </div>

    <div class="hotel-metrics">
      <div><span>参考评分</span><strong>{{ card.rating }}</strong></div>
      <div><span>{{ card.rooms }}间 × {{ card.nights }}晚</span><strong>¥{{ card.total_price_yuan }}</strong></div>
      <div class="price"><span>每间每晚</span><strong>¥{{ card.unit_price_yuan }}</strong></div>
    </div>

    <div class="inventory-line">
      <span :class="{ limited: card.inventory_status === '紧张' }">
        余 {{ card.remaining_inventory }} 间 · {{ card.inventory_status }}
      </span>
      <div class="actions">
        <button :class="{ active: selected }" type="button" @click="emit('select')">
          {{ selected ? '✓ 已选择' : '选择此酒店' }}
        </button>
        <a :href="card.booking_url" target="_blank" rel="noopener noreferrer">{{ card.cta_label }} ›</a>
      </div>
    </div>
  </article>
</template>

<style scoped>
.hotel-card {
  overflow: hidden;
  border: 1px solid #dfe5f1;
  border-top: 3px solid #19a777;
  border-radius: 14px;
  color: #20232a;
  background: #fff;
  box-shadow: 0 6px 20px rgba(38, 56, 92, 0.07);
}

.hotel-card.selected {
  border-color: #27a65a;
  box-shadow: 0 0 0 2px rgba(39, 166, 90, 0.13), 0 8px 22px rgba(38, 56, 92, 0.09);
}

.hotel-card.selected {
  border-color: #27a65a;
  box-shadow: 0 0 0 2px rgba(39, 166, 90, 0.13), 0 8px 22px rgba(38, 56, 92, 0.09);
}

.hotel-card.recommended {
  border-color: #f0a020;
  box-shadow: 0 0 0 2px rgba(240, 160, 32, 0.15), 0 8px 22px rgba(38, 56, 92, 0.09);
}

.hotel-head {
  padding: 11px 13px;
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) auto;
  align-items: center;
  gap: 9px;
}

.recommended-badge {
  padding: 4px 10px;
  border-radius: 12px;
  color: #fff;
  background: linear-gradient(135deg, #f0a020, #f5c842);
  font-size: 11px;
  font-weight: 600;
}

.hotel-icon {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: #eaf8f2;
  font-size: 18px;
}

.hotel-head div { min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.hotel-head strong { overflow: hidden; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.hotel-head div span { color: #8b93a3; font-size: 10px; }
.mode-badge { padding: 3px 7px; border-radius: 10px; color: #9a6700; background: #fff5cc; font-size: 10px; }

.stay-line {
  padding: 2px 14px 11px;
  display: grid;
  grid-template-columns: 1fr 42px 1fr;
  align-items: center;
}

.stay-line div { display: flex; flex-direction: column; gap: 2px; }
.stay-line div:last-child { align-items: flex-end; }
.stay-line span { color: #9298a3; font-size: 9px; }
.stay-line strong { font-size: 12px; }
.stay-line i { height: 1px; background: #c5ccda; }

.hotel-metrics {
  padding: 9px 13px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  border-top: 1px solid #edf0f5;
  background: #fafbfc;
}

.hotel-metrics div { display: flex; flex-direction: column; gap: 2px; }
.hotel-metrics span { color: #9298a3; font-size: 9px; }
.hotel-metrics strong { font-size: 12px; }
.hotel-metrics .price { align-items: flex-end; }
.hotel-metrics .price strong { color: #f05a29; font-size: 15px; }

.inventory-line {
  padding: 9px 11px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  border-top: 1px solid #edf0f5;
}

.inventory-line > span { padding: 3px 6px; border-radius: 9px; color: #168444; background: #eaf8ef; font-size: 9px; }
.inventory-line > span.limited { color: #b96a00; background: #fff3da; }
.actions { display: flex; align-items: center; gap: 6px; }
.actions button, .actions a { padding: 5px 8px; border-radius: 13px; font-family: inherit; font-size: 10px; text-decoration: none; }
.actions button { border: 1px solid #cad3e3; color: #536174; background: #fff; cursor: pointer; }
.actions button.active { border-color: #27a65a; color: #168444; background: #eaf8ef; font-weight: 600; }
.actions a { color: #fff; background: #19a777; }
</style>
