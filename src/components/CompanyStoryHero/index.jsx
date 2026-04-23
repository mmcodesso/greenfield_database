import styles from "./styles.module.css";

function StoryAnchor({ label, value }) {
  return (
    <article className={styles.anchorCard}>
      <p className={styles.anchorLabel}>{label}</p>
      <p className={styles.anchorValue}>{value}</p>
    </article>
  );
}

function StoryPanel({ title, text }) {
  return (
    <article className={styles.panel}>
      <h3 className={styles.panelTitle}>{title}</h3>
      <p className={styles.panelText}>{text}</p>
    </article>
  );
}

export default function CompanyStoryHero({
  title,
  lead,
  anchors = [],
  snapshotTitle,
  snapshotText,
  panels = [],
}) {
  return (
    <section className={styles.wrapper}>
      <div className={styles.hero}>
        <div className={styles.heroContent}>
          <p className={styles.kicker}>Company Story</p>
          <h1 className={styles.title}>{title}</h1>
          <p className={styles.lead}>{lead}</p>
          <div className={styles.anchorGrid}>
            {anchors.map((anchor) => (
              <StoryAnchor
                key={anchor.label}
                label={anchor.label}
                value={anchor.value}
              />
            ))}
          </div>
        </div>
      </div>

      <div className={styles.snapshot}>
        <div className={styles.snapshotHeader}>
          <p className={styles.sectionLabel}>Business Snapshot</p>
          <h2 className={styles.snapshotTitle}>{snapshotTitle}</h2>
          <p className={styles.snapshotText}>{snapshotText}</p>
        </div>
        <div className={styles.panelGrid}>
          {panels.map((panel) => (
            <StoryPanel key={panel.title} title={panel.title} text={panel.text} />
          ))}
        </div>
      </div>
    </section>
  );
}
