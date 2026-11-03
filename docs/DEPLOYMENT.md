# Hosted deployment

The local Compose application and tests remain the reference implementation. Cloud preparation adds a root `streamlit_app.py` entry point, configurable port/TLS settings, ignored secret paths, and operator commands for a managed PostgreSQL database. These changes do not make a local URL publicly reachable. A verified hosted URL is recorded here only after deployment succeeds.

## Proposed free portfolio hosting

Use Streamlit Community Cloud for the UI and Neon PostgreSQL 16 for the database. Both offer free plans; idle services may sleep and usage limits apply. Free hosting has no uptime guarantee. These are proposed providers until the owner selects them and signs in. No paid plan is authorized by this document.

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
docker compose -f compose.cloud.yaml run --rm setup
# Build current code and load a separately validated hosted snapshot.
docker compose -f compose.cloud.yaml build pipeline
docker compose -f compose.cloud.yaml run --rm pipeline python -m src.generate
export GIT_SHA="$(git rev-parse HEAD)"
docker compose -f compose.cloud.yaml run --rm pipeline python -m src.pipeline --dataset data/clean
```

These are deployment instructions, not a claim that a remote database has already been initialized. Normal reruns use only the final pipeline command. The separate cloud operator Compose file starts no local database. Evidence and retained sources stay on the operator machine; database audit remains in the managed database. Hosted disaster recovery and external evidence storage remain deferred.

## Dashboard deployment

Select the GitHub repository, `main` branch, **streamlit_app.py**, and **Python 3.12**. Configure the seven root-level settings in `deploy/reporter-secrets.example.toml` using the hosted **reporter** password. Streamlit exposes root-level secrets as environment variables. The app must never receive owner or pipeline credentials. Keep TLS verification enabled and use a provider-supported certificate trust path.

Only the already-approved synthetic inventory and narrow status views are visible to visitors. There is no public upload, pipeline execution or database administration endpoint. Review repository visibility and app visibility separately; a private repository does not automatically make the hosted dashboard private.

After deploy, verify the real URL opens, the closing value agrees with the hosted database, differences are zero, and the reporter is denied raw reads/writes. Then set the repository homepage to the verified URL. GitHub Pages alone cannot run this Streamlit + PostgreSQL application.
