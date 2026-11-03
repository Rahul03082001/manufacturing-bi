# Manufacturing BI — decision log

Created: 2026-11-02

This starter file describes proposed defaults for a small portfolio project. No code, test pass, performance result, review, or Git commit is implied. The coding assistant may accept these defaults while implementing the supplied build prompt. Record what was actually verified.

## Rules

- Use `Proposed`, `Accepted`, or `Superseded` for design status. Track implementation separately as `Not started`, `Implemented, not verified`, or `Verified`.
- Keep meaningful earlier reasoning. Supersede a changed choice with a new numbered entry; update only the old status and reference.
- Link real source paths, test names, and commits when available. Use `Pending` rather than invented identifiers or results.
- Record trade-offs in business language first. Add entries for material changes to scope, money handling, model grain, publishing, controls, access, or tooling.
- A metric change also updates `metric_definitions.md`, lineage, and relevant tests.
- Actual Jira issues are optional later. Local task references do not prove use of Jira or team review.

## Index

| ID | Decision | Design status | Implementation |
| --- | --- | --- | --- |
| ADR-001 | Keep one evening's work to a component-inventory MVP | Accepted | Verified |
| ADR-002 | Use a local Docker/Python/PostgreSQL/Streamlit stack | Accepted | Verified |
| ADR-003 | Generate small deterministic, connected sources | Accepted | Verified |
| ADR-004 | Use fixed standard costs and integer USD cents | Accepted | Verified |
| ADR-005 | Use idempotent snapshot rebuilds for the MVP | Accepted | Verified |
| ADR-006 | Publish only a fully validated run | Accepted | Verified |
| ADR-007 | Reconcile independently exported finance inputs | Accepted | Verified |
| ADR-008 | Separate runtime processing and reporting permissions | Accepted | Verified |
| ADR-009 | Maintain explicit metric definitions and manual lineage | Accepted | Verified |
| ADR-010 | Prove four failures with isolated scenarios | Accepted | Verified |

## ADR-001: A small component-inventory MVP

- Date: 2026-11-02
- Status: Accepted; implementation: Verified
- Context: The project must demonstrate relevant data engineering in a short build session.
- Options: A complete factory/finance platform; a focused inventory-to-finance workflow.
- Decision: One plant, 30 days, roughly 1,000 movements, one dashboard, four deliberate faults.
- Reason: A working, explainable reconciliation demonstrates data quality and reporting integrity within a manageable scope.
- Trade-off: MES, BOMs, multi-site data, COGS, advanced costing, and procurement analytics are deferred. This is a planning target, not a guaranteed completion time.
- Verification: README.md and src/generate.py; actual generator output: 20 items, 5 suppliers, 100 PO lines, 1,000 movements, 1,000 finance entries. See docs/VERIFICATION.md.
- Commit / actual Jira key: d4ad0c1ccea81d0ea56a31c3e0227aaf03f4e18c (implementation) / None.

## ADR-002: Local containers and a small Python stack

- Date: 2026-11-02
- Status: Accepted; implementation: Verified
- Context: The Mac already runs Git and Docker; extra tooling would slow the first build.
- Options: Native installations; Docker Compose; a hosted/cloud platform.
- Decision: Python 3.12, pandas, PostgreSQL 16, SQLAlchemy/psycopg, Streamlit, and pytest inside Compose services. SQL files perform transformations.
- Reason: One reproducible environment can run ingestion, reports, and tests without local Python or database setup.
- Trade-off: dbt, orchestration frameworks, cloud deployment, and Power BI/Tableau are deferred. Streamlit demonstrates reporting but does not establish Power BI/Tableau experience.
- Verification: Dockerfile, requirements.txt + requirements.lock, compose.yaml; ARM64 database and dashboard healthy; reporter empty-state AppTest passed. See docs/VERIFICATION.md.
- Commit / actual Jira key: d4ad0c1ccea81d0ea56a31c3e0227aaf03f4e18c (implementation) / None.

## ADR-003: Deterministic synthetic source extracts

