/**
 * Substitutes `{token}` placeholders in a dictionary template with values.
 * Dictionaries stay plain, serializable data (strings and arrays of
 * strings) instead of functions, so a (sub-)dictionary can be passed as a
 * prop into a Client Component without a "functions cannot be passed to
 * Client Components" error.
 */
export function interpolate(template: string, values: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (match, token: string) =>
    token in values ? String(values[token]) : match
  );
}
