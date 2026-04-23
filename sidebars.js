const { loadSiteBranding } = require("./config/loadSiteBranding.cjs");

const branding = loadSiteBranding();

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  docsSidebar: [
    {
      type: "category",
      label: "Start Here",
      items: [
        "start-here/index",
        "start-here/why-this-dataset",
        "start-here/downloads",
        "start-here/dataset-overview",
      ],
    },
    {
      type: "category",
      label: "Learn the Business",
      items: [
        "learn-the-business/company-story",
        "learn-the-business/process-flows",
        "processes/o2c",
        "processes/design-services",
        "processes/p2p",
        "processes/manufacturing",
        "processes/payroll",
        "processes/manual-journals-and-close",
      ],
    },
    {
      type: "category",
      label: "Analyze the Data",
      link: { type: "doc", id: "analytics/index" },
      items: [
        "analytics/sql-guide",
        "analytics/excel-guide",
        {
          type: "category",
          label: "Reports",
          link: { type: "doc", id: "analytics/reports/index" },
          collapsed: true,
          items: [
            {
              type: "category",
              label: "Business Perspectives",
              link: { type: "doc", id: "analytics/reports/lens-packs" },
              collapsed: true,
              items: [
                "analytics/reports/executive-overview",
                "analytics/reports/commercial-and-working-capital",
                "analytics/reports/payroll-perspective",
                "analytics/reports/operations-and-risk",
              ],
            },
            {
              type: "category",
              label: "Report Library",
              collapsed: true,
              items: [
                "analytics/reports/financial",
                "analytics/reports/managerial",
                "analytics/reports/audit",
              ],
            },
          ],
        },
        {
          type: "category",
          label: "Cases",
          link: { type: "doc", id: "analytics/cases/index" },
          collapsed: true,
          items: [
            {
              type: "category",
              label: "Core Walkthroughs",
              collapsed: true,
              items: [
                "analytics/cases/o2c-trace-case",
                "analytics/cases/p2p-accrual-settlement-case",
                "analytics/cases/manufacturing-labor-cost-case",
                "analytics/cases/product-portfolio-and-lifecycle-case",
              ],
            },
            {
              type: "category",
              label: "Financial",
              collapsed: true,
              items: [
                "analytics/cases/working-capital-and-cash-conversion-case",
                "analytics/cases/financial-statement-bridge-case",
                "analytics/cases/capex-fixed-asset-lifecycle-case",
                "analytics/cases/pricing-and-margin-governance-case",
              ],
            },
            {
              type: "category",
              label: "Managerial and Planning",
              collapsed: true,
              items: [
                "analytics/cases/product-portfolio-profitability-case",
                "analytics/cases/workforce-coverage-and-attendance-case",
                "analytics/cases/demand-planning-and-replenishment-case",
              ],
            },
            {
              type: "category",
              label: "Audit and Controls",
              collapsed: true,
              items: [
                "analytics/cases/master-data-and-workforce-audit-case",
                "analytics/cases/workforce-cost-and-org-control-case",
                "analytics/cases/audit-review-pack-case",
                "analytics/cases/attendance-control-audit-case",
                "analytics/cases/replenishment-support-audit-case",
                "analytics/cases/pricing-governance-audit-case",
                "analytics/cases/audit-exception-lab",
              ],
            },
          ],
        },
        {
          type: "category",
          label: "Analysis Tracks",
          link: { type: "doc", id: "analytics/analysis-tracks" },
          collapsed: true,
          items: [
            "analytics/analysis-tracks",
            "analytics/financial",
            "analytics/managerial",
            "analytics/audit",
          ],
        },
      ],
    },
    {
      type: "category",
      label: "Reference",
      items: ["reference/schema", "reference/posting"],
    },
    {
      type: "category",
      label: branding.instructorLabel,
      items: ["teach-with-data/instructor-guide"],
    },
    {
      type: "category",
      label: "Technical",
      items: [
        "technical/technical-guide",
        "technical/dataset-delivery",
        "technical/roadmap",
        "technical/contributing",
        "technical/license",
      ],
    },
  ],
};

module.exports = sidebars;
