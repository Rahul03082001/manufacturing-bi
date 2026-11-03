\set ON_ERROR_STOP on
\getenv pipeline_password PIPELINE_PASSWORD
\getenv reporter_password REPORTER_PASSWORD
CREATE ROLE pipeline LOGIN PASSWORD :'pipeline_password' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE reporter LOGIN PASSWORD :'reporter_password' NOSUPERUSER NOCREATEDB NOCREATEROLE;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
CREATE SCHEMA audit;
CREATE SCHEMA raw;
CREATE SCHEMA candidate;
CREATE SCHEMA reporting;
CREATE TABLE audit.runs (
 run_id uuid PRIMARY KEY, started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 dataset text NOT NULL, git_sha text NOT NULL, start_date date NOT NULL, end_date date NOT NULL
);
CREATE TABLE audit.files (
 run_id uuid REFERENCES audit.runs, filename text, row_count integer NOT NULL,
 sha256 text NOT NULL, loaded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(run_id, filename)
);
CREATE TABLE audit.checks (
 run_id uuid REFERENCES audit.runs, control text, passed boolean NOT NULL,
 details jsonb NOT NULL, checked_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(run_id, control)
);
CREATE TABLE audit.outcomes (
 run_id uuid PRIMARY KEY REFERENCES audit.runs, outcome text NOT NULL CHECK(outcome IN ('SUCCESS','FAILED')),
 completed_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE raw.records (
 run_id uuid REFERENCES audit.runs, source_filename text, source_row integer,
 source_hash text NOT NULL, loaded_at timestamptz NOT NULL DEFAULT clock_timestamp(), payload jsonb NOT NULL,
 PRIMARY KEY(run_id, source_filename, source_row)
);
CREATE TABLE candidate.items (
 run_id uuid REFERENCES audit.runs, item_id text, item_name text NOT NULL,
 unit_cost_cents bigint NOT NULL CHECK(unit_cost_cents > 0), currency text NOT NULL CHECK(currency='USD'),
 PRIMARY KEY(run_id,item_id)
);
CREATE TABLE candidate.suppliers (
 run_id uuid REFERENCES audit.runs, supplier_id text, supplier_name text NOT NULL, PRIMARY KEY(run_id,supplier_id)
);
CREATE TABLE candidate.purchase_order_lines (
 run_id uuid, po_line_id text, supplier_id text NOT NULL, item_id text NOT NULL,
 ordered_qty bigint NOT NULL CHECK(ordered_qty>0), promised_date date NOT NULL,
 PRIMARY KEY(run_id,po_line_id), FOREIGN KEY(run_id,item_id) REFERENCES candidate.items,
 FOREIGN KEY(run_id,supplier_id) REFERENCES candidate.suppliers
);
CREATE TABLE candidate.inventory_movements (
 run_id uuid, movement_id text, item_id text NOT NULL, event_time timestamp NOT NULL,
 movement_type text NOT NULL CHECK(movement_type IN ('RECEIPT','PRODUCTION_ISSUE')),
 quantity_delta bigint NOT NULL, po_line_id text,
 PRIMARY KEY(run_id,movement_id), FOREIGN KEY(run_id,item_id) REFERENCES candidate.items,
 FOREIGN KEY(run_id,po_line_id) REFERENCES candidate.purchase_order_lines,
 CHECK((movement_type='RECEIPT' AND quantity_delta>0 AND po_line_id IS NOT NULL) OR
       (movement_type='PRODUCTION_ISSUE' AND quantity_delta<0 AND po_line_id IS NULL))
);
CREATE TABLE candidate.finance_entries (
 run_id uuid, entry_id text, movement_id text NOT NULL, posting_date date NOT NULL,
 account_code text NOT NULL CHECK(account_code='1400'), amount_cents bigint NOT NULL,
 PRIMARY KEY(run_id,entry_id), UNIQUE(run_id,movement_id),
 FOREIGN KEY(run_id,movement_id) REFERENCES candidate.inventory_movements
);
CREATE TABLE candidate.movement_balances (
 run_id uuid, movement_id text, item_id text, event_time timestamp,
 quantity_delta bigint, movement_value_cents bigint, running_qty bigint, running_value_cents bigint,
 PRIMARY KEY(run_id,movement_id)
);
CREATE TABLE candidate.daily_balances (
 run_id uuid, day date, item_id text, item_name text,
 closing_qty bigint, inventory_value_cents bigint, PRIMARY KEY(run_id,day,item_id)
);
CREATE TABLE candidate.po_receipts (
 run_id uuid, po_line_id text, ordered_qty bigint, received_qty bigint, PRIMARY KEY(run_id,po_line_id)
);
CREATE TABLE candidate.reconciliation (
 run_id uuid, day date, account_code text, inventory_value_cents bigint,
 finance_balance_cents bigint, difference_cents bigint,
 PRIMARY KEY(run_id,day,account_code)
);
CREATE TABLE reporting.publication (
 singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
 run_id uuid REFERENCES audit.outcomes, published_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE VIEW reporting.inventory AS
 SELECT b.* FROM candidate.daily_balances b JOIN reporting.publication p USING(run_id);
CREATE VIEW reporting.daily_summary AS
 SELECT run_id, day, sum(inventory_value_cents)::bigint AS inventory_value_cents,
 count(*) FILTER (WHERE closing_qty>0) AS positive_stock_items
 FROM reporting.inventory GROUP BY run_id,day;
CREATE VIEW reporting.reconciliation AS
 SELECT r.* FROM candidate.reconciliation r JOIN reporting.publication p USING(run_id);
CREATE VIEW reporting.status AS
 SELECT p.run_id AS published_run_id,p.published_at,
 o.run_id AS latest_run_id,o.outcome AS latest_outcome,o.completed_at AS latest_completed_at
 FROM (SELECT 1) anchor
 LEFT JOIN reporting.publication p ON true
 LEFT JOIN LATERAL (SELECT * FROM audit.outcomes ORDER BY completed_at DESC,run_id DESC LIMIT 1) o ON true;
CREATE VIEW reporting.recent_failures AS
 SELECT c.run_id,c.control,c.details,c.checked_at
 FROM audit.checks c WHERE NOT c.passed ORDER BY c.checked_at DESC,c.run_id DESC LIMIT 30;
GRANT USAGE ON SCHEMA audit,raw,candidate,reporting TO pipeline;
GRANT SELECT,INSERT ON ALL TABLES IN SCHEMA audit,raw,candidate TO pipeline;
GRANT SELECT,INSERT,UPDATE ON reporting.publication TO pipeline;
GRANT SELECT ON ALL TABLES IN SCHEMA reporting TO pipeline;
GRANT USAGE ON SCHEMA reporting TO reporter;
GRANT SELECT ON reporting.inventory,reporting.daily_summary,reporting.reconciliation,reporting.status,reporting.recent_failures TO reporter;
