import { promises as fs } from "fs";
import path from "path";
import { fileURLToPath } from "url";

import yaml from "js-yaml";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..");
const catalogPath = path.join(repoRoot, "config", "report_pack_catalog.yaml");
const outputPath = path.join(repoRoot, "src", "generated", "reportPackManifest.js");

function getPacks(rawCatalog) {
  if (Array.isArray(rawCatalog)) {
    return rawCatalog;
  }
  if (rawCatalog && Array.isArray(rawCatalog.packs)) {
    return rawCatalog.packs;
  }
  throw new Error(`Expected a pack list in ${catalogPath}`);
}

function normalizeLink(link) {
  if (!link) {
    return null;
  }
  return {
    label: String(link.label),
    href: String(link.href),
  };
}

function normalizeReportEntry(entry) {
  return {
    reportSlug: String(entry.report_slug),
    teachingRole: String(entry.teaching_role),
    whyItMatters: String(entry.why_it_matters),
    discussionQuestions: Array.isArray(entry.discussion_questions) ? entry.discussion_questions.map(String) : [],
    suggestedAnalysis: Array.isArray(entry.suggested_analysis) ? entry.suggested_analysis.map(String) : [],
    relatedLink: normalizeLink(entry.related_link),
  };
}

function normalizePack(pack) {
  return {
    slug: String(pack.slug),
    title: String(pack.title),
    summary: String(pack.summary),
    audience: String(pack.audience),
    businessLens: String(pack.business_lens),
    coreQuestions: Array.isArray(pack.core_questions) ? pack.core_questions.map(String) : [],
    whereToGoNext: Array.isArray(pack.where_to_go_next) ? pack.where_to_go_next.map(normalizeLink).filter(Boolean) : [],
    reports: Array.isArray(pack.reports) ? pack.reports.map(normalizeReportEntry) : [],
  };
}

async function main() {
  const raw = yaml.load(await fs.readFile(catalogPath, "utf8")) ?? {};
  const packs = getPacks(raw).map(normalizePack);
  const manifest = Object.fromEntries(packs.map((pack) => [pack.slug, pack]));
  const outputSource = `const reportPackManifest = ${JSON.stringify(manifest, null, 2)};\n\nexport default reportPackManifest;\n`;

  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  await fs.writeFile(outputPath, outputSource, "utf8");
  console.log(`Wrote ${outputPath}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
