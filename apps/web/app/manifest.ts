import type { MetadataRoute } from "next";

// Browser-behavior-preserving manifest: no shortcuts, share target, file
// handler, or screenshots, since none of those are implemented or tested.
// `display: "browser"` makes no installed-app claim beyond what's verified.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "DocuLens",
    short_name: "DocuLens",
    description:
      "Upload a PDF, then ask it questions or request analysis grounded in exact page evidence.",
    start_url: "/",
    scope: "/",
    display: "browser",
    background_color: "#eef1f6",
    theme_color: "#4338ca",
    icons: [
      {
        src: "/icon.svg",
        sizes: "any",
        type: "image/svg+xml",
      },
      {
        src: "/icons/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icons/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
    ],
  };
}