- Date: 2026-11-02
- Status: Accepted; implementation: Verified
- Context: Real ERP and finance records are unavailable, and controls need known test scenarios.
- Options: Public datasets; connected synthetic CSV exports.
- Decision: Generate five related sources with a fixed seed and date range. Create a clean history first, then independent scenario copies.
- Reason: Known source relationships allow precise tests of what should pass and fail.
- Trade-off: Synthetic data demonstrates engineering behavior, not real manufacturing or SAP integration experience. Locally produced file manifests provide limited, not independent external, assurance.
- Verification: tests/test_pipeline.py::test_same_seed_same_bytes and tests/test_input_controls.py; passed in PostgreSQL suite.
- Commit / actual Jira key: d4ad0c1ccea81d0ea56a31c3e0227aaf03f4e18c (implementation) / None.

## ADR-004: Fixed standard cost in integer cents

- Date: 2026-11-02
- Status: Accepted; implementation: Verified
- Context: Finance comparisons require explicit, reproducible valuation rules.
- Options: Floating-point dollars; integer cents; Decimal with more complex costing.
- Decision: Integer quantities, individual-unit UOM, fixed USD unit costs in integer cents, and zero opening stock. Receipts increase and production issues decrease inventory value.
- Reason: Exact arithmetic makes a discrepancy easy to explain and avoids binary floating-point rounding differences.
- Trade-off: No multi-currency, fractional quantities, changing cost basis, WIP, or full double-entry ledger. This is a simplified inventory-account extract.
- Verification: tests/test_pipeline.py::test_hand_calculated_fixture; 7 units, 17500 cents on both sides and zero difference, including a no-activity day; passed.
- Commit / actual Jira key: d4ad0c1ccea81d0ea56a31c3e0227aaf03f4e18c (implementation) / None.

## ADR-005: Idempotent full-snapshot processing

- Date: 2026-11-02
- Status: Accepted; implementation: Verified
- Context: Data is small, and correct reruns matter more than complex incremental ingestion tonight.
- Options: Incremental watermarks/upserts; complete versioned snapshot per attempt.
- Decision: Rebuild candidate snapshots from each full extract. Preserve run history but keep business outputs unchanged for identical inputs.
- Reason: Reprocessing is simple to verify and recover.
- Trade-off: Historical storage can repeat source rows across run versions. This is not CDC or an incremental ETL implementation; scale and retention are later work.
- Verification: tests/test_pipeline.py::test_identical_rerun_is_idempotent; different run IDs, identical business rows and unique daily keys; passed.
- Commit / actual Jira key: d4ad0c1ccea81d0ea56a31c3e0227aaf03f4e18c (implementation) / None.

## ADR-006: Validate before switching the published run

- Date: 2026-11-02
- Status: Accepted; implementation: Verified
- Context: A failed load must not replace trusted dashboard data.
- Options: Update live report tables then test; build a candidate run and select it only after success.
- Decision: Version results by run ID and update one published-run pointer transactionally after critical checks pass. Reporter views expose that selected run.
- Reason: Leaders retain the last valid report while a new attempt's problems are investigated.
- Trade-off: Data can be older after a failure; the dashboard must show the published timestamp and latest failed attempt separately. Empty-state behavior is needed before the first success.
- Verification: tests/test_pipeline.py::test_fault_preserves_publication_and_recovers, test_publication_rollback, test_repeatable_read_pins_dashboard_snapshot and tests/test_dashboard.py::test_dashboard_filters_and_failed_run_notice; passed.
- Commit / actual Jira key: d4ad0c1ccea81d0ea56a31c3e0227aaf03f4e18c (implementation) / None.

## ADR-007: Independent inputs and aligned reconciliation grain

