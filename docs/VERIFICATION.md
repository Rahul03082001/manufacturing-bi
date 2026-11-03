# Actual verification record

Executed on **2026-11-02, America/New_York**. Some audit timestamps are November 3 UTC, still November 2 locally. Platform: macOS Apple Silicon, Docker Desktop 4.95.0, Linux ARM64 containers, Compose 5.1.0. Actual runtimes: Python 3.12.16 and PostgreSQL 16.15. Direct versions: pandas 2.2.3, SQLAlchemy 2.0.38, psycopg 3.2.5, Streamlit 1.42.2, pytest 8.3.4. Resolved packages are captured in requirements.lock and used as build constraints.

## Commands and observed outcomes

| Actual command/check | Outcome |
| --- | --- |
| `docker version`; `docker compose version` | Docker engine accessible after system approval; native Linux ARM64 |
| `docker compose up -d --build --wait db dashboard` | Image build passed `pip check`; both services healthy; repeated with dependency lock |
| `docker compose exec -T dashboard python -c ...` using Streamlit AppTest before first publish | Asserted no exception/error and “No approved data” message; reporter connection verified |
| `docker compose run --rm pipeline python -m src.generate` | Exit 0; actual counts: 20 items, 5 suppliers, 100 PO lines, 1,000 movements, 1,000 finance entries |
| `docker compose --profile test run --rm tests pytest -q -p no:cacheprovider tests/test_pipeline.py` (initial balance milestone) | 3 passed, including independent $175 fixture |
| `docker compose --profile test run --rm tests` (final pinned image) | **48 passed, 1 warning**, exit 0 |
| `docker compose run --rm pipeline python -m src.pipeline --dataset data/clean` | Exit 0, SUCCESS, published |
| Same pipeline command for `data/duplicate_movement` | Exit 2, FAILED, business_key_uniqueness |
| Same pipeline command for `data/unknown_item` | Exit 2, FAILED, relationships |
| Same pipeline command for `data/missing_finance` | Exit 2, FAILED, reconciliation |
| Same pipeline command for `data/negative_inventory` | Exit 2, FAILED, negative_inventory |
| Clean command after the four rejections | Exit 0, SUCCESS; run `4e635a02-6798-4efe-84a7-b3b9b32f9017` |
| Reporter SELECT from approved reconciliation/status views | January 30 inventory 116866100 cents; finance 116866100 cents; difference 0; latest outcome SUCCESS |
| Live browser at `http://127.0.0.1:8501` | Actual inventory card $1,168,661.00, 20 positive-stock components, genuine trend and item balances visible |

A test initially asserted permission-error SQLSTATE for DELETE on a join view; PostgreSQL correctly refused the write as a non-updatable view (55000). The corrected test asserts that refusal and separately verifies that the reporter has no write privileges at all. A single upstream Altair deprecation warning remains in Streamlit rendering; no failures were suppressed. This is a functional test result, not a performance benchmark.

## Recorded demo evidence

These run IDs are real local attempts. Each has a sanitized JSON file under `evidence/` and retained inputs under `data/received/` (both ignored by Git). Do not expect these local artifacts in a fresh checkout; rerun the demo to create new evidence.

| Scenario | Run ID | Outcome |
| --- | --- | --- |
| duplicate_movement | 3379be36-58cb-4062-9cf6-b61dd305f7b8 | FAILED / expected |
| unknown_item | 7cee29fd-6fff-4976-8183-cdcf80aa9c8b | FAILED / expected |
| missing_finance | d233a833-355e-49a5-9618-93f38522fee0 | FAILED / expected |
| negative_inventory | 4fe27cf2-6b26-4029-81e4-42398146bd0f | FAILED / expected |
| clean recovery | 4e635a02-6798-4efe-84a7-b3b9b32f9017 | SUCCESS |

## Local history and limits

Implementation commit: `d4ad0c1ccea81d0ea56a31c3e0227aaf03f4e18c` — pipeline, SQL, dashboard, Docker setup, 48 tests and CI workflow. It is the Git SHA carried by the recorded CLI demo attempts. Later documentation and dashboard filesystem isolation changes appear in local Git history; no commit IDs are invented. Git used the machine's existing automatic author/committer identity; no global Git configuration was changed.

CI workflow was added only after real local checks passed. Hosted GitHub Actions and deployment were verified in the later follow-ups below. No Jira issue, external review, SOX certification or production readiness is claimed. Administrator override, synthetic common-source limitations and deferred work are documented in README and BACKLOG.

Final deployment check: `docker compose up -d --wait dashboard` passed after limiting dashboard mounts. A container-side AppTest asserted reporter identity, no pipeline/owner password environment variables, no `/app/data` or `/app/evidence` directories, no rendering errors and the $1,168,661.00 published card. The disposable test service was stopped after verification; the demo database and dashboard remain running.

## Hosting preparation follow-up

At the owner's request, added a root cloud entry point, configurable PostgreSQL port/TLS/timeouts, secret exclusions and separate cloud operator Compose commands. Executed `docker compose build pipeline && docker compose --profile test run --rm tests`: **50 passed, 1 upstream deprecation warning**, exit 0. Hosted database and public URL checks were then performed separately, as recorded below.

Hosted follow-up: GitHub Actions run 41556442227 completed successfully. A dedicated free Neon PostgreSQL 16 database was initialized using verified TLS; the clean run ff2cf6a5-3db6-4c07-8207-7d55f8415ce8 published 116866100-cent closing inventory and finance balances with zero differences. `docker compose -f compose.cloud.yaml run --rm verify` confirmed actual approved-view reads and denied raw/candidate reads and pointer writes. Streamlit public-page verification is tracked in DEPLOYMENT.md.

Cloud startup handling follow-up: observed missing DB_USER during initial Streamlit startup. Moved connection construction inside error handling and added a test for the readable setup state. Matched the hosted platform's pyarrow 24.0.0 selection in both dependency files. Rebuilt image and ran the full suite: **51 passed, 1 upstream Altair deprecation warning**, exit 0.

## Public app verification — November 3, 2026

After the owner saved reporter secrets, opened [the actual hosted app](https://rahul-manufacturing-bi.streamlit.app/) in the browser. Inventory showed **$1,168,661.00** and **20** components with positive stock. Reconciliation showed inventory and finance each **$1,168,661.00**, difference **$0.00**. Run status showed approved snapshot `ff2cf6a5-3db6-4c07-8207-7d55f8415ce8`, latest attempt **SUCCESS**, and no recorded failures in the dedicated hosted database. Streamlit sharing confirmed the app is public.

GitHub Actions [run 41580632413](https://github.com/Rahul03082001/manufacturing-bi/actions/runs/41580632413) passed for application commit `fe0cda86fd47f2679ffaddd547e4e0132ab0f4eb`; [run 41581264347](https://github.com/Rahul03082001/manufacturing-bi/actions/runs/41581264347) passed after the dev-container addition. The original local verification record above is retained as evidence of earlier milestones.
