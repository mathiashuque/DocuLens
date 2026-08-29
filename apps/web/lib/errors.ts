export type BackendErrorKind =
  | "not_found"
  | "unavailable"
  | "malformed_response"
  | "config";

/** Normalized, safe-to-render error from the backend document service. */
export class BackendError extends Error {
  readonly kind: BackendErrorKind;
  readonly status?: number;

  constructor(kind: BackendErrorKind, message: string, status?: number) {
    super(message);
    this.name = "BackendError";
    this.kind = kind;
    this.status = status;
  }
}
