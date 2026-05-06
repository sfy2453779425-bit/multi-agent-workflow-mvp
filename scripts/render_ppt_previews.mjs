import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const artifactToolUrl = pathToFileURL(
  "C:/Users/lain/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs",
).href;

const { PresentationFile } = await import(artifactToolUrl);

const decks = [
  {
    label: "KR",
    pptx: path.join(ROOT, "docs", "AI_Agent_Builder_MVP_KR.pptx"),
    outDir: path.join(ROOT, "docs", "ppt_previews", "KR"),
  },
  {
    label: "ZH",
    pptx: path.join(ROOT, "docs", "AI_Agent_Builder_MVP_ZH.pptx"),
    outDir: path.join(ROOT, "docs", "ppt_previews", "ZH"),
  },
];

async function saveBlob(blob, outputPath) {
  const buffer = Buffer.from(await blob.arrayBuffer());
  await fs.writeFile(outputPath, buffer);
  return buffer.length;
}

async function renderDeck(deck) {
  await fs.mkdir(deck.outDir, { recursive: true });
  const pptxData = await fs.readFile(deck.pptx);
  const presentation = await PresentationFile.importPptx(pptxData);
  const slides = presentation.slides.items;
  const rendered = [];

  for (let i = 0; i < slides.length; i += 1) {
    const slide = slides[i];
    const fileName = `slide-${String(i + 1).padStart(2, "0")}.png`;
    const outputPath = path.join(deck.outDir, fileName);
    const pngBlob = await slide.export({ format: "png" });
    const bytes = await saveBlob(pngBlob, outputPath);
    rendered.push({ slide: i + 1, file: outputPath, bytes });
  }

  return {
    label: deck.label,
    pptx: deck.pptx,
    slideCount: slides.length,
    previewDir: deck.outDir,
    rendered,
  };
}

const report = [];
for (const deck of decks) {
  report.push(await renderDeck(deck));
}

const reportPath = path.join(ROOT, "docs", "ppt_previews", "preview-report.json");
await fs.writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");

for (const item of report) {
  console.log(`${item.label}: ${item.slideCount} slides -> ${item.previewDir}`);
}
console.log(reportPath);
process.exit(0);
