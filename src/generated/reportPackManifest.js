const reportPackManifest = {
  "executive-overview": {
    "slug": "executive-overview",
    "title": "Executive Overview",
    "summary": "Start here when you want a broad company-level view that ties performance, financial position, cash, and working capital into one storyline.",
    "openingParagraphs": [
      "Executive Overview is the management-level entry point into the dataset. It frames the company as a system where profit, liquidity, operating discipline, and working-capital decisions all interact rather than appearing as isolated report lines.",
      "This perspective matters because a strong income statement does not automatically mean the company is financially healthy. Students need to see how revenue, margins, receivables, payables, inventory, and cost control combine to shape the real operating position month by month.",
      "The goal is to build a first-pass narrative before diving into detail. By the end of this perspective, the reader should understand where the business looks stable, where pressure is building, and which area deserves the next focused investigation."
    ],
    "approachGuidance": [
      "Start with performance, then move to position and cash, so the storyline develops from profit to liquidity.",
      "Compare trends across reports instead of reading each report in isolation.",
      "Treat working capital as an explanatory bridge between operating results and cash movement.",
      "Use the sequence to identify the next drill-down rather than trying to solve every question from the overview alone."
    ],
    "coreQuestions": [
      "Which months show the strongest and weakest operating performance?",
      "How closely do revenue growth, net income, and cash generation move together?",
      "Which working-capital buckets appear to explain the biggest month-to-month shifts in liquidity?",
      "Where should management drill down next after reviewing the top-line overview?"
    ],
    "whereToGoNext": [
      {
        "label": "Financial Reports Library",
        "href": "/docs/analytics/reports/financial"
      },
      {
        "label": "Working Capital and Cash Conversion Case",
        "href": "/docs/analytics/cases/working-capital-and-cash-conversion-case"
      },
      {
        "label": "Financial Statement Bridge Case",
        "href": "/docs/analytics/cases/financial-statement-bridge-case"
      }
    ],
    "reports": [
      {
        "reportSlug": "monthly-income-statement",
        "teachingRole": "anchor",
        "whyItMatters": "Use the income statement to establish the operating-performance story before looking at balance-sheet and cash implications.",
        "discussionQuestions": [
          "Which expense or margin lines appear to move most with revenue over time?",
          "When net income changes sharply, which lines are most responsible?",
          "What would management want to explain before presenting these results externally?"
        ],
        "suggestedAnalysis": [
          "Compare gross margin, operating income, and net income by month.",
          "Flag months where expense growth appears to outpace revenue growth.",
          "Note whether profitability appears stable, seasonal, or unusually volatile."
        ],
        "relatedLink": {
          "label": "Financial Statement Bridge Case",
          "href": "/docs/analytics/cases/financial-statement-bridge-case"
        }
      },
      {
        "reportSlug": "monthly-balance-sheet",
        "teachingRole": "anchor",
        "whyItMatters": "Use the balance sheet to connect performance to ending balances in receivables, inventory, payables, equity, and current-year earnings.",
        "discussionQuestions": [
          "Which balance-sheet sections seem to shift most across the modeled range?",
          "Do asset changes appear to be financed by operations, liabilities, or equity?",
          "Which balances would you inspect next if liquidity tightened?"
        ],
        "suggestedAnalysis": [
          "Trace period-end movements in current assets against current liabilities.",
          "Compare retained earnings and current-year earnings to the income statement trend.",
          "Identify balance-sheet accounts that move independently from revenue."
        ],
        "relatedLink": {
          "label": "Financial Statement Bridge Case",
          "href": "/docs/analytics/cases/financial-statement-bridge-case"
        }
      },
      {
        "reportSlug": "monthly-indirect-cash-flow",
        "teachingRole": "anchor",
        "whyItMatters": "Use the cash flow statement to reconcile accounting performance to cash movement and surface the operational timing drivers beneath liquidity.",
        "discussionQuestions": [
          "Which adjustments explain the largest differences between net income and operating cash flow?",
          "Does operating cash flow move consistently with reported profitability?",
          "When cash generation weakens, which bridge lines explain the gap?"
        ],
        "suggestedAnalysis": [
          "Compare net income with net cash from operating activities.",
          "Highlight working-capital adjustments that recur across multiple months.",
          "Note whether investing or financing activity is overshadowing operating cash movement."
        ],
        "relatedLink": {
          "label": "Working Capital and Cash Conversion Case",
          "href": "/docs/analytics/cases/working-capital-and-cash-conversion-case"
        }
      },
      {
        "reportSlug": "monthly-revenue-and-gross-margin",
        "teachingRole": "anchor",
        "whyItMatters": "Use the monthly revenue bridge to isolate the commercial engine before layering on working-capital and statement interpretation.",
        "discussionQuestions": [
          "Which periods show the strongest combination of revenue and margin?",
          "Do returns and discounts appear to move with revenue or against it?",
          "Where would management want a deeper portfolio or customer-level explanation?"
        ],
        "suggestedAnalysis": [
          "Compare revenue, gross margin, discounts, and returns by period.",
          "Flag months where margin behavior does not follow revenue behavior.",
          "Use the result to decide whether a pricing, customer, or portfolio drill-down is needed."
        ],
        "relatedLink": {
          "label": "Pricing and Margin Governance Case",
          "href": "/docs/analytics/cases/pricing-and-margin-governance-case"
        }
      },
      {
        "reportSlug": "monthly-ar-aging-summary",
        "teachingRole": "drill-down",
        "whyItMatters": "Use the AR summary to see whether strong revenue is being converted into collectible receivables or trapped in aging balances.",
        "discussionQuestions": [
          "Which customer segments appear to hold the largest past-due balances?",
          "Does the aging profile look stable or increasingly stressed over time?",
          "Which customers would merit a detailed follow-up?"
        ],
        "suggestedAnalysis": [
          "Compare current versus past-due balances by month-end.",
          "Identify customers with persistent balances in older aging buckets.",
          "Use the summary to decide where invoice-level review is needed."
        ],
        "relatedLink": {
          "label": "Working Capital and Cash Conversion Case",
          "href": "/docs/analytics/cases/working-capital-and-cash-conversion-case"
        }
      },
      {
        "reportSlug": "monthly-ap-aging-summary",
        "teachingRole": "drill-down",
        "whyItMatters": "Use the AP summary to understand whether supplier obligations are manageable or becoming a source of cash pressure.",
        "discussionQuestions": [
          "Which supplier groups carry the largest open balances?",
          "Does the aging profile suggest normal payment timing or growing strain?",
          "How might AP behavior interact with cash flow and inventory availability?"
        ],
        "suggestedAnalysis": [
          "Compare current versus past-due AP by month-end.",
          "Highlight suppliers with large balances and high-risk ratings.",
          "Relate AP aging changes to operating cash flow and working-capital movement."
        ],
        "relatedLink": {
          "label": "Working Capital and Cash Conversion Case",
          "href": "/docs/analytics/cases/working-capital-and-cash-conversion-case"
        }
      },
      {
        "reportSlug": "budget-vs-actual-by-cost-center",
        "teachingRole": "drill-down",
        "whyItMatters": "Use budget versus actual to add a managerial-control view to the executive pack and show where spending discipline is strongest or weakest.",
        "discussionQuestions": [
          "Which cost centers appear most consistently over or under budget?",
          "Do budget variances align with observed revenue or operating changes?",
          "Which variances look structural rather than one-time?"
        ],
        "suggestedAnalysis": [
          "Compare spending variance patterns by month and cost center.",
          "Distinguish recurring unfavorable variances from isolated months.",
          "Link cost-center variance to the profitability story from the income statement."
        ],
        "relatedLink": null
      },
      {
        "reportSlug": "working-capital-bridge-by-month",
        "teachingRole": "drill-down",
        "whyItMatters": "Use the working-capital bridge to identify which balance-sheet buckets are driving liquidity changes instead of treating working capital as one unexplained total.",
        "discussionQuestions": [
          "Which working-capital bucket contributes the most to month-to-month movement?",
          "Do AR, inventory, AP, and deposits appear to move together or independently?",
          "Which bucket would management monitor most closely?"
        ],
        "suggestedAnalysis": [
          "Compare month-over-month changes in AR, inventory, AP, GRNI, deposits, and accruals.",
          "Tie large movements back to the balance sheet and cash flow statement.",
          "Use the bridge to define the next focused working-capital analysis."
        ],
        "relatedLink": {
          "label": "Working Capital and Cash Conversion Case",
          "href": "/docs/analytics/cases/working-capital-and-cash-conversion-case"
        }
      }
    ]
  },
  "commercial-and-working-capital": {
    "slug": "commercial-and-working-capital",
    "title": "Commercial and Working Capital",
    "summary": "Use this pack to connect revenue quality, customer behavior, pricing, and settlement timing to working-capital outcomes.",
    "openingParagraphs": [
      "Commercial and Working Capital focuses on the quality of revenue rather than revenue volume alone. It asks whether customer mix, pricing discipline, credits, collections, and supplier obligations are helping the business convert sales activity into healthy cash outcomes.",
      "This perspective matters because commercial decisions shape more than the top line. Discounting, refunds, delayed collections, unapplied cash, and uneven supplier-payment timing can all weaken the company even when reported sales look strong.",
      "The reader should approach this perspective as a bridge between sales behavior and liquidity. The sequence is designed to show how customer-level and supplier-level patterns move through pricing, settlement, receivables, payables, and ultimately cash conversion."
    ],
    "approachGuidance": [
      "Start by understanding revenue quality before jumping into receivables and payables aging.",
      "Compare customer-side and supplier-side timing to see how working-capital pressure builds on both sides of the business.",
      "Treat pricing, credits, and unapplied cash as indicators of process quality, not just isolated exceptions.",
      "Use summary reports first, then move into detail only where balances or timing patterns remain unclear."
    ],
    "coreQuestions": [
      "Which customers, regions, or segments appear most commercially important?",
      "Where do pricing pressure, returns, credits, or unapplied cash change the quality of reported revenue?",
      "Which working-capital signals suggest collection or supplier-payment pressure?",
      "How does commercial activity translate into settlement timing and cash conversion?"
    ],
    "whereToGoNext": [
      {
        "label": "Financial Reports Library",
        "href": "/docs/analytics/reports/financial"
      },
      {
        "label": "Managerial Reports Library",
        "href": "/docs/analytics/reports/managerial"
      },
      {
        "label": "Working Capital and Cash Conversion Case",
        "href": "/docs/analytics/cases/working-capital-and-cash-conversion-case"
      },
      {
        "label": "Pricing and Margin Governance Case",
        "href": "/docs/analytics/cases/pricing-and-margin-governance-case"
      }
    ],
    "reports": [
      {
        "reportSlug": "monthly-revenue-and-gross-margin",
        "teachingRole": "anchor",
        "whyItMatters": "Start with the monthly revenue bridge to establish the high-level commercial result before moving into customer, pricing, and settlement detail.",
        "discussionQuestions": [
          "Which periods show strong revenue but weaker-than-expected margin quality?",
          "Do discounts and returns appear concentrated or broadly spread?",
          "What commercial questions does this summary leave unanswered?"
        ],
        "suggestedAnalysis": [
          "Compare revenue, gross margin, discount, and return behavior across months.",
          "Identify months that warrant a customer-level or pricing-level drill-down.",
          "Use the report to frame the rest of the commercial pack."
        ],
        "relatedLink": {
          "label": "Pricing and Margin Governance Case",
          "href": "/docs/analytics/cases/pricing-and-margin-governance-case"
        }
      },
      {
        "reportSlug": "customer-sales-mix-by-region-and-item-group",
        "teachingRole": "anchor",
        "whyItMatters": "Use the customer sales mix report to see where revenue is concentrated by geography, customer type, and product family.",
        "discussionQuestions": [
          "Which regions and customer segments drive the largest share of billed sales?",
          "Does the product mix differ materially by customer segment?",
          "Where might revenue concentration create commercial risk?"
        ],
        "suggestedAnalysis": [
          "Rank customer-region combinations by revenue and billed quantity.",
          "Compare item-group mix across segments and geographies.",
          "Look for evidence of dependence on a narrow customer or product slice."
        ],
        "relatedLink": null
      },
      {
        "reportSlug": "price-realization-vs-list-by-customer-and-portfolio",
        "teachingRole": "drill-down",
        "whyItMatters": "Use price realization to separate headline revenue from realized commercial discipline and pricing leakage.",
        "discussionQuestions": [
          "Which customers or portfolio groups realize the lowest percentage of list price?",
          "Does price realization differ more by customer segment or by product portfolio?",
          "Where would management want to inspect promotions or overrides?"
        ],
        "suggestedAnalysis": [
          "Compare base list revenue to net revenue by customer and portfolio group.",
          "Highlight low price-realization pockets that still carry high revenue.",
          "Use the report to decide whether discounting looks strategic or uncontrolled."
        ],
        "relatedLink": {
          "label": "Pricing and Margin Governance Case",
          "href": "/docs/analytics/cases/pricing-and-margin-governance-case"
        }
      },
      {
        "reportSlug": "customer-credit-and-refunds",
        "teachingRole": "drill-down",
        "whyItMatters": "Use customer credit and refund activity to identify where post-sale corrections or overpayments turn into open customer-credit balances.",
        "discussionQuestions": [
          "Which credit memos create customer credit instead of simply reducing AR?",
          "Are credits being refunded quickly or left open?",
          "What might open customer credit suggest about sales quality or settlement control?"
        ],
        "suggestedAnalysis": [
          "Compare credit memo amount, customer credit created, and refunded amount.",
          "Flag open customer-credit balances that remain unresolved.",
          "Relate credit behavior to returns, customer service, or pricing issues."
        ],
        "relatedLink": null
      },
      {
        "reportSlug": "customer-deposits-and-unapplied-cash-aging",
        "teachingRole": "drill-down",
        "whyItMatters": "Use unapplied cash aging to show that cash received is not the same as receivables settled, which makes it a strong teaching bridge between sales and working capital.",
        "discussionQuestions": [
          "How much cash remains unapplied after receipt?",
          "Which receipts stayed open the longest before application?",
          "What control or process issues could create persistent unapplied cash?"
        ],
        "suggestedAnalysis": [
          "Compare receipt amount, applied amount, and open unapplied balance.",
          "Focus on receipts with long delays before first application.",
          "Connect unapplied cash behavior to the working-capital story."
        ],
        "relatedLink": {
          "label": "Working Capital and Cash Conversion Case",
          "href": "/docs/analytics/cases/working-capital-and-cash-conversion-case"
        }
      },
      {
        "reportSlug": "monthly-ar-aging-summary",
        "teachingRole": "anchor",
        "whyItMatters": "Use the AR summary to see whether billed revenue is translating into timely collections at the customer level.",
        "discussionQuestions": [
          "Which customer groups hold the most open and past-due receivables?",
          "Does the aging mix suggest stable collections or growing stress?",
          "Where would management need invoice-level detail next?"
        ],
        "suggestedAnalysis": [
          "Compare current and past-due balances by customer segment over time.",
          "Focus on customers with persistent balances in older buckets.",
          "Use the summary to target a detailed AR review."
        ],
        "relatedLink": {
          "label": "Working Capital and Cash Conversion Case",
          "href": "/docs/analytics/cases/working-capital-and-cash-conversion-case"
        }
      },
      {
        "reportSlug": "monthly-ar-aging-detail",
        "teachingRole": "drill-down",
        "whyItMatters": "Use the invoice-level AR detail to inspect the exact documents driving the summary aging pattern.",
        "discussionQuestions": [
          "Which invoices remain open across multiple month-ends?",
          "Where do due-date timing and settlement behavior diverge most sharply?",
          "Which customers appear to have the oldest invoice-level pressure?"
        ],
        "suggestedAnalysis": [
          "Trace recurring invoice numbers across month-end snapshots.",
          "Isolate invoices that move slowly through the aging buckets.",
          "Compare cash applied and credit memo applied against the remaining open balance."
        ],
        "relatedLink": null
      },
      {
        "reportSlug": "monthly-ap-aging-summary",
        "teachingRole": "drill-down",
        "whyItMatters": "Use the AP summary to compare commercial growth and collections against the company's cash obligations to suppliers.",
        "discussionQuestions": [
          "Which supplier groups carry the largest open balances?",
          "Does AP aging suggest deliberate working-capital management or payment strain?",
          "How should AP behavior be interpreted alongside AR?"
        ],
        "suggestedAnalysis": [
          "Compare AP aging concentration by supplier and category.",
          "Contrast payables behavior with receivables behavior across month-ends.",
          "Use the summary to frame supplier-level follow-up questions."
        ],
        "relatedLink": {
          "label": "Working Capital and Cash Conversion Case",
          "href": "/docs/analytics/cases/working-capital-and-cash-conversion-case"
        }
      },
      {
        "reportSlug": "monthly-ap-aging-detail",
        "teachingRole": "drill-down",
        "whyItMatters": "Use the invoice-level AP detail to see which supplier documents are driving the month-end obligation profile.",
        "discussionQuestions": [
          "Which supplier invoices remain open across multiple month-ends?",
          "Where do payment timing and due-date timing diverge most clearly?",
          "Which supplier relationships would management watch most closely?"
        ],
        "suggestedAnalysis": [
          "Trace recurring invoice numbers across month-end snapshots.",
          "Compare open balances to supplier category and risk rating.",
          "Identify invoices that stay unresolved long after their due date."
        ],
        "relatedLink": null
      },
      {
        "reportSlug": "supplier-purchasing-activity-by-category",
        "teachingRole": "drill-down",
        "whyItMatters": "Use supplier purchasing activity to connect the payables story back to sourcing volume, supplier mix, and category exposure.",
        "discussionQuestions": [
          "Which supplier categories dominate committed purchasing volume?",
          "Does supplier spend appear diversified or concentrated?",
          "How might purchasing mix influence AP and inventory risk?"
        ],
        "suggestedAnalysis": [
          "Compare ordered value by supplier, category, and item group.",
          "Note high-value suppliers that also carry large AP exposure.",
          "Use the result to set up supplier-risk discussion."
        ],
        "relatedLink": null
      },
      {
        "reportSlug": "cash-conversion-timing-review",
        "teachingRole": "anchor",
        "whyItMatters": "Use the timing review to link commercial activity and procurement activity to the actual pace of settlement.",
        "discussionQuestions": [
          "Which document family takes the longest to reach first settlement?",
          "Are settlement delays concentrated in AR, AP, or goods-receipt timing?",
          "What does this imply about operational cash conversion?"
        ],
        "suggestedAnalysis": [
          "Compare average days to first settlement across the three metric families.",
          "Identify months with elevated open-document counts.",
          "Use the timing view to explain changes in working capital and cash flow."
        ],
        "relatedLink": {
          "label": "Working Capital and Cash Conversion Case",
          "href": "/docs/analytics/cases/working-capital-and-cash-conversion-case"
        }
      }
    ]
  },
  "operations-and-risk": {
    "slug": "operations-and-risk",
    "title": "Operations and Risk",
    "summary": "Use this pack to connect planning, supply reliability, capacity, workforce structure, and control signals into one operational-risk storyline.",
    "openingParagraphs": [
      "Operations and Risk frames the company as an execution system. It asks whether demand, supply, capacity, workforce structure, and controls are aligned well enough for the business to deliver reliably without creating hidden operational or financial stress.",
      "This perspective matters because operational problems often surface before they appear clearly in financial statements. Supplier delays, weak inventory coverage, overcommitted work centers, unstable forecasts, and control exceptions can all signal future pressure on service, margin, and risk.",
      "The purpose of this perspective is to help readers connect operational indicators with governance signals. Rather than treating planning, staffing, and controls as separate topics, the report sequence shows how they reinforce one another inside the same operating environment."
    ],
    "approachGuidance": [
      "Read the sequence as an operating narrative that moves from capacity pressure into supply reliability, planning quality, and control signals.",
      "Compare operational strain indicators across reports instead of treating each one as a separate exception list.",
      "Use forecast, inventory, and capacity reports together to understand whether pressure is structural or temporary.",
      "Treat control findings as part of operational risk, not as a standalone audit topic."
    ],
    "coreQuestions": [
      "Which operational constraints appear most likely to disrupt service or margin?",
      "Where do supplier reliability, inventory coverage, and capacity pressure reinforce one another?",
      "What workforce or control signals should management monitor alongside operational metrics?",
      "Which risks deserve detailed audit-style follow-up?"
    ],
    "whereToGoNext": [
      {
        "label": "Managerial Reports Library",
        "href": "/docs/analytics/reports/managerial"
      },
      {
        "label": "Audit Reports Library",
        "href": "/docs/analytics/reports/audit"
      },
      {
        "label": "Demand Planning and Replenishment Case",
        "href": "/docs/analytics/cases/demand-planning-and-replenishment-case"
      },
      {
        "label": "Audit Review Pack Case",
        "href": "/docs/analytics/cases/audit-review-pack-case"
      }
    ],
    "reports": [
      {
        "reportSlug": "monthly-work-center-utilization",
        "teachingRole": "anchor",
        "whyItMatters": "Start with utilization to see where the operating model is running near capacity before moving into planning and risk details.",
        "discussionQuestions": [
          "Which months show the highest capacity pressure?",
          "Does utilization look stable, seasonal, or consistently tight?",
          "Which work centers would you want to investigate next?"
        ],
        "suggestedAnalysis": [
          "Compare utilization trends by month and work center.",
          "Highlight periods that appear persistently near capacity.",
          "Use the result to frame the need for capacity planning detail."
        ],
        "relatedLink": {
          "label": "Demand Planning and Replenishment Case",
          "href": "/docs/analytics/cases/demand-planning-and-replenishment-case"
        }
      },
      {
        "reportSlug": "rough-cut-capacity-load-vs-available-hours",
        "teachingRole": "drill-down",
        "whyItMatters": "Use the rough-cut plan to inspect the week-level load behind utilization pressure and identify where capacity is overtly overcommitted.",
        "discussionQuestions": [
          "Which weeks or work centers are over capacity versus merely tight?",
          "Is planned load concentrated in a small number of work centers?",
          "How might over-capacity weeks affect service and labor decisions?"
        ],
        "suggestedAnalysis": [
          "Compare planned load, available hours, and utilization percentage by week.",
          "Flag work centers repeatedly labeled over capacity.",
          "Tie weekly planning pressure back to monthly utilization."
        ],
        "relatedLink": {
          "label": "Demand Planning and Replenishment Case",
          "href": "/docs/analytics/cases/demand-planning-and-replenishment-case"
        }
      },
      {
        "reportSlug": "supplier-lead-time-and-receipt-reliability",
        "teachingRole": "anchor",
        "whyItMatters": "Use supplier lead-time performance to see whether inbound reliability is supporting or undermining the production and fulfillment plan.",
        "discussionQuestions": [
          "Which suppliers are slowest to first receipt or full receipt?",
          "Where do partial receipts or no receipts appear most often?",
          "How might unreliable receipts affect inventory and capacity pressure?"
        ],
        "suggestedAnalysis": [
          "Compare average days to first and full receipt by supplier.",
          "Focus on suppliers with repeated partial or missing receipt patterns.",
          "Relate receipt reliability to inventory and planning risk."
        ],
        "relatedLink": {
          "label": "Demand Planning and Replenishment Case",
          "href": "/docs/analytics/cases/demand-planning-and-replenishment-case"
        }
      },
      {
        "reportSlug": "inventory-coverage-and-projected-stockout-risk",
        "teachingRole": "anchor",
        "whyItMatters": "Use projected coverage and stockout risk to identify where the current planning state may be inadequate for demand.",
        "discussionQuestions": [
          "Which items or warehouses show the most urgent stockout-risk signals?",
          "Does low projected availability cluster by collection, style family, or warehouse?",
          "How should management distinguish normal replenishment from true risk?"
        ],
        "suggestedAnalysis": [
          "Compare weeks of coverage against risk labels.",
          "Focus on expedite-priority items and negative projected availability.",
          "Relate coverage problems to forecast and supplier behavior."
        ],
        "relatedLink": {
          "label": "Demand Planning and Replenishment Case",
          "href": "/docs/analytics/cases/demand-planning-and-replenishment-case"
        }
      },
      {
        "reportSlug": "forecast-error-and-bias-by-collection-and-style-family",
        "teachingRole": "drill-down",
        "whyItMatters": "Use forecast bias to see where planning error is systematic rather than random, which makes it a strong learning bridge between commercial demand and operations.",
        "discussionQuestions": [
          "Which collections or style families appear most over-forecasted or under-forecasted?",
          "Does forecast bias seem concentrated in a small part of the portfolio?",
          "How could forecast bias feed directly into stockout or capacity risk?"
        ],
        "suggestedAnalysis": [
          "Compare forecast quantity, actual order quantity, bias, and absolute error.",
          "Focus on portfolio groups with the largest absolute error.",
          "Relate forecast misses to coverage or expedite pressure."
        ],
        "relatedLink": {
          "label": "Demand Planning and Replenishment Case",
          "href": "/docs/analytics/cases/demand-planning-and-replenishment-case"
        }
      },
      {
        "reportSlug": "headcount-by-cost-center-and-job-family",
        "teachingRole": "drill-down",
        "whyItMatters": "Use workforce structure to add organizational context to the operational plan and show where capability or staffing concentration may matter.",
        "discussionQuestions": [
          "Which cost centers and job families carry the largest share of headcount?",
          "Does the workforce mix align with the operating pressure shown elsewhere in the pack?",
          "Where might management worry about staffing imbalance or concentration?"
        ],
        "suggestedAnalysis": [
          "Compare headcount concentration across cost centers and job families.",
          "Look for structural differences between support and operating functions.",
          "Use the result to frame workforce-risk follow-up questions."
        ],
        "relatedLink": null
      },
      {
        "reportSlug": "approval-and-sod-review",
        "teachingRole": "anchor",
        "whyItMatters": "Use the SOD review to show that operational performance should be evaluated together with control design, not separately from it.",
        "discussionQuestions": [
          "Which approval or same-user conflicts appear most concerning?",
          "Are control issues concentrated in particular processes?",
          "How might these conflicts create operational or financial risk?"
        ],
        "suggestedAnalysis": [
          "Group findings by source-document process area.",
          "Highlight recurring approval-role conflicts.",
          "Use the result to decide whether deeper audit review is needed."
        ],
        "relatedLink": {
          "label": "Audit Review Pack Case",
          "href": "/docs/analytics/cases/audit-review-pack-case"
        }
      },
      {
        "reportSlug": "potential-anomaly-review",
        "teachingRole": "drill-down",
        "whyItMatters": "Use the anomaly review as a broad risk screen that can point students toward the specific operating or control areas most worth investigating.",
        "discussionQuestions": [
          "Which anomaly families appear most meaningful operationally?",
          "Are the exceptions isolated or repeated across processes?",
          "Which anomalies would you escalate first and why?"
        ],
        "suggestedAnalysis": [
          "Group anomalies by process area and exception type.",
          "Compare operational exceptions with the supply and capacity reports in this pack.",
          "Use the broad screen to define one focused audit follow-up."
        ],
        "relatedLink": {
          "label": "Audit Review Pack Case",
          "href": "/docs/analytics/cases/audit-review-pack-case"
        }
      }
    ]
  },
  "payroll-perspective": {
    "slug": "payroll-perspective",
    "title": "Payroll and Workforce",
    "summary": "Use this perspective to connect people cost, payroll calculation, cash movement, time support, and payroll-control risk into one guided storyline.",
    "openingParagraphs": [
      "Payroll and Workforce treats payroll as more than a routine back-office process. It is one of the clearest places where workforce structure, operating time, accounting, cash movement, and control discipline all meet in the same monthly cycle.",
      "This perspective matters because payroll can look stable on the surface while still hiding meaningful issues underneath. Students need to see where people cost sits, how gross pay turns into net pay, how liabilities clear through payments and remittances, and whether approved time actually supports what was paid.",
      "The goal is to help readers move from payroll as an expense line to payroll as a business process. By the end of this sequence, the reader should understand whether payroll looks operationally supported, financially well explained, and controlled strongly enough to trust."
    ],
    "approachGuidance": [
      "Start with payroll cost concentration before moving into register-level calculation detail.",
      "Read gross-to-net, cash outflow, and liability reports together so payroll is interpreted as a full accounting cycle rather than a single payment event.",
      "Compare time support and pay support separately, because approved hours, labor allocation, and payroll earnings do not answer the same question.",
      "Use the control reports at the end of the sequence to test whether the cost and process story is reliable enough to trust."
    ],
    "coreQuestions": [
      "Where does payroll cost concentrate by cost center, job family, and pay class?",
      "How does gross pay become net pay, and which burdens remain company cost rather than employee reduction?",
      "Do payroll cash payments and liability remittances align with the liability and timing story?",
      "Does approved time support what hourly employees were paid?",
      "Which payroll and timekeeping patterns deserve control-oriented follow-up?"
    ],
    "whereToGoNext": [
      {
        "label": "Financial Reports Library",
        "href": "/docs/analytics/reports/financial"
      },
      {
        "label": "Managerial Reports Library",
        "href": "/docs/analytics/reports/managerial"
      },
      {
        "label": "Audit Reports Library",
        "href": "/docs/analytics/reports/audit"
      },
      {
        "label": "Workforce Cost and Org-Control Case",
        "href": "/docs/analytics/cases/workforce-cost-and-org-control-case"
      },
      {
        "label": "Workforce Coverage and Attendance Case",
        "href": "/docs/analytics/cases/workforce-coverage-and-attendance-case"
      },
      {
        "label": "Attendance Control Audit Case",
        "href": "/docs/analytics/cases/attendance-control-audit-case"
      },
      {
        "label": "Working Capital and Cash Conversion Case",
        "href": "/docs/analytics/cases/working-capital-and-cash-conversion-case"
      }
    ],
    "reports": [
      {
        "reportSlug": "payroll-expense-mix-by-cost-center-and-pay-class",
        "teachingRole": "anchor",
        "whyItMatters": "Start with payroll expense mix to identify where people cost sits before moving into payroll mechanics and control interpretation.",
        "discussionQuestions": [
          "Which cost centers and pay classes carry the largest payroll totals?",
          "Does payroll mix appear concentrated in a small part of the organization?",
          "What would management want to explain about the current payroll profile?"
        ],
        "suggestedAnalysis": [
          "Compare gross pay, net pay, and employer burden across cost centers and pay classes.",
          "Highlight areas where employee count and payroll cost do not move together cleanly.",
          "Use the result to decide which workforce group deserves deeper follow-up."
        ],
        "relatedLink": null
      },
      {
        "reportSlug": "gross-to-net-payroll-review",
        "teachingRole": "anchor",
        "whyItMatters": "Use the register-level gross-to-net bridge to explain payroll calculation clearly before turning to cash movement or exception review.",
        "discussionQuestions": [
          "Which employees or cost centers show the largest gross-to-net spread?",
          "How much of the payroll picture sits in employee withholdings versus employer burden?",
          "Which status or approval patterns would merit additional review?"
        ],
        "suggestedAnalysis": [
          "Compare gross pay, employee withholdings, employer burden, and net pay by period.",
          "Distinguish employee deductions from company-side payroll cost.",
          "Use the result to frame the later cash and liability discussion."
        ],
        "relatedLink": {
          "label": "Workforce Cost and Org-Control Case",
          "href": "/docs/analytics/cases/workforce-cost-and-org-control-case"
        }
      },
      {
        "reportSlug": "punch-to-pay-bridge-for-hourly-workers",
        "teachingRole": "anchor",
        "whyItMatters": "Use the punch-to-pay bridge to connect raw workforce activity to approved hours, labor allocation, and hourly payroll outcome.",
        "discussionQuestions": [
          "How closely do punch counts, approved hours, labor hours, and pay align?",
          "Which hourly employees or periods appear hardest to explain?",
          "Where would you expect follow-up between attendance review and payroll review?"
        ],
        "suggestedAnalysis": [
          "Compare punch count, approved clock hours, labor hours, and pay by employee and payroll period.",
          "Flag cases where labor support or pay appears disproportionate to approved time.",
          "Use the bridge to identify whether a payroll issue looks operational, accounting, or control-related."
        ],
        "relatedLink": {
          "label": "Workforce Coverage and Attendance Case",
          "href": "/docs/analytics/cases/workforce-coverage-and-attendance-case"
        }
      },
      {
        "reportSlug": "payroll-and-people-cost-mix-by-cost-center-job-family-level",
        "teachingRole": "drill-down",
        "whyItMatters": "Use the people-cost mix report to compare payroll concentration to the shape of the workforce rather than reading payroll totals in isolation.",
        "discussionQuestions": [
          "Which job families or levels drive the most people cost within each cost center?",
          "Where do headcount concentration and payroll concentration diverge?",
          "Which workforce group would management scrutinize next?"
        ],
        "suggestedAnalysis": [
          "Compare end-state headcount to employees with payroll by workforce grouping.",
          "Highlight groups with high total people cost but relatively small headcount.",
          "Use the output to frame organizational and pay-mix questions."
        ],
        "relatedLink": {
          "label": "Workforce Cost and Org-Control Case",
          "href": "/docs/analytics/cases/workforce-cost-and-org-control-case"
        }
      },
      {
        "reportSlug": "payroll-cash-payments-and-remittances",
        "teachingRole": "drill-down",
        "whyItMatters": "Use payroll cash outflow detail to separate employee payments from liability remittances and explain how payroll reaches the cash ledger.",
        "discussionQuestions": [
          "Do employee payments and remittances move in the same periods or with visible lag?",
          "Which month shows the highest total payroll cash outflow?",
          "How should management interpret remittance timing versus payroll register timing?"
        ],
        "suggestedAnalysis": [
          "Compare net-pay cash to tax and benefits remittances by fiscal period.",
          "Identify periods where remittance mix changes meaningfully.",
          "Relate cash outflow timing back to liability movement."
        ],
        "relatedLink": {
          "label": "Working Capital and Cash Conversion Case",
          "href": "/docs/analytics/cases/working-capital-and-cash-conversion-case"
        }
      },
      {
        "reportSlug": "payroll-liability-rollforward",
        "teachingRole": "drill-down",
        "whyItMatters": "Use the liability rollforward to show whether payroll obligations accumulate and clear in a pattern that makes accounting and cash sense.",
        "discussionQuestions": [
          "Which payroll-liability accounts carry the largest ending balances?",
          "Do liabilities appear to clear regularly or build up over time?",
          "Which liability type would management or audit monitor most closely?"
        ],
        "suggestedAnalysis": [
          "Compare debit, credit, net increase, and ending balance by account and period.",
          "Highlight accounts with recurring positive buildup.",
          "Read the rollforward together with payroll cash remittances."
        ],
        "relatedLink": {
          "label": "Working Capital and Cash Conversion Case",
          "href": "/docs/analytics/cases/working-capital-and-cash-conversion-case"
        }
      },
      {
        "reportSlug": "labor-and-headcount-by-work-location-job-family-cost-center",
        "teachingRole": "drill-down",
        "whyItMatters": "Use this report to connect payroll totals back to workforce structure, approved time, and direct labor usage across the organization.",
        "discussionQuestions": [
          "Which locations or job families combine high people cost with high approved or direct labor hours?",
          "Where does workforce structure appear operationally heavy or light?",
          "Which organizational slice looks most important for deeper payroll analysis?"
        ],
        "suggestedAnalysis": [
          "Compare headcount, gross pay, approved hours, and direct labor hours by grouping.",
          "Look for groupings where total people cost is high but direct labor support is low.",
          "Use the result to connect payroll interpretation to operating structure."
        ],
        "relatedLink": {
          "label": "Workforce Cost and Org-Control Case",
          "href": "/docs/analytics/cases/workforce-cost-and-org-control-case"
        }
      },
      {
        "reportSlug": "overtime-approval-coverage-and-concentration",
        "teachingRole": "drill-down",
        "whyItMatters": "Use overtime approval coverage to show where payroll pressure may be operationally justified versus weakly governed.",
        "discussionQuestions": [
          "Which work centers carry the most overtime?",
          "Where do overtime hours and missing approvals appear together?",
          "Does overtime look concentrated in a few operational hotspots?"
        ],
        "suggestedAnalysis": [
          "Compare overtime totals, approval coverage, and missing approval counts by month and work center.",
          "Identify recurring work centers with meaningful overtime and weak approval coverage.",
          "Use the result to connect staffing pressure to control follow-up."
        ],
        "relatedLink": {
          "label": "Workforce Coverage and Attendance Case",
          "href": "/docs/analytics/cases/workforce-coverage-and-attendance-case"
        }
      },
      {
        "reportSlug": "absence-rate-by-work-location-job-family-month",
        "teachingRole": "drill-down",
        "whyItMatters": "Use absence rate to add workforce-availability context before treating overtime or payroll-support issues as purely administrative problems.",
        "discussionQuestions": [
          "Which work locations or job families show the highest absence pressure?",
          "Does paid versus unpaid absence change the interpretation?",
          "How might absence patterns explain overtime or payroll irregularities elsewhere?"
        ],
        "suggestedAnalysis": [
          "Compare absence rate, hours absent, and paid versus unpaid absence by month.",
          "Focus on workforce groups with persistent absence pressure.",
          "Relate absence trends to overtime or hourly pay support questions."
        ],
        "relatedLink": {
          "label": "Workforce Coverage and Attendance Case",
          "href": "/docs/analytics/cases/workforce-coverage-and-attendance-case"
        }
      },
      {
        "reportSlug": "payroll-control-review",
        "teachingRole": "drill-down",
        "whyItMatters": "Use the payroll control review to test whether the payroll cycle has basic approval, payment-timing, and register-quality discipline.",
        "discussionQuestions": [
          "Which payroll-control issue types appear most frequently?",
          "Which exception would create the greatest trust problem in payroll reporting?",
          "What would you inspect next for a flagged employee or pay period?"
        ],
        "suggestedAnalysis": [
          "Group findings by issue type and payroll period.",
          "Compare exception timing to the gross-to-net and cash reports.",
          "Use the result to prioritize control follow-up."
        ],
        "relatedLink": {
          "label": "Attendance Control Audit Case",
          "href": "/docs/analytics/cases/attendance-control-audit-case"
        }
      },
      {
        "reportSlug": "paid-without-clock-and-clock-without-pay-review",
        "teachingRole": "drill-down",
        "whyItMatters": "Use this exception review to test the most important support bridge in hourly payroll: approved work should flow to pay, and pay should have approved work behind it.",
        "discussionQuestions": [
          "Which exception direction appears more operationally serious in this dataset?",
          "Are the exceptions isolated to a few employees or spread across periods?",
          "What source-table evidence would you trace next?"
        ],
        "suggestedAnalysis": [
          "Separate paid-without-clock findings from clock-without-pay findings.",
          "Compare affected periods to the punch-to-pay bridge and overtime coverage.",
          "Use the result to define a focused attendance or payroll audit follow-up."
        ],
        "relatedLink": {
          "label": "Attendance Control Audit Case",
          "href": "/docs/analytics/cases/attendance-control-audit-case"
        }
      }
    ]
  }
};

export default reportPackManifest;
