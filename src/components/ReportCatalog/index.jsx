import React, { useState } from "react";
import useBaseUrl from "@docusaurus/useBaseUrl";

import { ReportPreviewOverlay } from "@site/src/components/ReportPreviewOverlay";
import reportManifest from "@site/src/generated/reportManifest";
import styles from "./styles.module.css";

function getReportEntry(reportKey) {
  const entry = reportManifest[reportKey];
  if (!entry) {
    throw new Error(`Unknown report key: ${reportKey}`);
  }
  return entry;
}

function ReportCard({ reportKey }) {
  const entry = getReportEntry(reportKey);
  const previewUrl = useBaseUrl(entry.previewPath);
  const excelUrl = useBaseUrl(entry.excelPath);
  const csvUrl = useBaseUrl(entry.csvPath);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);

  return (
    <article className={styles.card}>
      <div className={styles.cardHeader}>
        <div className={styles.cardText}>
          <h4 className={styles.cardTitle}>{entry.title}</h4>
          <p className={styles.cardDescription}>{entry.description}</p>
          <div className={styles.chipRow}>
            <span className={styles.chip}>{entry.processGroupLabel}</span>
            <span className={styles.chip}>{entry.cadence}</span>
          </div>
        </div>
        <div className={styles.actionRow}>
          <button
            className={styles.primaryAction}
            type="button"
            onClick={() => setIsPreviewOpen(true)}
            aria-haspopup="dialog"
          >
            Preview
          </button>
          {entry.excelEnabled ? (
            <a className={styles.secondaryAction} href={excelUrl}>
              Download Excel
            </a>
          ) : null}
          {entry.csvEnabled ? (
            <a className={styles.secondaryAction} href={csvUrl}>
              Download CSV
            </a>
          ) : null}
        </div>
      </div>
      <ReportPreviewOverlay
        isOpen={isPreviewOpen}
        onClose={() => setIsPreviewOpen(false)}
        previewUrl={previewUrl}
        title={entry.title}
      />
    </article>
  );
}

export function ReportCatalog({ groups, helperText }) {
  return (
    <div className={styles.section}>
      {helperText ? <p className={styles.sectionHelper}>{helperText}</p> : null}
      {groups.map((group) => (
        <section key={group.processGroup} className={styles.group}>
          <div className={styles.groupHeader}>
            <h3 className={styles.groupTitle}>{group.processGroupLabel}</h3>
          </div>
          <div className={styles.groupGrid}>
            {group.items.map((item) => (
              <ReportCard key={item.reportKey} reportKey={item.reportKey} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
