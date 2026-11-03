# Local backlog

These are local references, not Jira issues. The public repository and free hosted dashboard were completed under LOCAL-015; no Jira tickets were created.

| Local ID | Task | Status | Evidence |
| --- | --- | --- | --- |
| LOCAL-001 | Container setup and empty dashboard | Completed | Docker health checks; reporter AppTest empty-state assertion in verification log |
| LOCAL-002 | Deterministic independent CSV exports | Completed | src/generate.py; test_same_seed_same_bytes |
| LOCAL-003 | SQL inventory and finance balances | Completed | sql/models.sql; test_hand_calculated_fixture |
| LOCAL-004 | Safe publication and isolated fault controls | Completed | test_fault_preserves_publication_and_recovers; publication trigger test |
| LOCAL-005 | Restricted roles and immutable audit events | Completed | tests/test_permissions.py |
| LOCAL-006 | Dashboard, filters, failure notice | Completed | tests/test_dashboard.py |
| LOCAL-007 | Decisions, lineage, metrics and demo | Completed | docs/ and README.md |
| LOCAL-008 | Tiny CI workflow using local commands | Completed | .github/workflows/test.yml; successful GitHub Actions runs linked in DEPLOYMENT.md |
| LOCAL-009 | Real ERP ingestion, independent finance assurance | Deferred | Synthetic sources only |
| LOCAL-010 | Incremental ingestion, retention, migrations, orchestration | Deferred | Snapshot MVP; no CDC/dbt/Airflow/Spark/Kafka |
| LOCAL-011 | Production authentication, secrets manager, approvals | Deferred | Local demo settings; application roles are not independent reviewers |
| LOCAL-012 | Multi-plant/currency, variable costs, WIP, COGS, full ledger | Deferred | Fixed inventory-account model only |
| LOCAL-013 | Automated column lineage, Power BI/Tableau | Deferred | Manual lineage + Streamlit; hosting completed under LOCAL-015 |
| LOCAL-014 | Dependency refresh and base-image digest pinning | Deferred | Tested lock captured; image tags remain mutable; upstream chart deprecation warning recorded |

LOCAL-015 — **Completed**: public GitHub publication and free hosted app, requested by the owner. Cloud entry point, verified TLS, reporter-only secrets and operator commands implemented; 51 local tests and hosted CI pass. Inventory, reconciliation and run status verified in the public app on November 3, 2026. Actual links and evidence are recorded in [DEPLOYMENT.md](DEPLOYMENT.md).
