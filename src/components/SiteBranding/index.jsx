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
  const href = `${branding.releaseBaseUrl}/${fileName}`;
  return <Link href={href}>{children ?? fileName}</Link>;
}
