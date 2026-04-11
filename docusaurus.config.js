const { themes } = require("prism-react-renderer");

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: "Greenfield Accounting Dataset",
  tagline: "Student-first documentation for accounting analytics courses.",
  favicon: "img/favicon.svg",
  url: "https://mmcodesso.github.io",
  baseUrl: "/greenfield_database/",
  organizationName: "mmcodesso",
  projectName: "greenfield_database",
  trailingSlash: false,
  onBrokenLinks: "throw",
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
          editUrl: "https://github.com/mmcodesso/greenfield_database/tree/main/",
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
  themeConfig: {
    image: "img/greenfield-social-card.svg",
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
      title: "Greenfield",
      items: [
        { to: "/docs/", label: "Start Here", position: "left" },
        { to: "/docs/student-quickstart", label: "Students", position: "left" },
        { to: "/docs/analytics", label: "Analytics", position: "left" },
        {
          to: "/docs/teach-with-greenfield/instructor-adoption",
          label: "Adopt",
          position: "left",
        },
        {
          to: "/docs/reference/schema",
          label: "Reference",
          position: "left",
        },
        {
          href: "https://github.com/mmcodesso/greenfield_database",
          label: "GitHub",
          position: "right",
        },
      ],
    },
    footer: {
      style: "dark",
      links: [
        {
          title: "Start Here",
          items: [
            { label: "Documentation Home", to: "/docs/" },
            { label: "Student Quick Start", to: "/docs/student-quickstart" },
            { label: "Dataset Overview", to: "/docs/dataset-overview" },
          ],
        },
        {
          title: "Teaching",
          items: [
            {
              label: "Instructor Adoption Guide",
              to: "/docs/teach-with-greenfield/instructor-adoption",
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
              href: "https://github.com/mmcodesso/greenfield_database",
            },
            {
              label: "Contributing",
              href: "https://github.com/mmcodesso/greenfield_database/blob/main/CONTRIBUTING.md",
            },
            {
              label: "License",
              href: "https://github.com/mmcodesso/greenfield_database/blob/main/LICENSE",
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} Greenfield Accounting Dataset.`,
    },
    prism: {
      theme: themes.github,
      darkTheme: themes.dracula,
      additionalLanguages: ["sql"],
    },
  },
};

module.exports = config;
