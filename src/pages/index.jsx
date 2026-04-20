import Link from "@docusaurus/Link";
import useDocusaurusContext from "@docusaurus/useDocusaurusContext";
import Layout from "@theme/Layout";
import { DatasetStructuredData } from "@site/src/components/SiteBranding";

import styles from "./index.module.css";

const proofPoints = [
  {
    title: "Process-to-ledger traceability",
    text: "Follow business events from source documents through process flow and into GLEntry with clear traceability.",
  },
  {
    title: "SQL and Excel ready",
    text: "Use one integrated environment for query work, workbook analysis, and guided interpretation without rebuilding the dataset first.",
  },
  {
    title: "Teaching materials included",
    text: "Pair process guides, schema and posting references, analytics pages, and cases so students learn the business before the joins.",
  },
];

const classroomUses = [
  {
    title: "AIS and business process courses",
    text: "Teach why each document exists, how process cycles connect, and which events actually reach the ledger.",
  },
  {
    title: "SQL and accounting analytics",
    text: "Support structured query work with one company model that already connects process logic, documents, and accounting outcomes.",
  },
  {
    title: "Excel analytics and interpretation",
    text: "Use the same environment for pivots, workbook-based analysis, and classroom discussion without losing business context.",
  },
  {
    title: "Auditing, controls, and managerial analysis",
    text: "Trace approvals, exceptions, labor, variance, portfolio behavior, and control logic inside one integrated teaching dataset.",
  },
];

const adoptionPoints = [
  "One company and one dataset can support multiple accounting courses.",
  "The same environment works for demos, guided labs, process tracing, SQL, Excel, and open-ended assignments.",
  "Students can start with business context and then move into analysis without switching models or file structures.",
];

const includedAssets = [
  {
    title: "SQLite accounting database",
    text: "Download a ready-to-query SQLite database with 68 tables for SQL practice, source-to-ledger tracing, and accounting analytics labs.",
  },
  {
    title: "Excel workbook and CSV export",
    text: "Work from the same synthetic accounting dataset in an Excel workbook or a CSV package when the class needs pivots, charts, or external tooling.",
  },
  {
    title: "Financial, managerial, and audit paths",
    text: "Use one dataset across financial reporting, managerial analysis, audit procedures, working-capital review, payroll, and manufacturing cases.",
  },
  {
    title: "Teaching materials with the data",
    text: "Pair downloads with process flows, schema guidance, SQL walkthroughs, analytics pages, and instructor adoption support instead of starting from bare tables.",
  },
];

const faqItems = [
  {
    question: "Is this a synthetic accounting analytics dataset?",
    answer:
      "Yes. Charles River is a synthetic accounting analytics dataset built for teaching, open reuse, and broad classroom distribution without exposing real company transactions.",
  },
  {
    question: "What files are included?",
    answer:
      "The published package includes a SQLite database, an Excel workbook, and a CSV export so users can move between SQL practice, workbook analysis, and table-by-table tooling without switching datasets.",
  },
  {
    question: "Can students use it for SQL practice and audit work?",
    answer:
      "Yes. The dataset is designed for SQL practice, source-to-ledger tracing, audit exception review, financial analysis, managerial accounting, and business-process teaching in one connected model.",
  },
  {
    question: "Who is it for?",
    answer:
      "It is built for AIS, accounting analytics, audit, financial, managerial, and business-process courses where students need a realistic accounting database plus guided teaching materials.",
  },
];

const nextSteps = [
  {
    title: "Start Here",
    text: "Open the main student entry page for the recommended reading order, downloads, and core references.",
    href: "/docs/",
  },
  {
    title: "See Process Flows",
    text: "Go straight to the business cycles if you want to understand documents, process logic, and ledger touchpoints.",
    href: "/docs/process-flows",
  },
  {
    title: "Adopt in a Course",
    text: "Use the instructor guide when you want teaching sequence, setup notes, and course-ready adoption support.",
    href: "/docs/teach-with-data/instructor-adoption",
  },
];

