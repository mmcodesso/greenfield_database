import clsx from "clsx";
import Link from "@docusaurus/Link";
import Layout from "@theme/Layout";

import styles from "./index.module.css";

const audienceCards = [
  {
    title: "Students",
    text: "Start with the company story, process guides, schema reference, and GLEntry posting reference before moving into starter SQL or Excel paths.",
    href: "/docs/quick-start",
    cta: "Open the quick start",
  },
  {
    title: "Instructors",
    text: "Adopt the database with a course-ready sequence for AIS, analytics, auditing, SQL, and Excel assignments.",
    href: "/docs/teach-with-greenfield/instructor-adoption",
    cta: "Read the adoption guide",
  },
];

const highlights = [
  "55 linked tables across accounting, O2C, P2P, manufacturing, payroll, time, and planning.",
  "Ready for SQL labs, Excel analysis, auditing analytics, and process-to-ledger tracing.",
  "Built around a fictional hybrid manufacturer-distributor with five fiscal years of activity.",
];

const deliverables = [
  "SQLite database for query work",
  "Excel workbook for pivots and classroom exercises",
  "Ready-to-use files published through GitHub Releases",
];

export default function Home() {
  return (
    <Layout
      title="Student-first accounting analytics documentation"
      description="Greenfield Accounting Dataset provides student-first documentation and teaching materials for accounting analytics courses."
    >
      <main className={styles.page}>
        <section className={styles.hero}>
          <div className={styles.heroBackdrop} />
          <div className={styles.heroContent}>
            <p className={styles.kicker}>Accounting analytics database</p>
            <h1 className={styles.title}>Teach the business before the joins.</h1>
            <p className={styles.lede}>
              Greenfield Accounting Dataset is a synthetic business database for
              accounting students who need business context, process logic, SQL,
              Excel, and audit-style analysis in one place.
            </p>
            <div className={styles.actions}>
              <Link className="button button--primary button--lg" to="/docs/quick-start">
                Open quick start
              </Link>
              <Link className="button button--secondary button--lg" to="/docs/downloads">
                Download the data
              </Link>
              <Link className="button button--secondary button--lg" to="/docs/teach-with-greenfield/instructor-adoption">
                Adopt it in a course
              </Link>
            </div>
            <div className={styles.ribbon}>
              <span>Hybrid manufacturer-distributor</span>
              <span>Five fiscal years</span>
              <span>Student-first docs</span>
            </div>
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <p className={styles.sectionLabel}>Who this is for</p>
            <h2>Different entry points, one connected dataset.</h2>
          </div>
          <div className={styles.cardGrid}>
            {audienceCards.map((card) => (
              <article key={card.title} className={styles.card}>
                <h3>{card.title}</h3>
                <p>{card.text}</p>
                <Link className={styles.cardLink} to={card.href}>
                  {card.cta}
                </Link>
              </article>
            ))}
          </div>
        </section>

        <section className={clsx(styles.section, styles.splitSection)}>
          <div className={styles.panel}>
            <p className={styles.sectionLabel}>What the database includes</p>
            <ul className={styles.list}>
              {highlights.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
          <div className={styles.panel}>
            <p className={styles.sectionLabel}>Typical teaching package</p>
            <ul className={styles.list}>
              {deliverables.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <p className={styles.panelNote}>
              Most students should download the SQLite database and Excel workbook
              from the latest release, then start with the docs.
            </p>
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <p className={styles.sectionLabel}>Choose a path</p>
            <h2>Move from orientation to analysis without getting lost in the repo.</h2>
          </div>
          <div className={styles.pathGrid}>
            <Link className={styles.pathCard} to="/docs/company-story">
              <strong>Learn the business</strong>
              <span>Company context, process flows, and why each document exists.</span>
            </Link>
            <Link className={styles.pathCard} to="/docs/analytics">
              <strong>Analyze the data</strong>
              <span>Starter SQL, Excel workflows, and guided accounting analytics cases.</span>
            </Link>
            <Link className={styles.pathCard} to="/docs/reference/schema">
              <strong>Reference the model</strong>
              <span>Schema groups, join paths, and posting behavior for student and instructor work.</span>
            </Link>
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.repoBanner}>
            <div>
              <p className={styles.sectionLabel}>Repository</p>
              <h2>Need teaching setup notes, source files, or contribution guidance?</h2>
            </div>
            <div className={styles.repoActions}>
              <Link className="button button--primary" href="https://github.com/mmcodesso/greenfield_database">
                Open GitHub
              </Link>
              <Link className="button button--secondary" to="/docs/technical/dataset-delivery">
                Build and delivery guide
              </Link>
            </div>
          </div>
        </section>
      </main>
    </Layout>
  );
}
