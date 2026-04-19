import clsx from "clsx";
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
      <div className={clsx("docusaurus-mt-lg", styles.callout)}>
        <div className={styles.content}>
          <div>
            <p className={styles.eyebrow}>Feedback</p>
            <h3 className={styles.title}>Report an error on this page</h3>
            <p className={styles.text}>
              Open the GitHub error form with this page already filled in so
              maintainers can triage the issue faster.
            </p>
          </div>
          <Link
            className="button button--primary button--sm"
            href={prefilledIssueUrl}
            target="_blank"
            rel="noopener noreferrer"
          >
            Report This Page
          </Link>
        </div>
      </div>
    </>
  );
}
