import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "DocuLens",
  description:
    "DocuLens turns complex documents into structured, evidence-backed analysis.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col bg-white font-sans text-zinc-900">
        {children}
      </body>
    </html>
  );
}
