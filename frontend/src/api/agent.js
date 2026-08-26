const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

async function parseError(res) {
  try {
    const data = await res.json()
    return data.detail || `请求失败(${res.status})`
  } catch {
    return `请求失败(${res.status})`
  }
}

/** 健康检查，返回当前后端使用的模型 */
export async function fetchHealth() {
  const res = await fetch(`${BASE_URL}/health`)
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

/** 一次性返回完整回复 */
export async function chat(messages, temperature = 0.3) {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages, temperature }),
  })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

/**
 * 流式对话，逐字回调
 * @param {Array<{role: string, content: string}>} messages
 * @param {(token: string) => void} onToken
 * @param {(card: object) => void} onCard
 */
export async function chatStream(messages, onToken, onCard = () => {}, temperature = 0.3) {
  const res = await fetch(`${BASE_URL}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages, temperature }),
  })
  if (!res.ok) throw new Error(await parseError(res))

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const chunks = buffer.split('\n\n')
    buffer = chunks.pop() ?? ''

    for (const chunk of chunks) {
      const line = chunk.trim()
      if (!line.startsWith('data:')) continue

      const data = line.slice(5).trim()
      if (data === '[DONE]') return

      try {
        const parsed = JSON.parse(data)
        if (parsed.error) throw new Error(parsed.error)
        if (parsed.token) onToken(parsed.token)
        if (parsed.card) onCard(parsed.card)
      } catch (err) {
        if (err instanceof SyntaxError) continue
        throw err
      }
    }
  }
}
