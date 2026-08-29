export type BackendErrorKind =
  | "not_found"
  | "unavailable"
  | "malformed_response"
  | "config"
  // Analysis-specific: kept distinct from "unavailable" so the UI can tell a
  // configured-but-momentarily-unreachable provider (503) apart from a
  // provider that responded with invalid/unusable output (502), and both
  // apart from the textless/no-extractable-text conflict (409).
  | "conflict"
  | "provider_unavailable"
  | "provider_invalid";

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
