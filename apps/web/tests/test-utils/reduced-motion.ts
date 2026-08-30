/**
 * Overrides `window.matchMedia` so `(prefers-reduced-motion: reduce)`
 * reports `matches`. Returns a restore function; call it (or let the
 * caller's own afterEach) to put the default "no preference" mock from
 * vitest.setup.ts back.
 */
export function mockPrefersReducedMotion(matches: boolean) {
  const original = window.matchMedia;
  window.matchMedia = (query: string) =>
    ({
      matches: query.includes("prefers-reduced-motion") ? matches : false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }) as MediaQueryList;

  return () => {
    window.matchMedia = original;
  };
}
