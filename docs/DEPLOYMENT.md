# Hosted deployment

**[Live public dashboard](https://rahul-manufacturing-bi.streamlit.app/)** · **[GitHub repository](https://github.com/Rahul03082001/manufacturing-bi)**

Verified November 3, 2026: the hosted dashboard reads the approved Neon snapshot and displays matching inventory and finance balances. The local Compose application and tests remain the reference implementation. Cloud deployment uses the root `streamlit_app.py` entry point, configurable port/TLS settings, ignored secret paths, and local operator commands for managed PostgreSQL.

## Free portfolio hosting

The deployed UI uses Streamlit Community Cloud and the database uses Neon PostgreSQL 16. The owner selected free hosting and completed account consent. Both services use free plans; idle services may sleep and usage limits apply. Free hosting has no uptime guarantee. No paid plan is authorized.

- [Streamlit deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
- [Streamlit secret settings](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)
- [Neon plan details](https://neon.com/docs/introduction/plans)
- [Neon restricted SQL-created roles](https://neon.com/docs/manage/roles)

## Database preparation

Create a dedicated, empty PostgreSQL 16 database in the selected hosting account. Use the provider's direct database hostname for bootstrap and the pipeline. Never bootstrap a shared existing database: the setup creates fixed role/schema names and intentionally fails rather than replacing existing objects.

Keep owner and runtime credentials in separate ignored files:

`.env.cloud.owner` (local operator only):

```dotenv
PGHOST=your-managed-postgres-host
PGPORT=5432
PGDATABASE=manufacturing
PGUSER=your-provider-owner-role
PGPASSWORD=your-provider-owner-password
PGSSLMODE=verify-full
PGSSLROOTCERT=/etc/ssl/certs/ca-certificates.crt
PIPELINE_PASSWORD=a-new-random-pipeline-password
REPORTER_PASSWORD=a-different-new-random-reporter-password
```

`.env.cloud.pipeline` (local operator only):

```dotenv
DB_HOST=your-managed-postgres-host
DB_PORT=5432
DB_NAME=manufacturing
DB_USER=pipeline
DB_PASSWORD=the-same-new-pipeline-password
DB_SSLMODE=verify-full
DB_SSLROOTCERT=/etc/ssl/certs/ca-certificates.crt
```

Use random passwords, not the local demo defaults. Protect these files on the host. They and `.streamlit/secrets.toml` are excluded from both Git and Docker build context. Do not paste secrets into chat, screenshots or commit messages.

Run from the project root after configuring the files:

```bash
# One-time setup, atomic; reruns against an initialized database fail safely.
docker compose -f compose.cloud.yaml run --build --rm setup
# Build current code and load a separately validated hosted snapshot.
docker compose -f compose.cloud.yaml build pipeline
docker compose -f compose.cloud.yaml run --rm pipeline python -m src.generate
export GIT_SHA="$(git rev-parse HEAD)"
docker compose -f compose.cloud.yaml run --rm pipeline python -m src.pipeline --dataset data/clean
```

The current hosted database has already been initialized; do not repeat setup against it. Normal reruns use only the final pipeline command. The separate cloud operator Compose file starts no local database. Evidence and retained sources stay on the operator machine; database audit remains in the managed database. Hosted disaster recovery and external evidence storage remain deferred.

## Dashboard deployment

Select the GitHub repository, `main` branch, **streamlit_app.py**, and **Python 3.12**. Configure the seven root-level settings in `deploy/reporter-secrets.example.toml` using the hosted **reporter** password. Streamlit exposes root-level secrets as environment variables. The app must never receive owner or pipeline credentials. Keep TLS verification enabled and use a provider-supported certificate trust path.

Only the already-approved synthetic inventory and narrow status views are visible to visitors. There is no public upload, pipeline execution or database administration endpoint. Review repository visibility and app visibility separately; a private repository does not automatically make the hosted dashboard private.

After deploy, verify the real URL opens, the closing value agrees with the hosted database, differences are zero, and the reporter is denied raw reads/writes. Then set the repository homepage to the verified URL. GitHub Pages alone cannot run this Streamlit + PostgreSQL application.

## Verified deployment (completed 2026-11-03, America/New_York)

- [Public source](https://github.com/Rahul03082001/manufacturing-bi) (`main`).
- GitHub Actions succeeded for application commit `fe0cda86fd47f2679ffaddd547e4e0132ab0f4eb`: [run 41580632413](https://github.com/Rahul03082001/manufacturing-bi/actions/runs/41580632413). The subsequent dev-container commit `d13e1d4f479875569c4b301592cd7fa4bea8eb51` also passed [run 41581264347](https://github.com/Rahul03082001/manufacturing-bi/actions/runs/41581264347). These verify the container test workflow on GitHub's Linux runner.
- Created a dedicated **free** Neon project `manufacturing-bi` in AWS US East 2 with PostgreSQL **16**, database `manufacturing`. No paid upgrade or extra optional Neon services were enabled.
- Owner bootstrap executed transactionally. The first connection attempt identified a missing CA bundle in the standard PostgreSQL client image; `Dockerfile.setup` adds public CA certificates. The successful retry kept `verify-full` enabled.
- `docker compose -f compose.cloud.yaml run --build --rm setup`: success.
- Hosted clean pipeline run `ff2cf6a5-3db6-4c07-8207-7d55f8415ce8`: SUCCESS, all eight controls passed. January 30 inventory and finance each equal **116866100 cents**, difference **0**.
- `docker compose -f compose.cloud.yaml run --rm verify`: passed actual reporter queries and denied raw/candidate reads and publication writes.
- Streamlit deployment uses `streamlit_app.py`, branch `main`, Python **3.12**, with only reporter database settings in app secrets.
- Live browser verification: Inventory displays **$1,168,661.00** and **20** positive-stock components; Reconciliation displays matching inventory/finance balances and a **$0.00** difference; Run status shows the hosted run above with latest attempt **SUCCESS**.
- Streamlit's sharing dialog confirms **Make this app public** is enabled.

For future database smoke checks, keep `.env.cloud.reporter` locally with the same root settings as the TOML example, in dotenv `KEY=value` format, and run `docker compose -f compose.cloud.yaml run --rm verify`. This service receives only the reporter credential. The cloud operator env files use Compose parsing; do not pass quoted dotenv values directly to `docker run --env-file`, whose parsing differs.

Initial startup lacked reporter secrets (`DB_USER` missing). The owner saved the ignored local `.streamlit/secrets.toml` contents in App settings → Secrets, resolving the setup state. No credentials are published in the repository. Missing settings now produce a readable setup message. The repository pins **pyarrow 24.0.0** to match the hosted platform's selection; the rebuilt local image passed **51 tests** after these changes.
