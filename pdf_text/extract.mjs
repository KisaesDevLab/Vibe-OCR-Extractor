/**
 * PDF text-layer analysis + extraction using pdf.js (pdfjs-dist).
 *
 * This intentionally mirrors the logic in the Vibe-Transaction-Convertor
 * `packages/extractor/src/preprocess.ts` so the text shown here is exactly what
 * the converter receives from a PDF's text layer:
 *   - same thresholds (page coverage, avg chars/page, per-page has-text)
 *   - same per-item join (item.str + '\n' on hasEOL else ' ')
 *   - same whitespace cleanup and routing (text | ocr | hybrid)
 *
 * Usage: node extract.mjs <path-to-pdf>   ->   JSON on stdout
 */

import { readFile } from "node:fs/promises";

// pdf.js's legacy build prints polyfill warnings ("Cannot polyfill DOMMatrix")
// to stdout. Redirect all console output to stderr so stdout stays pure JSON.
console.log = (...args) => process.stderr.write(args.join(" ") + "\n");
console.warn = (...args) => process.stderr.write(args.join(" ") + "\n");
console.error = (...args) => process.stderr.write(args.join(" ") + "\n");

const { getDocument, VerbosityLevel } = await import(
  "pdfjs-dist/legacy/build/pdf.mjs"
);

// Thresholds copied verbatim from preprocess.ts.
const TEXT_LAYER_PAGE_THRESHOLD = 0.5; // >50% of pages must carry text
const TEXT_AVG_CHAR_THRESHOLD = 100; // average chars/page for a real text layer
const PER_PAGE_HAS_TEXT_THRESHOLD = 30; // chars for a single page to "have text"

function isTextItem(item) {
  return item && typeof item.str === "string";
}

async function main() {
  const path = process.argv[2];
  if (!path) {
    process.stderr.write("usage: extract.mjs <pdf>\n");
    process.exit(2);
  }

  const data = new Uint8Array(await readFile(path));
  const doc = await getDocument({
    data,
    isEvalSupported: false,
    useSystemFonts: true,
    verbosity: VerbosityLevel ? VerbosityLevel.ERRORS : 0,
  }).promise;

  const pageCount = doc.numPages;
  const pages = [];
  const pageTexts = [];
  let pagesWithText = 0;
  let totalChars = 0;

  for (let i = 1; i <= pageCount; i += 1) {
    const page = await doc.getPage(i);
    const tc = await page.getTextContent();

    let charCount = 0;
    const parts = [];
    for (const item of tc.items) {
      if (!isTextItem(item)) continue;
      const text = item.str;
      if (text.length === 0) continue;
      charCount += text.length;
      parts.push(text);
      if (item.hasEOL) parts.push("\n");
      else parts.push(" ");
    }

    const hasText = charCount >= PER_PAGE_HAS_TEXT_THRESHOLD;
    if (hasText) pagesWithText += 1;
    totalChars += charCount;

    // Same cleanup as preprocess.ts: collapse trailing spaces/tabs before a
    // newline, then trim the whole page.
    const pageText = parts.join("").replace(/[ \t]+\n/g, "\n").trim();
    pages.push({ index: i, hasText, charCount });
    pageTexts.push(pageText);
  }

  const textLayerCoverage = pageCount === 0 ? 0 : pagesWithText / pageCount;
  const avgCharsPerPage = pageCount === 0 ? 0 : totalChars / pageCount;
  const hasTextLayer =
    textLayerCoverage > TEXT_LAYER_PAGE_THRESHOLD &&
    avgCharsPerPage > TEXT_AVG_CHAR_THRESHOLD;
  const suspectedScan = !hasTextLayer && pageCount > 0;

  // Routing, mirroring preprocess.ts.
  let route;
  if (hasTextLayer && pages.every((p) => p.hasText)) route = "text";
  else if (textLayerCoverage === 0) route = "ocr";
  else route = "hybrid";

  const out = {
    pageCount,
    hasTextLayer,
    textLayerCoverage,
    avgCharsPerPage,
    suspectedScan,
    route,
    pages,
    pageTexts,
  };
  process.stdout.write(JSON.stringify(out));
}

main().catch((err) => {
  process.stderr.write(String(err && err.stack ? err.stack : err));
  process.exit(1);
});