- Date: 2026-11-02
- Status: Accepted; implementation: Verified
- Context: A check is meaningless if both compared values are copied from the same computed result.
- Options: Derive finance from the reporting mart; ingest a separately exported finance file.
- Decision: Finance is exported from clean source history and ingested separately. Compare signed cumulative balances by day and inventory account, using the same cutoff and currency. Aggregate before joining.
- Reason: An omitted posting can create a real, detectable difference without join multiplication.
- Trade-off: Both sources are still synthetic and share an initial generator. A hand-calculated fixture adds independent expected totals; this does not reproduce organizational separation of duties.
- Verification: tests/test_pipeline.py::test_clean_publish, test_missing_finance_exact_difference and test_hand_calculated_fixture; omitted -7500-cent posting gives -7500-cent differences on affected dates; passed.
- Commit / actual Jira key: d4ad0c1ccea81d0ea56a31c3e0227aaf03f4e18c (implementation) / None.

## ADR-008: Restricted application roles and reviewable evidence

- Date: 2026-11-02
- Status: Accepted; implementation: Verified
- Context: The reporting application should not change transactions or hide prior failures.
- Options: One administrator credential; separate setup, pipeline, and reporting roles.
- Decision: Use bootstrap ownership, a non-superuser pipeline account, and a non-owner read-only reporter. Log sanitized run/check evidence; block application updates/deletes of prior audit events.
- Reason: Role tests can show that reporting privileges are limited and run evidence is retained.
- Trade-off: Database owners/admins can override controls. A solo portfolio project has no independent approver and is not SOX-certified or production-compliant.
- Verification: tests/test_permissions.py; approved-view reads succeed; raw/candidate/audit reads, writes, and audit updates/deletes/truncates denied; passed.
- Commit / actual Jira key: d4ad0c1ccea81d0ea56a31c3e0227aaf03f4e18c (implementation) / None.

## ADR-009: Documented definitions and manual lineage

- Date: 2026-11-02
- Status: Accepted; implementation: Verified
- Context: A dashboard number needs an understandable formula and source path.
- Options: A lineage platform/parser; a reviewed mapping table for a few KPIs.
- Decision: Maintain CSV-field-to-SQL-to-view-to-dashboard mappings, including parsing and cents-to-dollars conversion. Keep formulas in SQL and document grain/cutoff/consumer.
- Reason: Small, explicit mappings are feasible to review and demonstrate the requested lineage practice.
- Trade-off: This is not automatic column-level lineage. Mappings must be updated with code and metric changes.
- Verification: docs/metric_definitions.md and docs/lineage.md map all dashboard cards, tables, trend and operational status to implemented SQL and views; manually checked against dashboard/app.py.
- Commit / actual Jira key: d4ad0c1ccea81d0ea56a31c3e0227aaf03f4e18c (implementation) / None.

## ADR-010: Four isolated failure demonstrations

- Date: 2026-11-02
- Status: Accepted; implementation: Verified
- Context: Multiple simultaneous defects can stop processing before downstream controls are exercised.
- Options: One dataset with every error; one clean baseline and four independent scenarios.
- Decision: Test duplicate movement, unknown item, missing finance posting, and negative inventory independently. Checks do not read the test-only expected-answer manifest.
- Reason: Each test establishes which control detects which failure, followed by safe recovery.
- Trade-off: This is a focused control set, not comprehensive enterprise data-quality coverage. Expected scenario rejections are successful tests when correctly asserted.
- Verification: tests/test_pipeline.py::test_fault_preserves_publication_and_recovers (four parameterized scenarios) and test_missing_finance_exact_difference; passed.
- Commit / actual Jira key: d4ad0c1ccea81d0ea56a31c3e0227aaf03f4e18c (implementation) / None.

## Template for a later decision

```markdown
## ADR-011: <clear title>

- Date: <actual date>
- Status: Proposed | Accepted | Superseded by ADR-XXX
- Implementation: Not started | Implemented, not verified | Verified
- Context: <business problem and constraint>
- Options: <two realistic alternatives>
- Decision: <choice>
- Reason: <why it fits the project>
- Trade-off: <limitations and deferred work>
- Verification: <actual file/test/command and observed result, or Pending>
- Commit / actual Jira key: <real values, or Pending / None>
```

