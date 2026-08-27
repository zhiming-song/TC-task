<script setup>
import { ref, watch } from 'vue'
const props = defineProps({
  sections: {
    type: Array,
    required: true,
  },
})

const emit = defineEmits(['select-section-item'])
const selected = ref({})

function syncSelected(sections) {
  selected.value = Object.fromEntries(sections.map((section) => [section.key, [...section.selectedIds]]))
}

watch(() => props.sections, syncSelected, { immediate: true })

function cardTitle(card) {
  return card.title || card.attraction_name || card.service_label || card.id
}

function cardMeta(card) {
  return [
    card.origin && card.destination ? `${card.origin} → ${card.destination}` : '',
    card.location || card.destination || '',
    card.departure_date || card.checkin_date || '',
    card.return_date || card.checkout_date || '',
  ].filter(Boolean).join(' · ')
}

function cardPrice(card) {
  return card.total_price_yuan ? `¥${card.total_price_yuan}` : ''
}

function selectItem(section, card) {
  if (section.locked) return
  const current = selected.value[section.key] || []
  selected.value[section.key] = section.key === 'ticket'
    ? (current.includes(card.id) ? current.filter((id) => id !== card.id) : [...current, card.id])
    : [card.id]
  emit('select-section-item', { sectionKey: section.key, cardId: card.id })
}

function selectedIds(section) {
  return selected.value[section.key] || []
}
</script>

<template>
  <section class="trip-summary">
    <div v-for="section in props.sections" :key="section.key" class="summary-section">
      <div class="section-head">
        <strong>{{ section.title }}</strong>
        <span>{{ section.locked ? '已锁定' : '可选择' }}</span>
      </div>

      <div v-if="section.cards.length" class="summary-options">
        <button
          v-for="card in section.cards"
          :key="card.id"
          class="summary-option"
          :class="{ selected: selectedIds(section).includes(card.id), locked: section.locked }"
          type="button"
          :disabled="section.locked"
          @click="selectItem(section, card)"
        >
          <span class="option-radio" :class="{ checked: selectedIds(section).includes(card.id) }" aria-hidden="true"></span>
          <span class="option-main">
            <strong>{{ cardTitle(card) }}</strong>
            <small>{{ cardMeta(card) }}</small>
          </span>
          <span class="option-side">
            <b>{{ cardPrice(card) }}</b>
            <small>{{ section.selectedIds.includes(card.id) ? '已选' : '选择' }}</small>
          </span>
        </button>
      </div>

      <p v-else class="empty-section">暂无候选</p>
    </div>
  </section>
</template>

<style scoped>
.trip-summary {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 10px 10px 20px;
  background: #fff;
}

.summary-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.summary-head div,
.section-head {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.summary-head strong {
  color: #20232a;
  font-size: 16px;
}

.summary-head span,
.section-head span,
.empty-section {
  color: #8b93a3;
  font-size: 12px;
}

.summary-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-head {
  padding-top: 4px;
}

.section-head strong {
  font-size: 13px;
}

.summary-options {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.summary-option {
  width: 100%;
  min-height: 58px;
  padding: 9px 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid #dfe5f1;
  border-radius: 8px;
  background: #fff;
  color: #20232a;
  text-align: left;
}

.option-radio {
  width: 18px;
  height: 18px;
  flex: 0 0 18px;
  border: 1.5px solid #c8ceda;
  border-radius: 50%;
  background: #fff;
  position: relative;
}

.option-radio.checked {
  border-color: #4b6ef5;
}

.option-radio.checked::after {
  content: '';
  position: absolute;
  inset: 4px;
  border-radius: 50%;
  background: #4b6ef5;
}

.summary-option.selected {
  border-color: #27a65a;
  background: #eaf8ef;
}

.summary-option.locked {
  cursor: not-allowed;
}

.option-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.option-main strong,
.option-main small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.option-main strong {
  font-size: 13px;
}

.option-main small,
.option-side small {
  color: #8b93a3;
  font-size: 11px;
}

.option-side {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 3px;
}

.option-side b {
  color: #f05a29;
  font-size: 14px;
}

.empty-section {
  margin: 0;
}
</style>
