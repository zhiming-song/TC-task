<script setup>
import ChatBox from './ChatBox.vue'

defineProps({
  initialMessage: {
    type: String,
    default: '',
  },
  initialContext: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['back', 'open-summary'])

function openSummary(sections, info) {
  emit('open-summary', sections, info)
}
</script>

<template>
  <section class="deeptrip-page">
    <header class="dt-header">
      <button class="dt-back" aria-label="返回" @click="emit('back')">‹</button>
      <h1>DeepTrip</h1>
      <span class="dt-spacer"></span>
    </header>

    <ChatBox
      :initial-message="initialMessage"
      :initial-context="initialContext"
      variant="deeptrip"
      welcome-text="哈喽~我是DeepTrip 行程规划小能手！可以帮你规划行程、找酒店、订机票火车票！快说说你想去哪儿，有啥要求？我来安排！"
      @open-summary="openSummary"
    />
  </section>
</template>

<style scoped>
.deeptrip-page {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
}

.dt-header {
  min-height: 44px;
  padding: calc(8px + var(--safe-top)) 14px 8px;
  display: grid;
  grid-template-columns: 40px 1fr 40px;
  align-items: center;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  background: #fff;
  z-index: 2;
}

.dt-back {
  width: 38px;
  height: 38px;
  border: 0;
  padding: 0;
  color: #111;
  background: transparent;
  font-size: 30px;
  line-height: 30px;
  cursor: pointer;
}

.dt-header h1 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  text-align: center;
}
</style>