export default function Home() {
  const { siteConfig } = useDocusaurusContext();
  const branding = siteConfig.customFields?.branding ?? {};
  const displayName = branding.displayName ?? "Dataset";
  const datasetName = branding.datasetName ?? "Accounting Dataset";
  const homeDescription = `${datasetName} is a synthetic accounting analytics dataset and SQLite database for SQL practice, Excel analysis, audit review, financial reporting, managerial accounting, and classroom teaching.`;

  return (
    <Layout
      title="Synthetic Accounting Analytics Dataset for SQL, Excel, Audit, and Teaching"
      description={homeDescription}
    >
      <DatasetStructuredData pagePath="/" description={homeDescription} />
      <main className={styles.page}>
        <section className={styles.hero}>
          <div className={styles.heroBackdrop} />
          <div className={styles.heroContent}>
            <p className={styles.kicker}>Synthetic accounting analytics dataset</p>
            <h1 className={styles.title}>Teach the business before the joins.</h1>
            <p className={styles.lede}>
              {displayName} is a synthetic ERP-style accounting analytics
              environment that helps students trace business activity from
              source documents to GLEntry using SQL, Excel, and guided teaching
              materials.
            </p>
            <div className={styles.actions}>
              <Link className="button button--primary button--lg" to="/docs/">
                Start Here
              </Link>
              <Link className="button button--secondary button--lg" to="/docs/process-flows">
                See Process Flows
              </Link>
              <Link className="button button--secondary button--lg" to="/docs/teach-with-data/instructor-adoption">
                Adopt in a Course
              </Link>
            </div>
            <div className={styles.ribbon}>
              <span>Source documents to GLEntry</span>
              <span>SQL and Excel ready</span>
              <span>Classroom-ready teaching materials</span>
            </div>
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <p className={styles.sectionLabel}>{branding.whyTitle ?? "Why This Dataset"}</p>
            <h2>Connect business activity to ledger impact.</h2>
          </div>
          <p className={styles.whyText}>
            Students often see tables before they understand the business
            process and accounting logic behind them. {displayName} exists to solve
            that teaching problem by connecting business events, source
            documents, process flows, and posted ledger activity in one
            integrated model.
          </p>
        </section>

        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <p className={styles.sectionLabel}>What's Included</p>
            <h2>One accounting database, multiple classroom-ready formats.</h2>
          </div>
          <div className={styles.cardGrid}>
            {includedAssets.map((asset) => (
              <article key={asset.title} className={styles.card}>
                <h3>{asset.title}</h3>
                <p>{asset.text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <p className={styles.sectionLabel}>What Makes It Different</p>
            <h2>One teaching model, three proof points.</h2>
          </div>
          <div className={styles.cardGrid}>
            {proofPoints.map((point) => (
              <article key={point.title} className={styles.card}>
                <h3>{point.title}</h3>
                <p>{point.text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <p className={styles.sectionLabel}>What You Can Do With It</p>
            <h2>Use one environment across multiple accounting teaching paths.</h2>
          </div>
          <div className={styles.cardGrid}>
            {classroomUses.map((item) => (
              <article key={item.title} className={styles.card}>
                <h3>{item.title}</h3>
                <p>{item.text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <p className={styles.sectionLabel}>Why Instructors Adopt It</p>
            <h2>One company, one dataset, multiple course and assignment styles.</h2>
          </div>
          <div className={styles.adoptionBlock}>
            <p className={styles.adoptionText}>
              {displayName} is designed for reuse across AIS, business process,
              SQL, Excel, audit, and managerial accounting work. Instructors
              can keep one integrated environment and vary the emphasis by
              course, module, or assignment type.
            </p>
            <ul className={styles.list}>
              {adoptionPoints.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <p className={styles.sectionLabel}>Choose Your Next Step</p>
            <h2>Start with the route that matches what you need next.</h2>
          </div>
          <div className={styles.pathGrid}>
            {nextSteps.map((step) => (
              <Link key={step.title} className={styles.pathCard} to={step.href}>
                <strong>{step.title}</strong>
                <span>{step.text}</span>
              </Link>
            ))}
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <p className={styles.sectionLabel}>Common Questions</p>
            <h2>What people usually want to know before they download the dataset.</h2>
          </div>
          <div className={styles.cardGrid}>
            {faqItems.map((item) => (
              <article key={item.question} className={styles.card}>
                <h3>{item.question}</h3>
                <p>{item.answer}</p>
              </article>
            ))}
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.oerBlock}>
            <p className={styles.sectionLabel}>Open Educational Resource</p>
            <p className={styles.oerText}>
              {datasetName} is an openly licensed open educational resource
              designed for reuse, adaptation, and course adoption.
            </p>
            <div className={styles.oerActions}>
              <Link className="button button--primary" to="/docs/">
                Start Here
              </Link>
              <Link className="button button--secondary" to="/docs/process-flows">
                See Process Flows
              </Link>
              <Link className="button button--secondary" to="/docs/teach-with-data/instructor-adoption">
                Adopt in a Course
              </Link>
            </div>
          </div>
        </section>
      </main>
    </Layout>
  );
}
