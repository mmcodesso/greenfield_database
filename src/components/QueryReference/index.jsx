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

function humanizeQueryFilename(filename) {
  const lowerCaseWords = new Set([
    "and",
    "by",
    "for",
    "in",
    "of",
    "on",
    "or",
    "to",
    "vs",
    "with",
    "without",
  ]);
  const acronyms = new Map([
    ["ap", "AP"],
    ["ar", "AR"],
    ["bom", "BOM"],
    ["fg", "FG"],
    ["gl", "GL"],
    ["mrp", "MRP"],
    ["o2c", "O2C"],
    ["p2p", "P2P"],
    ["sod", "SOD"],
    ["wip", "WIP"],
  ]);

  return filename
    .replace(/^\d+_/, "")
    .replace(/\.sql$/, "")
    .split("_")
    .map((word, index) => {
      const lowerWord = word.toLowerCase();
      if (acronyms.has(lowerWord)) {
        return acronyms.get(lowerWord);
      }
      if (index > 0 && lowerCaseWords.has(lowerWord)) {
        return lowerWord;
      }
      return lowerWord.charAt(0).toUpperCase() + lowerWord.slice(1);
    })
    .join(" ");
}

function normalizeSequenceHelper(lead) {
  if (!lead) {
    return undefined;
  }

  const trimmed = lead.trim();
  if (!trimmed || /^run$/i.test(trimmed)) {
    return undefined;
  }

  return trimmed;
}

export function QueryReference({
  queryKey,
  label,
  variant = "catalog",
  helperText,
  showMetadata = false,
}) {
  const entry = getQueryEntry(queryKey);
  const queryUrl = useBaseUrl(entry.publicPath);
  const displayLabel = label ?? humanizeQueryFilename(entry.filename);
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

  function handleToggle() {
    if (expanded) {
      setExpanded(false);
      return;
    }

    setExpanded(true);
    void loadSql();
  }

  return (
    <div className={clsx(styles.reference, styles[variant])}>
      <div className={styles.referenceHeader}>
        <div className={styles.referenceText}>
          <div className={styles.referenceLabel}>{displayLabel}</div>
          {helperText ? <p className={styles.referenceHelper}>{helperText}</p> : null}
          {showMetadata ? (
            <div className={styles.metadata}>
              {entry.teachingObjective ? (
                <p className={styles.metadataObjective}>{entry.teachingObjective}</p>
              ) : null}
              {entry.outputShape || entry.mainTables ? (
                <dl className={styles.metadataList}>
                  {entry.outputShape ? (
                    <>
                      <dt>Output</dt>
                      <dd>{entry.outputShape}</dd>
                    </>
                  ) : null}
                  {entry.mainTables ? (
                    <>
                      <dt>Main tables</dt>
                      <dd>{entry.mainTables}</dd>
                    </>
                  ) : null}
                </dl>
              ) : null}
            </div>
          ) : null}
        </div>
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
            showMetadata
          />
        ))}
      </div>
    </div>
  );
}

export function QueryGroupCatalog({ groups }) {
  return (
    <div className={styles.groupList}>
      {groups.map((group) => (
        <section key={group.title} className={styles.group}>
          <h3>{group.title}</h3>
          {group.description ? <p className={styles.groupDescription}>{group.description}</p> : null}
          <QueryCatalog
            items={group.items}
            helperText="Open a query when you want to inspect the SQL, copy it into SQLite, or trace the source-table logic."
          />
        </section>
      ))}
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
            <QueryReference
              queryKey={item.queryKey}
              helperText={normalizeSequenceHelper(item.lead)}
              variant="sequence"
            />
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
