import { promises as fs } from "fs";
import path from "path";
import { fileURLToPath } from "url";

import yaml from "js-yaml";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..");
const catalogPath = path.join(repoRoot, "config", "report_catalog.yaml");
const reportRoot = path.join(repoRoot, "static", "reports");

async function fileExists(targetPath) {
  try {
    const stat = await fs.stat(targetPath);
    return stat.isFile();
  } catch {
    return false;
  }
}

function getReports(rawCatalog) {
  if (Array.isArray(rawCatalog)) {
    return rawCatalog;
  }
  if (rawCatalog && Array.isArray(rawCatalog.reports)) {
    return rawCatalog.reports;
  }
  throw new Error(`Expected a report list in ${catalogPath}`);
}

async function main() {
  const raw = yaml.load(await fs.readFile(catalogPath, "utf8")) ?? {};
  const reports = getReports(raw);
  const missing = [];

  for (const report of reports) {
    const assetDir = path.join(reportRoot, report.area, report.process_group, report.slug);
    const requiredFiles = [
      path.join(assetDir, "preview.json"),
      path.join(assetDir, `${report.slug}.xlsx`),
      path.join(assetDir, `${report.slug}.csv`),
    ];

    for (const requiredFile of requiredFiles) {
      if (!(await fileExists(requiredFile))) {
        missing.push(path.relative(repoRoot, requiredFile));
      }
    }
  }

  if (missing.length > 0) {
    console.error("Missing report assets:");
    for (const missingFile of missing) {
      console.error(`- ${missingFile}`);
    }
    console.error(
      "Generate the curated report files into static/reports locally, configure published_sqlite_url or REPORTS_SQLITE_URL so the build can download them automatically, or let the GitHub Pages workflow generate them during deploy. These assets do not need to be committed."
    );
    process.exitCode = 1;
    return;
  }

  console.log(`Validated report assets in ${reportRoot}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
