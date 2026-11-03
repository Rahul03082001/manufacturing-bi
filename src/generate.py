"""Deterministic synthetic history, independently exported inventory and finance."""
import argparse
import copy
import csv
import hashlib
import json
import random
from datetime import date, datetime, time, timedelta
from pathlib import Path

FIELDS = {
    'items': ['item_id', 'item_name', 'unit_cost_cents', 'currency'],
    'suppliers': ['supplier_id', 'supplier_name'],
    'purchase_order_lines': ['po_line_id', 'supplier_id', 'item_id', 'ordered_qty', 'promised_date'],
    'inventory_movements': ['movement_id', 'item_id', 'event_time', 'movement_type', 'quantity_delta', 'po_line_id'],
    'finance_entries': ['entry_id', 'movement_id', 'posting_date', 'account_code', 'amount_cents'],
}
NAMES = ['CPU', 'Memory module', 'Motherboard', 'Power supply', 'SSD', 'Cooling fan',
         'Heat sink', 'Network card', 'Chassis', 'Backplane', 'RAID controller',
         'Riser card', 'Cable harness', 'SATA cable', 'Mounting rail', 'Front panel',
         'Battery', 'Optical module', 'GPU', 'Drive tray']


def write_dataset(path, tables, start, end):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, fields in FIELDS.items():
        file = path / f'{name}.csv'
        with file.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
            writer.writeheader()
            writer.writerows(tables[name])
        files[file.name] = {'row_count': len(tables[name]), 'sha256': hashlib.sha256(file.read_bytes()).hexdigest()}
    manifest = {'start_date': str(start), 'end_date': str(end), 'files': files}
    (path / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')


def generate(root='data', seed=42, start='2026-01-01', days=30, items=20, suppliers=5, po_lines=100, movements=1000):
    if days < 2 or items < 1 or suppliers < 1 or po_lines < items or movements < po_lines:
        raise ValueError('Need days>=2, items/suppliers>=1, PO lines>=items, movements>=PO lines')
    rng = random.Random(seed)
    start = date.fromisoformat(start)
    end = start + timedelta(days=days - 1)
    tables = {name: [] for name in FIELDS}
    for i in range(items):
        tables['items'].append(dict(item_id=f'I{i+1:03}', item_name=NAMES[i % len(NAMES)] + (f' {i+1}' if i >= 20 else ''),
                                    unit_cost_cents=rng.randint(5, 500) * 100, currency='USD'))
    for i in range(suppliers):
        tables['suppliers'].append(dict(supplier_id=f'S{i+1:03}', supplier_name=f'Component supplier {i+1}'))
    history = []
    # All PO receipts precede consumption; reserve enough stock for every generated issue.
    stock = {row['item_id']: 0 for row in tables['items']}
    receipt_qty = max(100, movements * 10 // po_lines + 10)
    for i in range(po_lines):
        item = tables['items'][i % items]['item_id']
        po = f'PO{i+1:04}'
        tables['purchase_order_lines'].append(dict(po_line_id=po, supplier_id=f'S{rng.randrange(suppliers)+1:03}',
              item_id=item, ordered_qty=receipt_qty, promised_date=str(start)))
        history.append(dict(movement_id=f'M{i+1:06}', item_id=item,
              event_time=datetime.combine(start, time(8)) + timedelta(seconds=i),
              movement_type='RECEIPT', quantity_delta=receipt_qty, po_line_id=po))
        stock[item] += receipt_qty
    issue_count = movements - po_lines
    for i in range(issue_count):
        available = [item for item, qty in stock.items() if qty > 0]
        item = rng.choice(available)
        qty = rng.randint(1, min(10, stock[item]))
        day = 1 + i * (days - 1) // max(issue_count, 1)
        history.append(dict(movement_id=f'M{len(history)+1:06}', item_id=item,
              event_time=datetime.combine(start + timedelta(days=day), time(9)) + timedelta(seconds=i),
              movement_type='PRODUCTION_ISSUE', quantity_delta=-qty, po_line_id=''))
        stock[item] -= qty
    costs = {row['item_id']: row['unit_cost_cents'] for row in tables['items']}
    # Separate exports both read the immutable event history, never a reporting mart.
    tables['inventory_movements'] = [{**event, 'event_time': event['event_time'].isoformat()} for event in history]
    tables['finance_entries'] = [dict(entry_id=f'F{i+1:06}', movement_id=event['movement_id'],
        posting_date=str(event['event_time'].date()), account_code='1400',
        amount_cents=event['quantity_delta'] * costs[event['item_id']]) for i, event in enumerate(history)]
    write_dataset(Path(root) / 'clean', tables, start, end)
    expected = {}
    for scenario in ['duplicate_movement', 'unknown_item', 'missing_finance', 'negative_inventory']:
        changed = copy.deepcopy(tables)
        if scenario == 'duplicate_movement':
            record = changed['inventory_movements'][0]
            changed['inventory_movements'].append(record.copy())
            control = 'business_key_uniqueness'
        elif scenario == 'unknown_item':
            record = changed['inventory_movements'][0]
            record['item_id'] = 'UNKNOWN'
            control = 'relationships'
        elif scenario == 'missing_finance':
            record = changed['finance_entries'].pop(0)
            control = 'reconciliation'
        else:
            record = next((r for r in changed['inventory_movements'] if r['movement_type'] == 'PRODUCTION_ISSUE'), None)
            if record is None:
                continue
            record['quantity_delta'] = -receipt_qty * po_lines - 1
            control = 'negative_inventory'
        write_dataset(Path(root) / scenario, changed, start, end)
        expected[scenario] = {'record_id': record.get('movement_id'), 'expected_control': control}
    (Path(root) / 'test_only_faults.json').write_text(json.dumps(expected, indent=2) + '\n')
    return tables


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='data')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--start', default='2026-01-01')
    for name, default in [('days',30),('items',20),('suppliers',5),('po-lines',100),('movements',1000)]:
        parser.add_argument(f'--{name}', type=int, default=default)
    args = vars(parser.parse_args())
    args['root'] = args.pop('output')
    generated = generate(**args)
    print('Generated clean data and independent fault scenarios:', {k:len(v) for k,v in generated.items()})
