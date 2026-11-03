-- All inputs are isolated by :run_id. One row per source movement.
INSERT INTO candidate.movement_balances
SELECT m.run_id,m.movement_id,m.item_id,m.event_time,m.quantity_delta,
 m.quantity_delta*i.unit_cost_cents,
 sum(m.quantity_delta) OVER w,
 sum(m.quantity_delta*i.unit_cost_cents) OVER w
FROM candidate.inventory_movements m
JOIN candidate.items i ON i.run_id=m.run_id AND i.item_id=m.item_id
WHERE m.run_id=:run_id
WINDOW w AS (PARTITION BY m.run_id,m.item_id ORDER BY m.event_time,m.movement_id ROWS UNBOUNDED PRECEDING);

-- A full item/date spine carries balances across days with no activity.
INSERT INTO candidate.daily_balances
WITH calendar AS (
 SELECT r.run_id,generate_series(r.start_date::timestamp,r.end_date::timestamp,interval '1 day')::date AS day
 FROM audit.runs r WHERE r.run_id=:run_id
), daily_delta AS (
 SELECT run_id,item_id,event_time::date AS day,sum(quantity_delta) AS qty
 FROM candidate.inventory_movements WHERE run_id=:run_id GROUP BY run_id,item_id,event_time::date
), closing AS (
 SELECT c.run_id,c.day,i.item_id,i.item_name,i.unit_cost_cents,
 sum(coalesce(d.qty,0)) OVER (PARTITION BY c.run_id,i.item_id ORDER BY c.day ROWS UNBOUNDED PRECEDING) AS qty
 FROM calendar c JOIN candidate.items i ON i.run_id=c.run_id
 LEFT JOIN daily_delta d ON d.run_id=c.run_id AND d.item_id=i.item_id AND d.day=c.day
)
SELECT run_id,day,item_id,item_name,qty,qty*unit_cost_cents FROM closing;

INSERT INTO candidate.po_receipts
SELECT p.run_id,p.po_line_id,p.ordered_qty,coalesce(sum(m.quantity_delta),0)
FROM candidate.purchase_order_lines p
LEFT JOIN candidate.inventory_movements m ON m.run_id=p.run_id AND m.po_line_id=p.po_line_id AND m.movement_type='RECEIPT'
WHERE p.run_id=:run_id GROUP BY p.run_id,p.po_line_id,p.ordered_qty;

-- Inventory and finance aggregate independently before joining at day/account grain.
INSERT INTO candidate.reconciliation
WITH inventory AS (
 SELECT run_id,day,sum(inventory_value_cents) AS value FROM candidate.daily_balances
 WHERE run_id=:run_id GROUP BY run_id,day
), finance_daily AS (
 SELECT run_id,posting_date AS day,sum(amount_cents) AS delta FROM candidate.finance_entries
 WHERE run_id=:run_id AND account_code='1400' GROUP BY run_id,posting_date
), aligned AS (
 SELECT i.run_id,i.day,i.value,
 sum(coalesce(f.delta,0)) OVER (PARTITION BY i.run_id ORDER BY i.day ROWS UNBOUNDED PRECEDING) AS finance
 FROM inventory i LEFT JOIN finance_daily f ON f.run_id=i.run_id AND f.day=i.day
)
SELECT run_id,day,'1400',value,finance,value-finance FROM aligned;
