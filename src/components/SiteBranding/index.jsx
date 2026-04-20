import Head from "@docusaurus/Head";
import Link from "@docusaurus/Link";
import useDocusaurusContext from "@docusaurus/useDocusaurusContext";

function useSiteBranding() {
  const { siteConfig } = useDocusaurusContext();
  return siteConfig.customFields?.branding ?? {};
}

function getFileName(shortName, type) {
  switch (type) {
    case "sqlite":
      return `${shortName}.sqlite`;
    case "excel":
      return `${shortName}.xlsx`;
    case "support":
      return `${shortName}_support.xlsx`;
    case "csv":
      return `${shortName}_csv.zip`;
    case "generationLog":
      return "generation.log";
    default:
      throw new Error(`Unsupported file type: ${type}`);
  }
}

function toAbsoluteUrl(baseUrl, path = "/") {
  return new URL(path, `${String(baseUrl || "").replace(/\/+$/, "")}/`).toString();
}

function getReleaseDownloadUrl(branding, type) {
  const fileName = getFileName(branding.shortName ?? "dataset", type);
  return `${branding.releaseBaseUrl}/${fileName}`;
}

function compactObject(value) {
  return Object.fromEntries(
    Object.entries(value).filter(([, entry]) => entry !== undefined),
  );
}

function buildDatasetDescription(datasetName) {
  return `${datasetName} is a synthetic accounting analytics dataset with a SQLite database, Excel workbook, CSV export, process flows, and teaching materials for SQL, audit, financial, managerial, and business-process analysis.`;
}

function buildDatasetStructuredData(branding, { pagePath = "/", sameAsPath, description } = {}) {
  const datasetName = branding.datasetName ?? "Accounting Dataset";
  const datasetUrl = toAbsoluteUrl(branding.baseUrl, pagePath);
  const sameAsUrl = sameAsPath ? toAbsoluteUrl(branding.baseUrl, sameAsPath) : undefined;
  const datasetDescription = description ?? buildDatasetDescription(datasetName);

  return compactObject({
    "@context": "https://schema.org",
    "@type": "Dataset",
    name: datasetName,
    alternateName: branding.displayName,
    description: datasetDescription,
    url: datasetUrl,
    sameAs: sameAsUrl,
    isAccessibleForFree: true,
    license: "https://creativecommons.org/licenses/by-sa/4.0/",
    creator: {
      "@type": "Organization",
      name: "Accounting Analytics Hub",
      url: "https://accountinganalyticshub.com",
    },
    publisher: {
      "@type": "Organization",
      name: "Accounting Analytics Hub",
      url: "https://accountinganalyticshub.com",
    },
    includedInDataCatalog: {
      "@type": "DataCatalog",
      name: "Accounting Analytics Hub",
      url: "https://accountinganalyticshub.com",
    },
    distribution: [
      {
        "@type": "DataDownload",
        name: `${datasetName} SQLite Database`,
        encodingFormat: "application/vnd.sqlite3",
        contentUrl: getReleaseDownloadUrl(branding, "sqlite"),
      },
      {
        "@type": "DataDownload",
        name: `${datasetName} Excel Workbook`,
        encodingFormat:
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        contentUrl: getReleaseDownloadUrl(branding, "excel"),
      },
      {
        "@type": "DataDownload",
        name: `${datasetName} CSV Zip Package`,
        encodingFormat: "application/zip",
        contentUrl: getReleaseDownloadUrl(branding, "csv"),
      },
    ],
  });
}

export function CompanyName() {
  const branding = useSiteBranding();
  return branding.companyName ?? "Accounting Dataset";
}

export function DisplayName() {
  const branding = useSiteBranding();
  return branding.displayName ?? "Dataset";
}

export function DatasetName() {
  const branding = useSiteBranding();
  return branding.datasetName ?? "Accounting Dataset";
}

export function ShortName() {
  const branding = useSiteBranding();
  return branding.shortName ?? "dataset";
}

export function FileName({ type, prefix = "" }) {
  const branding = useSiteBranding();
  const fileName = `${prefix}${getFileName(branding.shortName ?? "dataset", type)}`;
  return <code>{fileName}</code>;
}

export function ReleaseDownloadLink({ type, children }) {
  const branding = useSiteBranding();
  const fileName = getFileName(branding.shortName ?? "dataset", type);
  const href = getReleaseDownloadUrl(branding, type);
  return <Link href={href}>{children ?? fileName}</Link>;
}

export function DatasetStructuredData({ pagePath = "/", sameAsPath, description }) {
  const branding = useSiteBranding();
  const dataset = buildDatasetStructuredData(branding, {
    pagePath,
    sameAsPath,
    description,
  });

  return (
    <Head>
      <script type="application/ld+json">{JSON.stringify(dataset)}</script>
    </Head>
  );
}
