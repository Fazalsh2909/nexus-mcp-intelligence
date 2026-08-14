import type { ChatMessage, ToolActivity } from './api'

export interface ConversationState {
  messages: ChatMessage[]
  toolActivities: ToolActivity[]
}

const cache = new Map<string, ConversationState>()

export function getCachedConversation(id: string): ConversationState | undefined {
  return cache.get(id)
}

export function getLastSessionId(): string | null {
  return localStorage.getItem('nexus_last_session')
}

export function chatTarget(): string {
  const last = getLastSessionId()
  return last ? `/chat/${last}` : '/chat'
}

export function setCachedConversation(id: string, state: ConversationState) {
  cache.set(id, {
    messages: state.messages.map(m => ({ ...m, sources: m.sources ? [...m.sources] : undefined })),
    toolActivities: [...state.toolActivities],
  })
}

// Tracks sessions with an in-flight stream so a page that remounts while the
// answer is still generating can keep polling until it completes.
const streaming = new Set<string>()

export function markStreaming(id: string) {
  streaming.add(id)
}

export function markStreamComplete(id: string) {
  streaming.delete(id)
}

export function isStreamingSession(id: string): boolean {
  return streaming.has(id)
}
