const fs = require("fs");
const path = require("path");
const yaml = require("js-yaml");

const LEGAL_SUFFIXES = new Set([
  "inc",
  "incorporated",
  "llc",
  "ltd",
  "corp",
  "corporation",
  "co",
  "company",
]);

function deriveShortName(companyName) {
  const compact = String(companyName || "")
    .replace(/[^A-Za-z0-9]+/g, " ")
    .trim();
  const tokens = compact.split(/\s+/).filter(Boolean);
  const filtered = tokens.filter((token) => !LEGAL_SUFFIXES.has(token.toLowerCase()));
  const baseTokens = filtered.length > 0 ? filtered : tokens;
  return (baseTokens.slice(0, 2).join("") || "Dataset").replace(/\s+/g, "");
}

function deriveDisplayName(shortName) {
  return String(shortName || "Dataset")
    .replace(/[_-]+/g, " ")
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/\s+/g, " ")
    .trim();
}

function normalizeBaseUrl(baseUrl, shortName) {
  const fallback = `https://${String(shortName || "dataset").toLowerCase()}.accountinganalyticshub.com`;
  const raw = String(baseUrl || fallback).trim();
  return raw.replace(/\/+$/, "");
}

function loadSiteBranding(configPath = path.join(__dirname, "settings.yaml")) {
  const raw = yaml.load(fs.readFileSync(configPath, "utf8")) || {};
  const companyName = String(raw.company_name || "Accounting Dataset");
  const shortName = String(raw.short_name || deriveShortName(companyName));
  const displayName = deriveDisplayName(shortName);
  const baseUrl = normalizeBaseUrl(raw.base_url, shortName);
  const domain = new URL(baseUrl).hostname;

  return {
    companyName,
    shortName,
    displayName,
    baseUrl,
    domain,
    datasetName: `${displayName} Accounting Dataset`,
    whyTitle: `Why ${displayName}`,
    instructorLabel: `Teach With ${displayName}`,
    // GitHub resolves this to the latest published full release asset.
    // This works as long as each release uploads the same asset filenames.
    releaseBaseUrl:
      "https://github.com/mmcodesso/CharlesRiver_Database/releases/latest/download",
    repositoryUrl: "https://github.com/mmcodesso/greenfield_database",
  };
}

module.exports = {
  deriveDisplayName,
  deriveShortName,
  loadSiteBranding,
  normalizeBaseUrl,
};
