import type { Metadata } from "next";

// Uploaded-document workspaces have no SEO value and may contain sensitive
// user data — never index, cache, or preview them. Static (not
// generateMetadata) so no document fetch is needed to build this metadata.
export const metadata: Metadata = {
  robots: {
    index: false,
    follow: false,
    noarchive: true,
    nosnippet: true,
    noimageindex: true,
  },
};

export default function DocumentLayout({ children }: { children: React.ReactNode }) {
  return children;
}
