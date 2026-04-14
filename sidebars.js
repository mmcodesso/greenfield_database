/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  docsSidebar: [
    {
      type: "category",
      label: "Start Here",
      items: [
        "start-here/index",
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
        "processes/o2c-returns-credits-refunds",
        "processes/p2p",
        "processes/manufacturing",
        "processes/time-clocks",
        "processes/payroll",
        "processes/manual-journals-and-close",
      ],
    },
    {
      type: "category",
      label: "Analyze the Data",
      items: [
        "analytics/index",
        "analytics/financial",
        "analytics/managerial",
        "analytics/audit",
        "analytics/sql-guide",
        "analytics/excel-guide",
        "analytics/cases/index",
        "analytics/cases/o2c-trace-case",
        "analytics/cases/p2p-accrual-settlement-case",
        "analytics/cases/manufacturing-labor-cost-case",
        "analytics/cases/master-data-and-workforce-audit-case",
        "analytics/cases/product-portfolio-and-lifecycle-case",
        "analytics/cases/working-capital-and-cash-conversion-case",
        "analytics/cases/financial-statement-bridge-case",
        "analytics/cases/product-portfolio-profitability-case",
        "analytics/cases/workforce-cost-and-org-control-case",
        "analytics/cases/workforce-coverage-and-attendance-case",
        "analytics/cases/demand-planning-and-replenishment-case",
        "analytics/cases/pricing-and-margin-governance-case",
        "analytics/cases/audit-review-pack-case",
        "analytics/cases/attendance-control-audit-case",
        "analytics/cases/replenishment-support-audit-case",
        "analytics/cases/pricing-governance-audit-case",
        "analytics/cases/audit-exception-lab",
      ],
    },
    {
      type: "category",
      label: "Reference",
      items: ["reference/schema", "reference/posting"],
    },
    {
      type: "category",
      label: "Teach With Greenfield",
      items: ["teach-with-greenfield/instructor-guide"],
    },
    {
      type: "category",
      label: "Technical",
      items: [
        "technical/technical-guide",
        "technical/dataset-delivery",
        "technical/roadmap",
      ],
    },
  ],
};

module.exports = sidebars;
