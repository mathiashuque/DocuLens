import { describe, expect, it } from "vitest";

import { metadata } from "@/app/[lang]/documents/[documentId]/layout";

describe("document route robots metadata", () => {
  it("is noindex/nofollow and carries no document-derived fields", () => {
    expect(metadata.robots).toEqual({
      index: false,
      follow: false,
      noarchive: true,
      nosnippet: true,
      noimageindex: true,
    });

    // Static object, not generateMetadata — nothing here can leak a
    // filename, document ID, answer, or evidence excerpt because no
    // document is ever fetched to build it.
    expect(Object.keys(metadata)).toEqual(["robots"]);
  });
});
