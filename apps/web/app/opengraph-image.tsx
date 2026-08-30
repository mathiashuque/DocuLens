import { ImageResponse } from "next/og";

export const alt = "DocuLens — ask your documents, with evidence";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// Static marketing content only: mark, name, and one truthful value
// proposition. No screenshot, filename, question, answer, or fabricated
// metric. Uses next/og's bundled default font — no network font loading, so
// this stays safe for the standalone Docker build.
export default function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: "88px 96px",
          background: "#eef1f6",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: 72,
              height: 72,
              borderRadius: 16,
              background: "#4338ca",
            }}
          >
            <svg width="40" height="40" viewBox="0 0 32 32" fill="none">
              <rect x="8.64" y="6.08" width="10.88" height="14.72" rx="1.6" stroke="#ffffff" strokeWidth="2.4" />
              <line x1="11.09" y1="10.86" x2="17.07" y2="10.86" stroke="#ffffff" strokeWidth="2.4" />
              <line x1="11.09" y1="13.81" x2="17.07" y2="13.81" stroke="#ffffff" strokeWidth="2.4" />
              <circle cx="20.48" cy="21.12" r="4.8" stroke="#ffffff" strokeWidth="2.4" />
              <line x1="23.94" y1="24.58" x2="26.24" y2="26.88" stroke="#ffffff" strokeWidth="2.4" />
            </svg>
          </div>
          <span style={{ fontSize: 40, fontWeight: 600, color: "#161a2e" }}>DocuLens</span>
        </div>

        <div style={{ display: "flex", marginTop: 56 }}>
          <span style={{ fontSize: 56, fontWeight: 600, color: "#161a2e", lineHeight: 1.15 }}>
            Ask your documents, with evidence.
          </span>
        </div>

        <div style={{ display: "flex", marginTop: 28 }}>
          <span style={{ fontSize: 28, color: "#4c5268", lineHeight: 1.4, maxWidth: 880 }}>
            Upload a PDF, ask questions or request analysis, and get answers grounded in the exact page and quote.
          </span>
        </div>
      </div>
    ),
    { ...size }
  );
}
