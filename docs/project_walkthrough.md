# First-person project walkthrough

Use this after reviewing and running the project. It describes a personal simulation, not an employer engagement.

“I built a repeatable ERP analysis workflow using synthetic Business Central-style vendor, invoice, payment, purchase order and inventory data. I used Python to enforce source schemas and identify duplicate records, missing values and invalid relationships, while retaining an exception log with the original records.

I used SQL to calculate accounts payable aging, supplier on-time performance and item/location inventory balances. I aggregated payments before joining invoices to avoid inflating invoice totals, and I used a reporting cutoff so future payments would not reduce an earlier balance.

I created a browser report, management brief and action queue to make the findings accessible to operational users. I also prepared an Excel Power Query importer and a Power Automate implementation guide. The local workflow runs and is tested; the Microsoft tenant integration remains a deployment step.”

## Interview discussion

- **What was automated?** Local validation, transformation, report generation and routing into a review CSV. Unchanged input is recognized by a content hash.
- **How did you handle defects?** Exact duplicates and invalid records are quarantined. Conflicting duplicates stop the run. Negative stock stays visible because suppressing it would hide a business issue.
- **How did you prevent overcounting?** Payments are aggregated to invoice before joining invoice amounts; inventory and order facts remain separate.
- **How did you measure on-time performance?** On-time received orders divided by all received orders, with open overdue orders reported separately.
- **How would you deploy?** Map complete Business Central extracts, host the worker or register a desktop-flow machine, publish validated outputs, configure review owners and test failure/idempotency behavior.
- **What improvement did you achieve?** A repeatable, tested local workflow. Time savings and production adoption have not been measured.
