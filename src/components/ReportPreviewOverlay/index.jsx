import React, { useEffect, useState } from "react";
import clsx from "clsx";

import styles from "./styles.module.css";

function formatPreviewValue(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
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

export function ReportPreviewOverlay({ isOpen, onClose, previewUrl, title }) {
  const [preview, setPreview] = useState(null);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isOpen || preview) {
      return undefined;
    }

    let ignore = false;

    async function loadPreview() {
      setStatus("loading");
      setError("");

      try {
        const response = await fetch(previewUrl);
        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`);
        }

        const payload = await response.json();
        if (!ignore) {
          setPreview(payload);
          setStatus("ready");
        }
      } catch (fetchError) {
        if (!ignore) {
          setStatus("error");
          setError(fetchError instanceof Error ? fetchError.message : "Unknown error");
        }
      }
    }

    void loadPreview();

    return () => {
      ignore = true;
    };
  }, [isOpen, preview, previewUrl]);

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    const previousOverflow = document.body.style.overflow;
    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  return (
    <div
      className={styles.backdrop}
      role="presentation"
      onClick={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div
        className={styles.modal}
        role="dialog"
        aria-modal="true"
        aria-label={`${title} preview`}
        onClick={(event) => event.stopPropagation()}
      >
        <div className={styles.modalToolbar}>
          <div>
            <p className={styles.modalTitle}>{title}</p>
            <p className={styles.modalHint}>Preview sample from the generated report.</p>
          </div>
          <button type="button" className={styles.closeButton} onClick={onClose}>
            Close
          </button>
        </div>
        <div className={styles.viewport}>
          {status === "loading" ? <p className={styles.message}>Loading preview...</p> : null}
          {status === "error" ? (
            <p className={clsx(styles.message, styles.error)}>
              Could not load this preview. {error}
            </p>
          ) : null}
          {status === "ready" && preview ? <PreviewTable preview={preview} /> : null}
        </div>
      </div>
    </div>
  );
}