## ADR-011: Disposable test service and pinned application environment

- Date: 2026-11-02
- Status: Accepted; implementation: Verified
- Context: The runtime pipeline must not receive administrator credentials just to create a test database, and tests must not change demo data.
- Options: Grant runtime database creation privileges; reuse the demo database; create an isolated Compose test profile.
- Decision: Add `db-test` (PostgreSQL 16, tmpfs storage) and `tests` services under profile `test`. Use the shared Python image with separate test pipeline/reporter settings. Pin direct and resolved Python dependencies.
- Reason: Real database tests can exercise runtime permissions without exposing the demo database to fixture setup.
- Trade-off: The canonical test command is `docker compose --profile test run --rm tests`, not `docker compose run pipeline pytest`. Two optional services supplement the three demo services. Test instances consume extra local memory; hosted CI remains unexecuted until a remote is created. Base image tags remain mutable.
- Verification: compose.yaml, requirements.lock, tests/conftest.py host/database assertions; 48 PostgreSQL and Streamlit tests passed. The default demo volume stayed intact.
- Commit / actual Jira key: d4ad0c1ccea81d0ea56a31c3e0227aaf03f4e18c (implementation) / None.

## ADR-012: Database publication guard and consistent dashboard reads

- Date: 2026-11-02
- Status: Accepted; implementation: Verified
- Context: A pointer is safe only if it cannot select a rejected or incomplete run; separate dashboard queries can otherwise observe different publications.
- Options: Application checks alone; database backstop plus a consistent read transaction.
- Decision: An owner-installed trigger requires SUCCESS and all eight named passing controls when changing the pointer. The dashboard reads only approved views inside one read-only REPEATABLE READ transaction and pins its selected run ID.
- Reason: An accidental direct runtime pointer update cannot publish failed results, and all cards agree during concurrent refreshes.
- Trade-off: Pipeline is still trusted to insert honest control results; there is no independent approver. Multiple publishers follow successful completion order. In-progress attempts are audited but the narrow dashboard status shows the latest completed attempt.
- Verification: sql/publication_guard.sql; tests/test_pipeline.py::test_database_rejects_publication_of_failed_run and test_repeatable_read_pins_dashboard_snapshot; tests/test_dashboard.py; passed.
- Commit / actual Jira key: d4ad0c1ccea81d0ea56a31c3e0227aaf03f4e18c (implementation) / None.

## Verification record

See [VERIFICATION.md](VERIFICATION.md) for actual commands and outputs, and [BACKLOG.md](BACKLOG.md) for explicitly deferred work. Original context, alternatives, and trade-offs above are preserved. `Pending` commit fields do not imply missing implementation; actual local history is recorded after each commit is created. No real Jira keys or external review are claimed.

The dashboard service also overrides the shared development mounts: only its application/source folders are mounted read-only; delivered inputs and evidence folders are not mounted into the reporting container. This complements database role restrictions without claiming process isolation against a host administrator.

## ADR-013: Public portfolio repository and free hosted deployment

- Date: 2026-11-02
- Status: Accepted; implementation: Implemented, not verified (remote deployment)
- Context: The owner explicitly requested GitHub publication and a live project, then selected a public repository and free hosting only. This supersedes the earlier local-only scope boundary for this requested deployment.
- Options: Keep local-only; paid hosting; free Streamlit UI plus managed PostgreSQL.
- Decision: Publish under Rahul03082001/manufacturing-bi and prepare Streamlit Community Cloud + Neon free hosting. Preserve PostgreSQL calculations, restricted reporter identity, and separate owner/pipeline operations. No paid plans.
- Trade-off: Account sign-in and provider consent may require the owner; free services may sleep and impose resource limits. This is a live portfolio demo, not production availability.
- Verification: 50 local tests passed after adding cloud entry-point rerender and explicit remote TLS configuration checks. Secret files are excluded from Git and Docker. Actual remote outcomes are recorded separately in DEPLOYMENT.md.
- Commit / actual Jira key: Pending / None.
