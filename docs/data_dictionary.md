# Data dictionary and Business Central mapping

All source data is synthetic. These are simplified ERP-style extracts, not exact Business Central API response schemas. One fictional company, CAD only, snapshot cutoff 2025-12-31. Dates are ISO YYYY-MM-DD. Financial values use integer cents, not formatted strings.

| CSV | Grain | Fields |
|---|---|---|
| vendors | VendorID | VendorID, VendorName, PaymentTermsDays |
| items | ItemID | ItemID, Description, UnitCostCents, ReorderPoint |
| invoices | InvoiceID | InvoiceID, VendorID, PostingDate, DueDate, AmountCents |
| payments | PaymentID | PaymentID, InvoiceID, PaymentDate, AmountCents |
| purchase_orders | OrderID | OrderID, VendorID, ItemID, OrderDate, PromisedDate, ReceivedDate, Quantity |
| inventory_movements | MovementID | MovementID, ItemID, Location, PostingDate, Quantity, MovementType |

InvoiceID is unique across this fictional company. Real deployments must use stable record IDs and a company key. Payments are applied amounts to individual invoices, not unallocated bank payments. Multiple payments per invoice are allowed; negative balances are exposed for review. No credit memos, FX, VAT or payment reversals are simulated.

Purchase orders are one item per order, with complete receipt date or blank. A real line-level, partially received order model must separate order headers, lines and receipt events. ReceivedDate blank means unreceived as of the extract. The on-time denominator includes only orders received by cutoff; open overdue orders are a separate measure.

Movement types: Opening and Receipt positive; Issue negative; Adjustment may be either sign. OnHand sums movements through cutoff for item/location. Valuation uses current synthetic standard cost, not historical costing layers. ReorderPoint applies independently to each location; no demand forecast, lead-time policy or reservation quantity is modeled. Negative stock stays in calculations and is flagged rather than silently clamped.

## Potential production sources requiring mapping

- Vendors and items: standard Business Central master resources.
- Invoices: posted purchase invoice data, retaining posting and due dates and stable IDs.
- Payments: vendor ledger application detail mapped to each invoice with an effective application date. Do not infer historical applied payments from current remaining balance alone.
- Purchase orders: order lines plus posted receipt history, mapped to an agreed order/line grain.
- Inventory movements: item ledger history and opening balances; avoid counting an opening balance plus earlier movements twice.

Not every required field or ledger application relationship is guaranteed to be exposed by the standard API. Evaluate available APIs or approved custom APIs in the target tenant. This project contains no live extraction connector.

## Validation policy

Exact duplicate business keys are quarantined. Conflicting duplicates stop publication. Required blanks, malformed dates, unknown parent IDs, impossible date ordering, and invalid amount/movement signs are rejected with raw-row evidence. Negative stock balances and overpayments are business exceptions retained in reporting. Cutoff filtering occurs in SQL; future records remain in the accepted database but do not enter current measures.

For live use, add source freshness, extract completeness and source control totals. This prototype's run checks establish internal consistency, not that a real upstream system delivered every record.
