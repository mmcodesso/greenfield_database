import React, { useState } from "react";
import Link from "@docusaurus/Link";
import useBaseUrl from "@docusaurus/useBaseUrl";

import { ReportPreviewOverlay } from "@site/src/components/ReportPreviewOverlay";
import reportManifest from "@site/src/generated/reportManifest";
import reportPackManifest from "@site/src/generated/reportPackManifest";
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

function ReportLearningCard({ item, index }) {
  const reportEntry = getReportEntry(item.reportSlug);
  const previewUrl = useBaseUrl(reportEntry.previewPath);
  const excelUrl = useBaseUrl(reportEntry.excelPath);
  const csvUrl = useBaseUrl(reportEntry.csvPath);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);

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
              <button
                className={styles.primaryAction}
                type="button"
                onClick={() => setIsPreviewOpen(true)}
                aria-haspopup="dialog"
              >
                Preview
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
            </div>
          </div>
          <div className={styles.reasonBlock}>
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
      <ReportPreviewOverlay
        isOpen={isPreviewOpen}
        onClose={() => setIsPreviewOpen(false)}
        previewUrl={previewUrl}
        title={reportEntry.title}
      />
    </article>
  );
}

export function ReportLearningPack({ pack }) {
  const resolvedPack = getPack(pack);

  return (
    <div className={styles.pack}>
      <section className={styles.section}>
        {resolvedPack.openingParagraphs.map((paragraph) => (
          <p key={paragraph} className={styles.sectionText}>
            {paragraph}
          </p>
        ))}
      </section>
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>How to Approach This Perspective</h2>
        <ul className={styles.list}>
          {resolvedPack.approachGuidance.map((guidance) => (
            <li key={guidance}>{guidance}</li>
          ))}
        </ul>
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
        <h2 className={styles.sectionTitle}>Next Steps</h2>
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
