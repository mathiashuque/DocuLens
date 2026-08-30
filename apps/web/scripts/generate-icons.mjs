#!/usr/bin/env node
// Deterministic, dependency-free icon generator for the DocuLens document/lens
// mark. Run with `node scripts/generate-icons.mjs` after editing
// scripts/brand/mark.mjs; the checked-in outputs below are its committed,
// reviewable build artifacts, not hand-edited binaries.
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { renderMark } from "./brand/mark.mjs";
import { encodePng } from "./brand/png.mjs";
import { encodeIco } from "./brand/ico.mjs";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

function writeAsset(path, buffer) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, buffer);
  console.log(`wrote ${path} (${buffer.length} bytes)`);
}

function pngAt(size) {
  return encodePng(renderMark(size), size);
}

// favicon.ico: 16/32/48 cover browser tabs, bookmarks, and history at their
// native resolutions.
writeAsset(
  join(root, "app/favicon.ico"),
  encodeIco([16, 32, 48].map((size) => ({ size, png: pngAt(size) })))
);

// apple-icon.png: Apple's recommended 180x180, opaque background (no
// transparency) so home-screen tiles never show through to a black/white grid.
writeAsset(join(root, "app/apple-icon.png"), pngAt(180));

// Manifest icons: 192 and 512 per the Web Manifest spec's minimum recommended
// set for install prompts and splash screens.
writeAsset(join(root, "public/icons/icon-192.png"), pngAt(192));
writeAsset(join(root, "public/icons/icon-512.png"), pngAt(512));
