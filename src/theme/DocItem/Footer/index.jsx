import Link from "@docusaurus/Link";
import { useLocation } from "@docusaurus/router";
import { useDoc } from "@docusaurus/plugin-content-docs/client";
import useDocusaurusContext from "@docusaurus/useDocusaurusContext";
import DocItemFooter from "@theme-original/DocItem/Footer";

import styles from "./styles.module.css";

function buildPageUrl(siteConfig, permalink, hash) {
  const base = `${siteConfig.url}${siteConfig.baseUrl ?? "/"}`;
  return new URL(`${permalink}${hash || ""}`, base).toString();
}

function buildSectionContext(hash) {
  if (!hash) {
    return "Page-level report";
  }

  return decodeURIComponent(hash.slice(1)).replace(/-/g, " ");
}

function buildPrefilledIssueUrl(baseUrl, siteConfig, metadata, hash) {
  const url = new URL(baseUrl);

  url.searchParams.set(
    "page_url",
    buildPageUrl(siteConfig, metadata.permalink, hash),
  );
  url.searchParams.set("page_title", metadata.title);
  url.searchParams.set("source_file", metadata.source);
  url.searchParams.set("section_context", buildSectionContext(hash));

  return url.toString();
}

export default function Footer() {
  const { siteConfig } = useDocusaurusContext();
  const { metadata } = useDoc();
  const { hash } = useLocation();
  const branding = siteConfig.customFields?.branding ?? {};
  const errorIssueUrl = branding.errorIssueUrl;

  if (!errorIssueUrl) {
    return <DocItemFooter />;
  }

  const prefilledIssueUrl = buildPrefilledIssueUrl(
    errorIssueUrl,
    siteConfig,
    metadata,
    hash,
  );

  return (
    <>
      <DocItemFooter />
      <div className={styles.feedbackRow}>
        <span className={styles.label}>Notice a mistake?</span>
        <Link
          className={styles.link}
          href={prefilledIssueUrl}
          target="_blank"
          rel="noopener noreferrer"
        >
          Report an error on this page
        </Link>
      </div>
    </>
  );
}
