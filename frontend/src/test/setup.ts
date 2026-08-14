import '@testing-library/jest-dom/vitest'

// jsdom lacks ResizeObserver, which Recharts' ResponsiveContainer uses.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
if (!globalThis.ResizeObserver) {
  globalThis.ResizeObserver = ResizeObserverStub as unknown as typeof ResizeObserver
}

// jsdom does not implement scrollIntoView (used to keep the chat scrolled down).
if (typeof Element !== 'undefined' && !Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {}
}

// jsdom's crypto may lack randomUUID (used for chat message ids).
try {
  const c = globalThis.crypto as unknown as { randomUUID?: () => string } | undefined
  if (c && !c.randomUUID) {
    c.randomUUID = () => `id-${Math.random().toString(36).slice(2)}`
  }
} catch {
  // ignore
}

