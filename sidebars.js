/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  docsSidebar: [
    {
      type: "category",
      label: "Start Here",
      items: ["index", "student-quickstart", "downloads", "dataset-overview"],
    },
    {
      type: "category",
      label: "Learn the Business",
      items: [
        "company-story",
        "process-flows",
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
      items: ["instructor-guide"],
    },
    {
      type: "category",
      label: "Technical",
      items: ["technical-guide", "teach-with-greenfield/dataset-delivery", "roadmap"],
    },
  ],
};

module.exports = sidebars;
