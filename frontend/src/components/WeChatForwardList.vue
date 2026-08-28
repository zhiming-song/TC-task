<script setup>
const emit = defineEmits(['back', 'forward-app'])
</script>

<template>
  <section class="wx-list-page">
    <header class="wx-list-header">
      <button class="back-btn" aria-label="返回群聊" @click="emit('back')">‹</button>
      <h1>微信</h1>
      <button class="forward-entry" @click="emit('forward-app')">转发到其他应用</button>
    </header>

    <main class="chat-list">
      <div class="chat-row">
        <div class="chat-avatar group">冲</div>
        <div class="chat-main">
          <div class="chat-top">
            <strong>国庆上海冲冲冲（5）</strong>
            <small>20:26</small>
          </div>
          <p class="chat-preview">林一：人均最好不要超过3000元</p>
        </div>
      </div>

      <div class="chat-row">
        <div class="chat-avatar file">文</div>
        <div class="chat-main">
          <div class="chat-top">
            <strong>文件传输助手</strong>
            <small>20:15</small>
          </div>
          <p class="chat-preview">程心AI：已收到群聊记录，正在整理</p>
        </div>
      </div>

      <div class="chat-row">
        <div class="chat-avatar news">订</div>
        <div class="chat-main">
          <div class="chat-top">
            <strong>订阅号消息</strong>
            <small>19:58</small>
          </div>
          <p class="chat-preview">同程旅行：deeptrip 上线，AI 帮你规划行程</p>
        </div>
        <span class="unread">2</span>
      </div>

      <div class="chat-row">
        <div class="chat-avatar official">微</div>
        <div class="chat-main">
          <div class="chat-top">
            <strong>微信团队</strong>
            <small>昨天</small>
          </div>
          <p class="chat-preview">微信支付提醒：本月账单已出</p>
        </div>
      </div>
    </main>
  </section>
</template>

<style scoped>
.wx-list-page {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #ededed;
}

.wx-list-header {
  position: relative;
  min-height: 44px;
  padding: calc(8px + var(--safe-top)) 14px 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  background: rgba(247, 247, 247, 0.96);
  z-index: 2;
}

.back-btn {
  width: 34px;
  height: 34px;
  border: 0;
  padding: 0;
  color: #111;
  background: transparent;
  font-size: 30px;
  line-height: 30px;
  cursor: pointer;
}

.wx-list-header h1 {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.forward-entry {
  border: 0;
  padding: 4px 0;
  color: #576b95;
  background: transparent;
  font-size: 13px;
  cursor: pointer;
}

.chat-list {
  flex: 1;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

.chat-row {
  padding: 11px 14px;
  display: flex;
  align-items: center;
  gap: 11px;
  border-bottom: 1px solid #ececec;
  background: #fff;
}

.chat-avatar {
  width: 44px;
  height: 44px;
  flex: 0 0 44px;
  display: grid;
  place-items: center;
  border-radius: 5px;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
}

.chat-avatar.group {
  background: linear-gradient(135deg, #34c98e, #07c160);
}

.chat-avatar.file {
  background: linear-gradient(135deg, #5b8ff9, #3a6ee8);
}

.chat-avatar.news {
  background: linear-gradient(135deg, #ffb020, #ff8a00);
}

.chat-avatar.official {
  background: #07c160;
}

.chat-main {
  flex: 1;
  min-width: 0;
}

.chat-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.chat-top strong {
  font-size: 15px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-top small {
  flex: 0 0 auto;
  color: #b2b2b2;
  font-size: 10px;
}

.chat-preview {
  margin: 4px 0 0;
  color: #999;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.unread {
  min-width: 17px;
  height: 17px;
  padding: 0 5px;
  display: grid;
  place-items: center;
  border-radius: 9px;
  color: #fff;
  background: #fa5151;
  font-size: 11px;
}
</style>
