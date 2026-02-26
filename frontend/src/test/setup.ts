import '@testing-library/jest-dom';
import { fetch } from 'cross-fetch';
import { vi } from 'vitest';

// Polyfill fetch for Node.js environment in Vitest
globalThis.fetch = fetch as any;

// Mock window.matchMedia which is required by Mantine
Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(), // Deprecated
        removeListener: vi.fn(), // Deprecated
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
    })),
});

// Mock ResizeObserver
globalThis.ResizeObserver = class {
    observe() { }
    unobserve() { }
    disconnect() { }
} as any;
