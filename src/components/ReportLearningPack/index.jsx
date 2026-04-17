import React, { useState } from "react";
import clsx from "clsx";
import Link from "@docusaurus/Link";
import useBaseUrl from "@docusaurus/useBaseUrl";

import reportManifest from "@site/src/generated/reportManifest";
import reportPackManifest from "@site/src/generated/reportPackManifest";
import queryManifest from "@site/src/generated/queryManifest";
import styles from "./styles.module.css";

function getPack(packOrKey) {
  if (typeof packOrKey === "string") {
    const pack = reportPackManifest[packOrKey];
    if (!pack) {
      throw new Error(`Unknown report pack: ${packOrKey}`);
    }
    return pack;
  }
  return packOrKey;
}

function getReportEntry(reportSlug) {
  const entry = reportManifest[reportSlug];
  if (!entry) {
    throw new Error(`Unknown report key: ${reportSlug}`);
  }
  return entry;
}

function getQueryEntry(reportEntry) {
  const queryKey = String(reportEntry.queryPath).replace(/^queries\//, "");
  const queryEntry = queryManifest[queryKey];
  if (!queryEntry) {
    throw new Error(`Unknown query key for report ${reportEntry.slug}: ${queryKey}`);
  }
  return queryEntry;
}

function formatPreviewValue(value) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }
  return String(value);
}

function PreviewTable({ preview }) {
  return (
    <div className={styles.previewBody}>
      <div className={styles.previewMeta}>
        <span>{preview.rowCount} rows total</span>
        <span>Showing {preview.previewRowCount}</span>
        <span>Generated {preview.generatedAt}</span>
      </div>
      <div className={styles.tableWrapper}>
        <table className={styles.previewTable}>
          <thead>
            <tr>
              {preview.columns.map((column) => (
                <th key={column}>{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {preview.rows.map((row, index) => (
              <tr key={`${preview.slug}-${index}`}>
                {preview.columns.map((column) => (
                  <td key={`${preview.slug}-${index}-${column}`}>{formatPreviewValue(row[column])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ReportLearningCard({ item, index }) {
  const reportEntry = getReportEntry(item.reportSlug);
  const queryEntry = getQueryEntry(reportEntry);
  const previewUrl = useBaseUrl(reportEntry.previewPath);
  const excelUrl = useBaseUrl(reportEntry.excelPath);
  const csvUrl = useBaseUrl(reportEntry.csvPath);
  const queryUrl = useBaseUrl(queryEntry.publicPath);
  const [expanded, setExpanded] = useState(false);
  const [preview, setPreview] = useState(null);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");

  async function loadPreview() {
    if (status !== "idle" || preview) {
      return;
    }

    setStatus("loading");
    setError("");

    try {
      const response = await fetch(previewUrl);
      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }

      const payload = await response.json();
      setPreview(payload);
      setStatus("ready");
    } catch (fetchError) {
      setStatus("error");
      setError(fetchError instanceof Error ? fetchError.message : "Unknown error");
    }
  }

  function handleToggle() {
    if (expanded) {
      setExpanded(false);
      return;
    }

    setExpanded(true);
    void loadPreview();
  }

  return (
    <article className={styles.card}>
      <div className={styles.cardFrame}>
        <div className={styles.stepBadge}>{index + 1}</div>
        <div className={styles.cardContent}>
          <div className={styles.cardHeader}>
            <div className={styles.cardText}>
              <h3 className={styles.cardTitle}>{reportEntry.title}</h3>
              <p className={styles.cardDescription}>{reportEntry.description}</p>
              <div className={styles.chipRow}>
                <span className={styles.chip}>{item.teachingRole}</span>
                <span className={styles.chip}>{reportEntry.processGroupLabel}</span>
                <span className={styles.chip}>{reportEntry.cadence}</span>
              </div>
            </div>
            <div className={styles.actionRow}>
              <button className={styles.primaryAction} type="button" onClick={handleToggle} aria-expanded={expanded}>
                {expanded ? "Hide Preview" : "Preview"}
              </button>
              {reportEntry.excelEnabled ? (
                <a className={styles.secondaryAction} href={excelUrl}>
                  Download Excel
                </a>
              ) : null}
              {reportEntry.csvEnabled ? (
                <a className={styles.secondaryAction} href={csvUrl}>
                  Download CSV
                </a>
              ) : null}
              <a className={styles.secondaryAction} href={queryUrl}>
                Open SQL
              </a>
              {item.relatedLink ? (
                <Link className={styles.secondaryAction} to={item.relatedLink.href}>
                  {item.relatedLink.label}
                </Link>
              ) : null}
            </div>
          </div>
          <div className={styles.reasonBlock}>
            <h4 className={styles.subheading}>Why This Report Belongs in the Lens</h4>
            <p className={styles.reasonText}>{item.whyItMatters}</p>
          </div>
          <div className={styles.learningGrid}>
            <div className={styles.learningColumn}>
              <h4 className={styles.subheading}>Discussion Questions</h4>
              <ul className={styles.list}>
                {item.discussionQuestions.map((question) => (
                  <li key={question}>{question}</li>
                ))}
              </ul>
            </div>
            <div className={styles.learningColumn}>
              <h4 className={styles.subheading}>Suggested Analysis</h4>
              <ul className={styles.list}>
                {item.suggestedAnalysis.map((analysis) => (
                  <li key={analysis}>{analysis}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
      {expanded ? (
        <div className={styles.previewPanel}>
          {status === "loading" ? <p className={styles.message}>Loading preview...</p> : null}
          {status === "error" ? (
            <p className={clsx(styles.message, styles.error)}>
              Could not load this preview. {error}
            </p>
          ) : null}
          {status === "ready" && preview ? <PreviewTable preview={preview} /> : null}
        </div>
      ) : null}
    </article>
  );
}

export function ReportLearningPack({ pack }) {
  const resolvedPack = getPack(pack);

  return (
    <div className={styles.pack}>
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Audience and Purpose</h2>
        <p className={styles.sectionText}>{resolvedPack.audience}</p>
      </section>
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Business Lens</h2>
        <p className={styles.sectionText}>{resolvedPack.businessLens}</p>
      </section>
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Core Questions</h2>
        <ul className={styles.list}>
          {resolvedPack.coreQuestions.map((question) => (
            <li key={question}>{question}</li>
          ))}
        </ul>
      </section>
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Recommended Report Sequence</h2>
        <ol className={styles.sequenceList}>
          {resolvedPack.reports.map((item) => {
            const entry = getReportEntry(item.reportSlug);
            return (
              <li key={item.reportSlug} className={styles.sequenceItem}>
                <span className={styles.sequenceTitle}>{entry.title}</span>
                <span className={styles.sequenceMeta}>{item.teachingRole}</span>
              </li>
            );
          })}
        </ol>
      </section>
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Report Blocks</h2>
        <div className={styles.blockList}>
          {resolvedPack.reports.map((item, index) => (
            <ReportLearningCard key={item.reportSlug} item={item} index={index} />
          ))}
        </div>
      </section>
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Where to Go Next</h2>
        <ul className={styles.list}>
          {resolvedPack.whereToGoNext.map((item) => (
            <li key={`${item.href}-${item.label}`}>
              <Link to={item.href}>{item.label}</Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
