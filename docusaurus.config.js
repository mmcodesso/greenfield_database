const { themes } = require("prism-react-renderer");

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: "Charles River Accounting Dataset",
  tagline: "Student-first documentation for accounting analytics courses.",
  favicon: "img/favicon.svg",
  url: "https://CharlesRiver.AccountingAnalyticsHub.com",
  baseUrl: "/",
  organizationName: "mmcodesso",
  projectName: "CharlesRiver_database",
  trailingSlash: false,
  onBrokenLinks: "throw",
  staticDirectories: ["static", "queries"],
  i18n: {
    defaultLocale: "en",
    locales: ["en"],
  },
  markdown: {
    mermaid: true,
    hooks: {
      onBrokenMarkdownLinks: "throw",
    },
  },
  themes: ["@docusaurus/theme-mermaid"],
  presets: [
    [
      "classic",
      {
        docs: {
          path: "docs",
          routeBasePath: "docs",
          sidebarPath: require.resolve("./sidebars.js"),
          showLastUpdateAuthor: false,
          showLastUpdateTime: false,
        },
        blog: false,
        theme: {
          customCss: require.resolve("./src/css/custom.css"),
        },
      },
    ],
  ],
  plugins: [
    [
      "@docusaurus/plugin-client-redirects",
      {
        redirects: [
          {
            to: "/docs/",
            from: ["/docs/quick-start"],
          },
        ],
      },
    ],
  ],
  themeConfig: {
    image: "img/CharlesRiver-social-card.svg",
    colorMode: {
      defaultMode: "light",
      disableSwitch: false,
      respectPrefersColorScheme: false,
    },
    mermaid: {
      theme: {
        light: "neutral",
        dark: "forest",
      },
      options: {
        fontFamily: "IBM Plex Sans, Trebuchet MS, sans-serif",
        flowchart: {
          useMaxWidth: true,
          htmlLabels: true,
          curve: "linear",
        },
        sequence: {
          useMaxWidth: true,
        },
      },
    },
    navbar: {
      title: "CharlesRiver",
      items: [
        { to: "/docs/", label: "Start Here", position: "left" },
        { to: "/docs/analytics", label: "Analytics", position: "left" },
        {
          to: "/docs/teach-with-CharlesRiver/instructor-adoption",
          label: "Adopt",
          position: "left",
        },
        {
          to: "/docs/reference/schema",
          label: "Reference",
          position: "left",
        },
      ],
    },
    footer: {
      style: "dark",
      links: [
        {
          title: "Start Here",
          items: [
            { label: "Start Here", to: "/docs/" },
            { label: "Downloads", to: "/docs/downloads" },
            { label: "Dataset Guide", to: "/docs/dataset-overview" },
          ],
        },
        {
          title: "Teaching",
          items: [
            {
              label: "Instructor Adoption Guide",
              to: "/docs/teach-with-CharlesRiver/instructor-adoption",
            },
            { label: "Analytics Hub", to: "/docs/analytics" },
            { label: "Process Flows", to: "/docs/process-flows" },
          ],
        },
        {
          title: "Repository",
          items: [
            {
              label: "GitHub Repository",
              href: "https://github.com/mmcodesso/CharlesRiver_database",
            },
            {
              label: "Contributing",
              to: "/docs/technical/contributing",
            },
            {
              label: "License",
              to: "/docs/technical/license",
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} Charles River Accounting Dataset.`,
    },
    prism: {
      theme: themes.github,
      darkTheme: themes.dracula,
      additionalLanguages: ["sql"],
    },
  },
};

module.exports = config;
