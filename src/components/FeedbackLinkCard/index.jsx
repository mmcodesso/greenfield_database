import clsx from "clsx";
import Link from "@docusaurus/Link";
import useDocusaurusContext from "@docusaurus/useDocusaurusContext";

import styles from "./styles.module.css";

const CARD_CONFIG = {
  error: {
    hrefKey: "issuesChooseUrl",
    eyebrow: "GitHub Issues",
    toneClassName: styles.error,
    buttonClassName: "button--primary",
  },
  recommendation: {
    hrefKey: "recommendationsDiscussionUrl",
    eyebrow: "GitHub Discussions",
    toneClassName: styles.recommendation,
    buttonClassName: "button--secondary",
  },
};

export default function FeedbackLinkCard({
  kind,
  title,
  description,
  ctaLabel,
}) {
  const { siteConfig } = useDocusaurusContext();
  const branding = siteConfig.customFields?.branding ?? {};
  const config = CARD_CONFIG[kind];
  const href = config ? branding[config.hrefKey] : null;

  if (!config || !href) {
    return null;
  }

  return (
    <article className={clsx(styles.card, config.toneClassName)}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>{config.eyebrow}</p>
        <h3>{title}</h3>
      </div>
      <p className={styles.description}>{description}</p>
      <Link
        className={clsx(
          "button button--lg",
          config.buttonClassName,
          styles.button,
        )}
        href={href}
        target="_blank"
        rel="noopener noreferrer"
      >
        {ctaLabel}
      </Link>
    </article>
  );
}
