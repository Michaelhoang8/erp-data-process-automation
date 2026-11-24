# ERP operational review — 2025-12-31

Synthetic portfolio findings, in CAD.

- Open AP: $871,596.18; overdue positive balances: $868,042.26.
- On-time receipt rate: 40.2%, based on 134 on-time / 333 received orders. Open overdue orders: 27.
- Negative stock positions: 6; source records quarantined: 5.

## Recommendations
1. AP analyst: prioritize unpaid invoices over 90 days past due, verify approvals and resolve disputes before payment. The report does not establish why invoices are unpaid.
2. Procurement: review Example Supplier 03's promised versus received dates and outstanding commitments. Its simulated delays are an intentional scenario assumption, not evidence about a real supplier.
3. Warehouse manager: investigate negative balances using movements and physical counts. Do not use negative stock as a reliable valuation without reconciliation.
4. Data steward: resolve quarantined rows in the source and re-extract. Keep the exception log and compare the new run to the prior run.

## Process improvement proposal
Replace repeated manual imports with a consistent extraction, schema validation, SQL analysis and review queue. Measure baseline minutes per run, rerun effort and exception closure time before estimating savings. No time savings or implementation in a Microsoft tenant have been measured.
