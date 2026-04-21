import { promises as fs, accessSync, createWriteStream } from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { Readable } from "stream";
import { pipeline } from "stream/promises";
import { spawnSync } from "child_process";

import yaml from "js-yaml";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..");
const configPath = path.join(repoRoot, "config", "settings.yaml");
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

function deriveShortName(companyName) {
  const compact = String(companyName ?? "").replace(/[^A-Za-z0-9]+/g, " ").trim();
  const tokens = compact.split(/\s+/).filter(Boolean);
  const legalSuffixes = new Set(["inc", "incorporated", "llc", "ltd", "corp", "corporation", "co", "company"]);
  const filtered = tokens.filter((token) => !legalSuffixes.has(token.toLowerCase()));
  return (filtered.slice(0, 2).join("") || tokens.slice(0, 1).join("") || "Dataset");
}

function interpolateTemplate(value, shortName) {
  if (!value) {
    return value;
  }
  const shortNameDisplay = String(shortName).replace(/(?<=[a-z0-9])(?=[A-Z])/g, " ").trim();
  return String(value)
    .replaceAll("{short_name}", shortName)
    .replaceAll("{short_name_lower}", shortName.toLowerCase())
    .replaceAll("{short_name_display}", shortNameDisplay);
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

async function collectMissingFiles() {
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
        missing.push(requiredFile);
      }
    }
  }

  return missing;
}

async function loadPublishedSqliteUrl() {
  const raw = yaml.load(await fs.readFile(configPath, "utf8")) ?? {};
  const shortName = String(raw.short_name || deriveShortName(raw.company_name));
  return (
    process.env.REPORTS_SQLITE_URL ||
    process.env.PUBLISHED_SQLITE_URL ||
    interpolateTemplate(raw.published_sqlite_url, shortName) ||
    null
  );
}

async function loadConfiguredSqlitePath() {
  if (process.env.REPORTS_SQLITE_PATH) {
    return path.resolve(repoRoot, process.env.REPORTS_SQLITE_PATH);
  }
  const raw = yaml.load(await fs.readFile(configPath, "utf8")) ?? {};
  const shortName = String(raw.short_name || deriveShortName(raw.company_name));
  const configuredPath = interpolateTemplate(raw.sqlite_path, shortName);
  if (!configuredPath) {
    return null;
  }
  return path.resolve(repoRoot, configuredPath);
}

function resolveDownloadTarget(sqliteUrl) {
  const filename = path.basename(new URL(sqliteUrl).pathname) || "published.sqlite";
  return path.join(repoRoot, "outputs", "_site_build", filename);
}

async function downloadSqlite(sqliteUrl, targetPath) {
  const response = await fetch(sqliteUrl);
  if (!response.ok || !response.body) {
    throw new Error(`Unable to download published SQLite: ${sqliteUrl} (${response.status})`);
  }

  await fs.mkdir(path.dirname(targetPath), { recursive: true });
  await pipeline(Readable.fromWeb(response.body), createWriteStream(targetPath));
}

function resolvePythonCommand() {
  const candidates = [
    process.env.REPORTS_PYTHON,
    path.join(repoRoot, ".venv", "Scripts", "python.exe"),
    path.join(repoRoot, ".venv", "bin", "python"),
    "python3",
    "python",
  ].filter(Boolean);

  for (const candidate of candidates) {
    if (candidate !== "python" && candidate !== "python3") {
      try {
        accessSync(candidate);
      } catch {
        continue;
      }
    }

    const probe = spawnSync(
      candidate,
      [
        "-c",
        [
          "import pandas, openpyxl, yaml, xlsxwriter",
          "try:",
          "    import sqlite3",
          "except ModuleNotFoundError:",
          "    from pysqlite3 import dbapi2 as sqlite3",
          "print('ok')",
        ].join("\n"),
      ],
      {
        cwd: repoRoot,
        encoding: "utf8",
        stdio: ["ignore", "pipe", "pipe"],
      }
    );

    if (probe.status === 0) {
      return candidate;
    }
  }

  throw new Error(
    "Unable to find a Python interpreter with the report-generation dependencies and SQLite support."
  );
}

function generateReports(sqlitePath) {
  const pythonCommand = resolvePythonCommand();
  console.log(`Using Python interpreter: ${pythonCommand}`);
  const scriptPath = path.join(repoRoot, "scripts", "generate-site-reports.py");
  const result = spawnSync(
    pythonCommand,
    [scriptPath, "--config", configPath, "--sqlite-path", sqlitePath, "--report-output-dir", reportRoot],
    {
      cwd: repoRoot,
      stdio: "inherit",
    }
  );

  if (result.status !== 0) {
    throw new Error(`Report generation failed with ${pythonCommand}`);
  }
}

async function main() {
  const missingBefore = await collectMissingFiles();
  if (missingBefore.length === 0) {
    console.log(`Report assets already available in ${reportRoot}`);
    return;
  }

  const configuredSqlitePath = await loadConfiguredSqlitePath();
  if (configuredSqlitePath && (await fileExists(configuredSqlitePath))) {
    try {
      console.log(`Using local SQLite from ${configuredSqlitePath}`);
      generateReports(configuredSqlitePath);

      const missingAfterLocal = await collectMissingFiles();
      if (missingAfterLocal.length === 0) {
        console.log(`Generated report assets in ${reportRoot}`);
        return;
      }
    } catch (error) {
      console.warn(`Local SQLite report generation failed: ${error instanceof Error ? error.message : error}`);
      console.warn("Falling back to the published SQLite asset.");
    }
  }

  const sqliteUrl = await loadPublishedSqliteUrl();
  if (!sqliteUrl) {
    console.error("Report assets are missing and no published SQLite download URL is configured.");
    console.error("Set published_sqlite_url in config/settings.yaml or REPORTS_SQLITE_URL in the environment.");
    process.exitCode = 1;
    return;
  }

  const downloadTarget = resolveDownloadTarget(sqliteUrl);
  console.log(`Downloading published SQLite from ${sqliteUrl}`);
  await downloadSqlite(sqliteUrl, downloadTarget);
  generateReports(downloadTarget);

  const missingAfter = await collectMissingFiles();
  if (missingAfter.length > 0) {
    console.error("Report assets are still missing after automatic preparation:");
    for (const missingFile of missingAfter.slice(0, 20)) {
      console.error(`- ${path.relative(repoRoot, missingFile)}`);
    }
    if (missingAfter.length > 20) {
      console.error(`... and ${missingAfter.length - 20} more`);
    }
    process.exitCode = 1;
    return;
  }

  console.log(`Generated report assets in ${reportRoot}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
