import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { loadSiteBranding } = require("../config/loadSiteBranding.cjs");

const branding = loadSiteBranding();

function escapeXml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}

function ensureDir(filePath) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

function writeFile(targetPath, contents) {
  ensureDir(targetPath);
  fs.writeFileSync(targetPath, contents, "utf8");
}

function buildSocialCardSvg() {
  const title = escapeXml(branding.datasetName);
  const displayName = escapeXml(branding.displayName);

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630" role="img" aria-labelledby="title desc">
  <title id="title">${title}</title>
  <desc id="desc">Student-first documentation for accounting analytics courses.</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#f7f2e7" />
      <stop offset="55%" stop-color="#efe2bf" />
      <stop offset="100%" stop-color="#d2e4d9" />
    </linearGradient>
  </defs>
  <rect width="1200" height="630" fill="url(#bg)" />
  <circle cx="970" cy="130" r="150" fill="#1f6b52" opacity="0.18" />
  <circle cx="220" cy="520" r="200" fill="#e1a43a" opacity="0.18" />
  <rect x="108" y="110" width="510" height="350" rx="36" fill="#173a2f" />
  <rect x="164" y="166" width="398" height="238" rx="18" fill="#fffdf8" />
  <rect x="208" y="210" width="310" height="20" rx="10" fill="#1f6b52" opacity="0.92" />
  <rect x="208" y="260" width="280" height="20" rx="10" fill="#1f6b52" opacity="0.74" />
  <rect x="208" y="310" width="210" height="20" rx="10" fill="#1f6b52" opacity="0.56" />
  <circle cx="518" cy="338" r="42" fill="#e1a43a" />
  <text x="670" y="210" fill="#173a2f" font-family="Georgia, serif" font-size="58" font-weight="700">
    ${title}
  </text>
  <text x="670" y="294" fill="#173a2f" font-family="Arial, sans-serif" font-size="32">
    Student-first docs for accounting analytics
  </text>
  <text x="670" y="344" fill="#2d5646" font-family="Arial, sans-serif" font-size="28">
    SQL, Excel, auditing, process tracing, and course adoption
  </text>
  <text x="670" y="420" fill="#2d5646" font-family="Arial, sans-serif" font-size="26">
    ${displayName} integrated teaching environment
  </text>
</svg>
`;
}

function buildFaviconSvg() {
  const title = escapeXml(branding.datasetName);
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-labelledby="title">
  <title>${title}</title>
  <rect width="64" height="64" rx="16" fill="#173a2f" />
  <path d="M18 18h28v28H18z" fill="#f7f2e7" />
  <path d="M24 24h16v3H24zm0 7h16v3H24zm0 7h10v3H24z" fill="#1f6b52" />
  <circle cx="42" cy="42" r="6" fill="#e1a43a" />
</svg>
`;
}

writeFile(path.join("static", "CNAME"), `${branding.domain}\n`);
writeFile(path.join("static", "img", "site-social-card.svg"), buildSocialCardSvg());
writeFile(path.join("static", "img", "favicon.svg"), buildFaviconSvg());
