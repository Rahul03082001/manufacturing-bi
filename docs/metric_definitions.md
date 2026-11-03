# Metric dictionary

All business calculations run in `sql/models.sql` or the dashboard's parameterized SELECTs over approved views. One fictional plant, USD, integer individual units, fixed standard costs, zero opening inventory. Reporting period is declared in each delivery manifest (default January 1–30, 2026). Event timestamps are timezone-free plant-local timestamps; cutoffs use their calendar date. Audit timestamps are UTC. Finance is inventory account **1400**, not a complete ledger.

| Metric | Formula and grain | Source / SQL model / approved view | Filters and cutoff | Consumer |
| --- | --- | --- | --- | --- |
| Running quantity | Sum quantity_delta through each event; run/item/event | inventory_movements → movement_balances | Order by event_time then movement_id; explicit ROWS window | Data quality analyst; negative-stock control |
| Running value (cents) | Sum quantity_delta × unit_cost_cents through event; run/item/event | movements + items → movement_balances | Same deterministic ordering | Inventory analyst |
| Closing quantity | Cumulative daily sum of quantity_delta; run/day/item | movements → calendar + daily_delta + closing → daily_balances → reporting.inventory | Full date/item spine carries stock through no-movement days; optional selected items and as-of day | Materials planner |
| Inventory value (cents) | Closing quantity × fixed unit_cost_cents; run/day/item; sum items for run/day/plant or selected item set | items + movements → daily_balances → reporting.inventory / daily_summary | Inventory tab uses selected items and as-of date; trend includes days through as-of | Plant controller |
| Components with positive stock | Count item rows where closing_qty > 0; run/day/selected item set | daily_balances → reporting.inventory (dashboard SQL aggregate); plant-wide equivalent in daily_summary | Same date and component selection as inventory card | Materials planner |
| Finance balance (cents) | Cumulative signed sum of amount_cents for account 1400; run/day/account | finance_entries → finance_daily + aligned → reconciliation → reporting.reconciliation | Entire plant; postings through selected date; zero on days without postings; no item filtering | Finance controller |
| Reconciliation difference (cents) | Inventory value − finance balance; run/day/account | Independently aggregated inventory and finance → reconciliation → reporting.reconciliation | Same daily cutoff, currency and scope; PASS exactly when difference = 0 | Finance controller / control reviewer |
| PO receipts (units) | Sum receipt quantity_delta by PO; run/PO line | purchase_order_lines LEFT JOIN inventory_movements → po_receipts | Complete candidate period; must not exceed ordered_qty | Pipeline control; no procurement dashboard |

Presentation divides cents by 100 only for currency strings and chart coordinates. No formatted dollar values feed back into calculations. A pass does not establish posting-level accounting completeness: offsetting errors can cancel at day/account grain. A failed candidate never supplies dashboard business metrics.

Run-status fields are operational metadata, not financial KPIs: published run/time comes from the publication pointer; latest outcome/time from the latest completed audit outcome; recent failures from the last 30 failed checks. In-progress attempts remain visible in audit.runs but are not described as completed attempts in the dashboard.
