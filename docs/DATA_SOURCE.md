# Data source and transformation policy

Publisher: City of Chicago Finance — Payments

Dataset: https://data.cityofchicago.org/d/s4vu-giwb

Size: 489,844 observed payment-disclosure records

Retrieved UTC: 2026-11-24T19:43:24.209867+00:00

Download: https://data.cityofchicago.org/api/views/s4vu-giwb/rows.csv?accessType=DOWNLOAD

Original SHA-256: `e54fd20aa89789ec353ba851f03327e5d02bc40e319cd1a0b9fc33a7977316c2`

Reuse/attribution reference: https://data.cityofchicago.org/. Government sources are published for public reuse under their portal terms; this repository does not relicense the source data as project code. UCI Online Retail II is attributed to Daqing Chen (2012), DOI 10.24432/C5CG6D, under CC BY 4.0. No source publisher endorses this analysis.

The raw government CSV is gzip-compressed without altering field content. UCI's workbook is converted by the included XML streaming converter into a lossless-field CSV, with explicit sheet and row references and Excel dates converted to ISO timestamps. The original workbook download is available through the source manifest; the large ZIP is not committed.

## Grain, calculations and limitations

Annual disclosures, dated monthly records, vendor-name concentration, direct-voucher share, department completeness and a reproducible exception-review queue. Exact repeated rows are retained and flagged because vouchers do not establish a unique transaction key.

Older rows are vendor/contract annual summaries. The year 2002 includes 1996–2002. No invoice due dates, open balances or inventory data exist, so AP aging and stock KPIs were removed. Vendor-name variants are not resolved into legal entities; do not infer duplicate disbursements or fraud. Business Central and Power Automate are documented deployment targets, not connected services.

Pinned snapshots make builds reproducible. A new upstream download must be reviewed as a new data version: update its manifest and checksums, rebuild outputs, re-review AI claims where applicable and recapture media. Never silently change a pinned snapshot.
