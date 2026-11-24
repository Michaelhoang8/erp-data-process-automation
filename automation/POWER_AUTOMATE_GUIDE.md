# Power Automate implementation blueprint

Status: local Python/SQL workflow runs. This is a step-by-step design, not an importable flow package. No Microsoft connections, cloud resources, schedules or notifications have been created.

## Practical deployment path

Use a scheduled cloud flow for orchestration and a separately deployed worker for Python. A Power Automate cloud flow cannot execute this local Python script by itself. For a Windows workstation implementation, use a desktop flow on a registered machine to run `automation/run_local.ps1`, then return the manifest and output location. Confirm your tenant's machine, licensing and execution requirements before choosing attended or unattended execution. Alternatively, package the worker in your approved hosted service and invoke its authenticated endpoint; that service is not included here.

## Extraction contract

The worker expects six CSV files with the exact schemas in `docs/data_dictionary.md`. A real integration must map Business Central resources into these schemas. Download a complete staged batch first; do not run the worker against half-written extracts. Follow pagination, retain extraction timestamp, tenant/environment/company identifiers and cutoff, and publish the batch only when every extract completes. Determine how to preserve historical payment applications and inventory movements before calculating historical cutoffs.

1. **Recurrence:** create Scheduled cloud flow. Suggested business setting: weekdays at 07:00, Mountain time; confirm the business's schedule. This is a proposal, not an installed timer.
2. **Initialize run context:** environment, company, AsOf, BatchID and destination library. Keep secrets in authenticated connections, not these project files.
3. **Extraction scope:** obtain complete Business Central source exports, map fields, and write a batch directory. Retrying a read must not append duplicate records to an existing partial file. A failed extraction stops the batch.
4. **Worker scope:** invoke the deployed worker or registered desktop flow. Set concurrency to one for this project because `latest.json` and the stable dashboard are shared pointers. Propagate nonzero exit code as failure. Use a bounded retry only for transient connectivity issues; schema and conflicting-duplicate failures require correction.
5. **Read manifest:** validate `run_id`, `as_of`, `status`, `quality_exception_count`, `checks` and `reused`. The worker writes the manifest only after its validation and exports succeed. `needs_review` is a successful analytical run with actionable exceptions, not a failed execution.
6. **Idempotency:** maintain a SharePoint RunRegister with RunID unique, AsOf, Status, OutputURL, StartedAt, CompletedAt and Error. Check the RunID before publication. If already completed, end without a second notification. Configure serial flow execution to avoid competing claims.
7. **Publish scope:** create an output folder keyed by RunID and upload report CSVs, brief and manifest. Do not replace the previous published report until all new files exist. Mark RunRegister completed only after publication succeeds.
8. **Review routing:** when status is needs_review, create or update review items keyed by RunID + Area + RecordID + Finding from action_queue.csv. Assign owner roles to actual tenant users during deployment. A role in the local CSV is not an actual assignment.
9. **Optional notification:** once an authorized recipient list is configured, send a single report link with cutoff, exception count and review status. No sending is implemented or authorized by this blueprint.
10. **Failure scope:** use Configure run after for failed/timed-out extraction, worker or publishing scopes. Record the error and preserve the last successful report. Route failure to the configured operator; never issue a clean status after failure.

## Parse JSON sample schema

Use `manifest_schema.json` for the worker result. Condition for review: `equals(body('Parse_JSON')?['status'], 'needs_review')`. A `reused` worker result does not prove the files were published to SharePoint; consult RunRegister before skipping a previously failed publication.

## Tenant acceptance tests

- Run one batch and compare published totals to the local brief.
- Repeat identical input: no duplicate report or notification.
- Simulate extraction failure: previous report stays available and run records failure.
- Introduce a conflicting invoice ID: worker fails without a successful manifest.
- Introduce an exact replay: row appears in the quarantine log, financial totals do not double.
- Verify permissions, assigned review owners, timezone and publication links using a test destination.

## Official references

- [Create a scheduled cloud flow](https://learn.microsoft.com/en-us/power-automate/run-scheduled-tasks)
- [Business Central API v2.0](https://learn.microsoft.com/en-us/dynamics365/business-central/dev-itpro/api-reference/v2.0/)
- [Business Central endpoint structure](https://learn.microsoft.com/en-us/dynamics365/business-central/dev-itpro/webservices/api-endpoint-structure)

The references establish scheduling and API structure. The worker orchestration and batch contract above are this project's proposed implementation and require tenant validation.
