import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

import "@testing-library/jest-dom/vitest";

// jsdom does not implement matchMedia. Motion's useReducedMotion() (and any
// other prefers-reduced-motion check) needs it to exist; default to "no
// preference" so normal-motion behavior is what tests get unless a test
// explicitly mocks a "reduce" match (see tests/test-utils/reduced-motion.ts).
if (typeof window !== "undefined" && !window.matchMedia) {
  window.matchMedia = (query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }) as MediaQueryList;
}

// jsdom does not implement scrollIntoView (no real layout engine). The chat
// transcript calls it to keep new turns in view; stub it as a no-op so that
// code path is exercised without throwing in tests.
if (typeof window !== "undefined" && !window.HTMLElement.prototype.scrollIntoView) {
  window.HTMLElement.prototype.scrollIntoView = () => {};
}

afterEach(() => {
  cleanup();
});
