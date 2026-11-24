# Microsoft deployment blueprint

The local worker analyzes real Chicago payment disclosures. It does not connect to Business Central or deploy a cloud flow.

1. Create a scheduled flow in your own tenant. Stage a complete reviewed source snapshot; keep its checksum and download metadata.
2. Execute `python src/run_pipeline.py` through a registered Power Automate desktop-flow machine or your separately hosted worker. A cloud flow cannot execute local Python by itself.
3. Parse `reports/manifest.json` using the supplied schema. Failed execution stops publication. `needs_review` means the pipeline completed with review tasks, not that it failed.
4. Store the run_id as a unique key in a publication register. Identical inputs reuse the immutable local run. A local `reused` flag does not prove SharePoint publication previously succeeded.
5. Upload the completed report bundle to a run-specific folder, then update the current link. Configure serial execution; concurrent writers are not supported by the local publisher.
6. Import `action_queue.csv` into your review system or use the workbook's ReviewQueue table in Excel Online (Business). Assign actual tenant reviewers yourself; role labels are not user assignments.
7. Configure any notification recipients explicitly. No messages, payment actions, credentials or schedules are created by this repository.

Business Central adaptation requires a separate mapping from actual vendor ledger entries and payment applications. The Chicago disclosure schema is not a Business Central import payload. Never create fabricated invoice dates, terms or stock records to satisfy the previous demonstration's schema.

Acceptance checks: repeat the same input without duplicate publication; corrupt a source file and confirm the prior successful output remains available; verify monetary reconciliation; confirm signed amounts and annual rollups survive; test the destination with a non-production folder.

References: [Power Automate scheduling](https://learn.microsoft.com/en-us/power-automate/run-scheduled-tasks), [Business Central API](https://learn.microsoft.com/en-us/dynamics365/business-central/dev-itpro/api-reference/v2.0/).
