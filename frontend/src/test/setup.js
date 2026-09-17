import { afterAll, vi } from 'vitest';

// Node's native web storage can shadow jsdom's implementation. Use the test
// browser's actual Storage object so persistence tests exercise browser behavior.
if (globalThis.jsdom) {
  vi.stubGlobal('localStorage', globalThis.jsdom.window.localStorage);
  vi.stubGlobal('Storage', globalThis.jsdom.window.Storage);
  afterAll(() => vi.unstubAllGlobals());
}
