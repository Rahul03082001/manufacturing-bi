# Manual lineage and row grains

Maintained by hand; no automatic column-lineage discovery. Update this file, the metric dictionary, SQL, and tests together when formulas change.

## Common ingestion path

`src.generate` creates clean event history and separately exports five CSVs. Finance export reads that history, never the inventory mart. `src.pipeline.run` copies received CSVs + manifest into `data/received/<run_id>/` before processing. `src.controls.load_delivery` checks actual bytes (SHA-256) and CSV row counts. pandas reads strings without converting IDs or literal `NA`; `validate` parses integers exactly, dates with ISO parsing, and plant-local timestamps. Required fields, relationships and business rules gate typed inserts.

`raw.records` preserves every successfully parsed delivered row as JSON, including original source IDs, filename, hash, source line number, load timestamp and run ID. Invalid deliveries remain on disk even if raw loading cannot proceed. Typed `candidate.*` tables preserve source IDs and run ID; join `(run_id, filename)` to `audit.files` or the source IDs in raw.records for file/hash/time provenance.

| CSV field(s) | Loaded fields | SQL expression/model | Approved view | Dashboard / control |
| --- | --- | --- | --- | --- |
| inventory_movements.item_id, movement_id, event_time, quantity_delta | candidate.inventory_movements same fields | sum(quantity_delta) OVER item ORDER BY event_time,movement_id → movement_balances.running_qty | Not exposed to reporter | Negative running stock check |
| items.unit_cost_cents + movements.quantity_delta | candidate.items.unit_cost_cents + candidate.inventory_movements.quantity_delta | quantity_delta × unit_cost_cents; running window → movement_balances | Not exposed | Candidate movement valuation |
| movements.event_time, item_id, quantity_delta | Same typed fields | event_time::date → daily_delta → calendar spine → cumulative qty → daily_balances.closing_qty | reporting.inventory | Units-on-hand table; selected date/component SQL filter |
| items.unit_cost_cents + daily closing_qty | candidate.items + daily_balances | qty × unit_cost_cents → inventory_value_cents; SQL sum across selected items | reporting.inventory; plant aggregate reporting.daily_summary | Closing inventory card, daily trend, item value table; Python dollars() or /100 for display only |
| items.item_id, item_name + movements.quantity_delta | candidate.items + daily_balances | count(*) FILTER (WHERE closing_qty>0) | reporting.inventory (filtered SELECT); reporting.daily_summary (plant) | Components with positive stock card; integer display |
| finance_entries.posting_date, amount_cents, account_code | candidate.finance_entries same fields | sum(amount_cents) by day/account → cumulative aligned.finance → reconciliation.finance_balance_cents | reporting.reconciliation | Finance card and daily detail; cents /100 display |
| Inventory and finance paths above | candidate.daily_balances + candidate.finance_entries | independently aggregate both facts; value − finance → reconciliation.difference_cents | reporting.reconciliation | Difference card, daily PASS/FAIL (=0) detail; plant-wide only |
| movements.po_line_id, quantity_delta + purchase_order_lines.ordered_qty | candidate.inventory_movements + candidate.purchase_order_lines | receipt-only LEFT JOIN + sum → po_receipts | Not exposed | Over-receipt check |
| Manifest bytes/counts and run/check execution | audit.runs/files/checks/outcomes | transactionally selected run + latest completed outcome + failed check subset | reporting.status, reporting.recent_failures | Published run/time; latest attempt/time/outcome; failure notice/detail |

## Physical grains

Every candidate grain includes run_id. Repeated snapshots intentionally retain historical rows across different runs.

| Table | Row grain / uniqueness |
| --- | --- |
| raw.records | run/source_filename/source_row (CSV line number, header excluded) |
| candidate.items | run/item_id |
| candidate.suppliers | run/supplier_id |
| candidate.purchase_order_lines | run/po_line_id |
| candidate.inventory_movements | run/movement_id |
| candidate.finance_entries | run/entry_id; also unique run/movement_id (one posting per movement if present) |
| candidate.movement_balances | run/movement_id |
| candidate.daily_balances | run/day/item_id |
| candidate.po_receipts | run/po_line_id |
| candidate.reconciliation | run/day/account_code |
| audit.runs | run_id, attempt start and declared period |
| audit.files | run/filename, observed rows/hash/load timestamp |
| audit.checks | run/control, pass/fail/details/check timestamp; stops at first failed control |
| audit.outcomes | run_id, terminal outcome/completion timestamp |
| reporting.publication | one singleton row selecting the approved run, absent before first success |

Approved business views join the singleton pointer. All dashboard reads use one read-only REPEATABLE READ transaction and filter the selected run ID, preventing mixed cards during a concurrent publication. Status views expose a narrow subset of audit data; reporter cannot access raw, candidate, full audit or the pointer table.
