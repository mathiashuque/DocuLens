/** Shared by every server-only backend client: parses a response body as
 * JSON, tolerating an empty body, without throwing on malformed JSON. */
export async function parseJsonSafely(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return undefined;
  }
  try {
    return JSON.parse(text);
  } catch {
    return undefined;
  }
}
