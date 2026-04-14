import React, { useState } from "react";
import clsx from "clsx";
import CodeBlock from "@theme/CodeBlock";
import useBaseUrl from "@docusaurus/useBaseUrl";
import queryManifest from "@site/src/generated/queryManifest";
import styles from "./styles.module.css";

function getQueryEntry(queryKey) {
  const entry = queryManifest[queryKey];
  if (!entry) {
    throw new Error(`Unknown query key: ${queryKey}`);
  }
  return entry;
}

export function QueryReference({
  queryKey,
  label,
  variant = "catalog",
  helperText,
}) {
  const entry = getQueryEntry(queryKey);
  const queryUrl = useBaseUrl(entry.publicPath);
  const [expanded, setExpanded] = useState(false);
  const [sql, setSql] = useState("");
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");

  async function loadSql() {
    if (status !== "idle" || sql) {
      return;
    }

    setStatus("loading");
    setError("");

    try {
      const response = await fetch(queryUrl);
      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }
      const text = await response.text();
      setSql(text.trimEnd());
      setStatus("ready");
    } catch (fetchError) {
      setStatus("error");
      setError(fetchError instanceof Error ? fetchError.message : "Unknown error");
    }
  }

  async function handleToggle() {
    const nextExpanded = !expanded;
    setExpanded(nextExpanded);
    if (nextExpanded) {
      await loadSql();
    }
  }

  return (
    <div className={clsx(styles.reference, styles[variant])}>
      {(label || helperText) && (
        <div className={styles.referenceHeader}>
          {label ? <div className={styles.referenceLabel}>{label}</div> : null}
          {helperText ? <p className={styles.referenceHelper}>{helperText}</p> : null}
        </div>
      )}
      <div className={styles.referenceBar}>
        <code className={styles.filename}>{entry.filename}</code>
        <button
          className={styles.toggle}
          type="button"
          onClick={handleToggle}
          aria-expanded={expanded}
        >
          {expanded ? "Hide SQL" : "Show SQL"}
        </button>
      </div>
      {expanded ? (
        <div className={styles.codePanel}>
          {status === "loading" ? (
            <p className={styles.message}>Loading SQL...</p>
          ) : null}
          {status === "error" ? (
            <p className={clsx(styles.message, styles.error)}>
              Could not load this query. {error}
            </p>
          ) : null}
          {status === "ready" ? (
            <CodeBlock language="sql" title={entry.filename}>
              {sql}
            </CodeBlock>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export function QueryCatalog({ items, helperText }) {
  const message =
    helperText ??
    "Click Show SQL to open a query, review the logic, and copy it into SQLite or a compatible SQL tool.";

  return (
    <div className={styles.section}>
      <p className={styles.sectionHelper}>{message}</p>
      <div className={styles.catalogList}>
        {items.map((item) => (
          <QueryReference
            key={item.queryKey}
            label={item.label}
            queryKey={item.queryKey}
            variant="catalog"
          />
        ))}
      </div>
    </div>
  );
}

export function QuerySequence({ items, helperText }) {
  const message =
    helperText ??
    "Work through the queries in order. Expand a query when you want to inspect the SQL or copy it into your tool.";

  return (
    <div className={styles.section}>
      <p className={styles.sectionHelper}>{message}</p>
      <ol className={styles.sequenceList}>
        {items.map((item) => (
          <li key={`${item.queryKey}-${item.lead}`} className={styles.sequenceItem}>
            <p className={styles.sequenceLead}>{item.lead}</p>
            <QueryReference queryKey={item.queryKey} variant="sequence" />
          </li>
        ))}
      </ol>
    </div>
  );
}

export function QueryMatrix({ items, helperText }) {
  const message =
    helperText ??
    "Expand any query in the first column when you want to review the SQL and copy it into your audit workflow.";

  return (
    <div className={styles.section}>
      <p className={styles.sectionHelper}>{message}</p>
      <div className={styles.tableWrapper}>
        <table className={styles.matrixTable}>
          <thead>
            <tr>
              <th>Query</th>
              <th>Recommended use</th>
              <th>Expected anomaly types</th>
              <th>Main tables</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.queryKey}>
                <td className={styles.matrixQueryCell}>
                  <QueryReference queryKey={item.queryKey} variant="matrix" />
                </td>
                <td>{item.recommendedUse}</td>
                <td>
                  <code>{item.expectedAnomalyTypes}</code>
                </td>
                <td>{item.mainTables}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
