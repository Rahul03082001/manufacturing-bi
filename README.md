# Manufacturing Data Pipeline & Inventory Reconciliation Dashboard

A live portfolio project for Rahul Gehlot: receive manufacturing extracts, check their quality, reconcile component inventory to an independently delivered finance extract, and publish only validated results. Failed attempts leave the last approved dashboard intact and retain evidence for diagnosis.

**[Open the live dashboard](https://rahul-manufacturing-bi.streamlit.app/)** · [Source on GitHub](https://github.com/Rahul03082001/manufacturing-bi)

Hosted on free Streamlit Community Cloud and Neon PostgreSQL. The synthetic demo closes January 30, 2026 with **$1,168,661.00** in inventory and finance, a **$0.00** difference, and **20** components with positive stock. Free services may sleep when idle; allow time for the app to wake up.

## Start locally

Requires Docker Desktop with Compose and Git. All Python, SQL transformations, and tests run in containers; no host Python installation is needed. Native ARM images work on Apple Silicon. From this folder:

```bash
# First setup only; preserves an existing .env.
test -f .env || cp .env.example .env
docker compose up -d --build --wait db dashboard
docker compose run --rm pipeline python -m src.generate
docker compose run --rm pipeline python -m src.pipeline --dataset data/clean
```

Open [the local dashboard](http://127.0.0.1:8501). Before the first successful load it shows an empty state. The UI is bound only to host loopback; PostgreSQL has no published host port. Data and evidence are shared through local folders; PostgreSQL uses a persistent named volume. The dashboard receives only its reporter database password.

For Git provenance on subsequent attempts (the pipeline records `unknown` if no valid SHA is supplied):

```bash
export GIT_SHA="$(git rev-parse HEAD)"
docker compose run --rm pipeline python -m src.pipeline --dataset data/clean
```

A SHA identifies a commit, not proof of a clean working tree. Check `git status --short` when collecting evidence. Do not copy passwords, `.env`, or connection URLs into screenshots or commits. `.env.example` is deliberately labeled **local demo** configuration. Changing it after volume initialization does not change stored database role passwords.

## Five-minute demo

1. Run the startup commands above. Open Inventory, select an as-of date/components, then inspect the plant-wide Reconciliation tab. Daily differences must be $0.00.
2. Note the published run ID in Run status. Reject a separately delivered file with an omitted finance posting:

   ```bash
   docker compose run --rm pipeline python -m src.pipeline --dataset data/missing_finance
   ```

   Expected exit **2**, outcome `FAILED`, control `reconciliation`. This is an intentional rejection. The manifest describes the altered file correctly, so delivery passes and reconciliation detects the defect.
3. Click **Refresh approved data**. The warning reports the failed attempt; cards retain the prior successful run. Run status shows the failure and diagnostic differences.
4. Recover without resetting anything:

   ```bash
   docker compose run --rm pipeline python -m src.pipeline --dataset data/clean
   ```

   Expected exit **0**, outcome `SUCCESS`. Refresh to see the new approved run.
5. Inspect `evidence/<run_id>.json` and `data/received/<run_id>/` to connect checks to delivered bytes. These are review evidence, not external assurance or compliance certification.

Other isolated faults (each expected exit 2):

```bash
docker compose run --rm pipeline python -m src.pipeline --dataset data/duplicate_movement
docker compose run --rm pipeline python -m src.pipeline --dataset data/unknown_item
docker compose run --rm pipeline python -m src.pipeline --dataset data/negative_inventory
# Restore a successful latest attempt afterward.
docker compose run --rm pipeline python -m src.pipeline --dataset data/clean
```

Expected controls: `business_key_uniqueness`, `relationships`, `negative_inventory`, respectively. `data/test_only_faults.json` records injected IDs for tests/review; the pipeline never reads it. Each scenario starts from a separate clean copy and changes only its relevant source.

## Tests

```bash
docker compose build pipeline
docker compose --profile test run --rm tests
```

The test runner shares the application image but uses `db-test/manufacturing_test`, a separate PostgreSQL 16 container with temporary memory-backed storage. It has no demo administrator credential. Tests assert the target name/host before processing. To ensure a fresh test database or release it afterward:

```bash
# Affects ONLY the disposable test service, never the demo volume.
docker compose --profile test stop db-test
docker compose --profile test rm -f db-test
docker compose --profile test run --rm tests
```

Tests cover deterministic bytes; an independently hand-authored 10 × $25 receipt / 3 × $25 issue fixture ($175 closing); no-activity-day carry-forward; clean publish; identical rerun totals and uniqueness; all four faults; retained published data; recovery; transactional rollback and concurrent read consistency; database constraints; reporter restrictions and denied audit updates/deletes/truncation; parsing/delivery/business-rule edge cases; and actual Streamlit rendering/filter behavior against PostgreSQL. See [verification](docs/VERIFICATION.md) for measured results. A small GitHub Actions workflow reuses these commands; the first hosted run passed. See docs/DEPLOYMENT.md for the source repository and run link.

## Model and controls

Default generated period: **2026-01-01 through 2026-01-30**, seed 42, one plant, 20 components, 5 suppliers, 100 PO lines and 1,000 inventory movements. Run `python -m src.generate --help` inside the pipeline container for configurable defaults. Receipts precede issues in the synthetic clean history, never exceed PO quantities, and provide sufficient stock. This deliberately simple pattern is not a forecast or realistic factory schedule.

Quantities are integer individual units; money is integer USD cents at fixed standard cost. Both balances open at zero. Inventory value = quantity × cost. Finance postings are signed changes in inventory account 1400, separately exported from the clean event history. SQL aggregates each source to day/account before joining. Difference = inventory − finance; every applicable day must equal zero. Calendar spines include days with no movements.

The pipeline performs **idempotent snapshot processing**, not incremental ETL or CDC. Each attempt gets a UUID, retained input copies, raw lineage, typed candidate rows, SQL results, append-only audit events and a compact evidence JSON. Identical reruns create audit history while leaving business counts and totals unchanged. Invalid candidates do not become reporting data.

Critical checks execute in order and stop at the first failure: source delivery (file list/count/hash/header), schema/types/required values, business-key uniqueness, relationships, business rules, receipt limits, negative running quantity, daily reconciliation. Database keys/FKs/checks provide a second layer. The owner-installed publication trigger requires a successful outcome and all eight passing checks. Successful completion and the pointer switch commit atomically. A dashboard refresh uses one read-only repeatable-read transaction, so every card/chart sees the same approved version.

| Role | Purpose | Permissions |
| --- | --- | --- |
| bootstrap_owner | First-time schema/role setup | Owns schemas; administrator can override controls |
| pipeline | Runtime ingestion, transformation, evidence, publication | Non-superuser; SELECT/INSERT candidate/raw/audit; pointer SELECT/INSERT/UPDATE; cannot mutate existing audit events |
| reporter | Dashboard | Non-owner; SELECT only on five approved views; no raw/candidate/full-audit/pointer access or writes |

The pipeline identity is trusted to evaluate checks honestly; it is not an independent approver. Audit restrictions protect existing records from application edits, not from a database owner or an administrator. Completed outcome, files and checks commit together; an interrupted process may leave an audit start/candidate without a terminal outcome. Status explicitly reports the latest **completed** attempt. The newest successful completion wins if multiple runs publish concurrently. Automatic recovery/retention of abandoned attempts is deferred.

## Repository guide

- `src/generate.py`: deterministic source history, clean delivery and isolated faults.
- `src/controls.py`, `src/pipeline.py`, `src/db.py`: exact parsing, controls, retained inputs, audit and publication.
- `sql/bootstrap.sql`, `sql/publication_guard.sql`: owner setup, tables/views/grants and publication guard.
- `sql/models.sql`: reviewable CTEs, joins and window functions.
- `dashboard/app.py`: approved data, inventory filters, reconciliation and run status.
- `tests/`: real database and Streamlit tests, including independent fixture in conftest.py.
- [Decisions](docs/DECISIONS.md), [metric dictionary](docs/metric_definitions.md), [manual lineage](docs/lineage.md), [local backlog](docs/BACKLOG.md), [interview notes](docs/INTERVIEW.md).

## Limits and safe operations

This is a synthetic portfolio MVP, not a complete accounting system or production/SOX-compliant service. No counterpart accounts, BOM/MES, WIP, actual costing, COGS, taxes or revenue recognition. No ERP/SAP integration, dbt, Airflow, Spark, Kafka, Power BI/Tableau, LLM runtime, custom frontend, or automatic column-lineage parser. Finance and inventory share the generator's initial history, so delivery manifests are not independent external assurance; hand calculations provide an additional test oracle. Daily balance reconciliation can miss offsetting posting errors. Data is retained indefinitely; growth, retention and schema migrations need a later design.

The MVP accepts at most a 366-day declared period, ISO dates and timezone-free event timestamps, and absolute integer field values up to 1,000,000,000. Aggregates use PostgreSQL bigint and reject processing errors on overflow; this is not a large-scale loader. Base image tags can change; direct and transitive Python packages are pinned to the tested environment. An upstream Altair deprecation warning occurs in Streamlit tests without affecting their result.

Stop services safely with `docker compose --profile test down` (no `-v`); the demo volume remains. Restart with the startup command. Regenerate and rerun clean inputs to recover a failed demo. Bootstrap SQL runs only on an empty database volume. Existing schema changes require an intentional migration, not deleting volumes. To make a completely separate new demo, first stop the current dashboard, then use a different Compose project name (`docker compose -p manufacturing-bi-fresh ...`) for every command; it creates another volume while preserving the old one. Never delete the database volume as routine troubleshooting.

Setup follows the official [Streamlit Docker guide](https://docs.streamlit.io/deploy/tutorials/docker), [Compose startup ordering](https://docs.docker.com/compose/how-tos/startup-order/), and [PostgreSQL 16 privilege model](https://www.postgresql.org/docs/16/ddl-priv.html).

## Public portfolio deployment

The public dashboard was verified on November 3, 2026: Inventory, Reconciliation and Run status display the approved hosted snapshot. The app uses only the restricted reporter credential over verified TLS. Owner and pipeline credentials stay with the local operator. The full suite passes **51 tests**, and GitHub Actions passes. See [deployment instructions and evidence](docs/DEPLOYMENT.md) for setup, actual run links and hosted checks. Local Docker startup remains available.
