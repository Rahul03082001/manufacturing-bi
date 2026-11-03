"""Input controls. No production code reads the test-only scenario answers."""
import csv
import hashlib
import io
import json
from datetime import date, datetime
from pathlib import Path
import pandas as pd
from src.generate import FIELDS

INTEGER_FIELDS = {'unit_cost_cents', 'ordered_qty', 'quantity_delta', 'amount_cents'}
DATE_FIELDS = {'promised_date', 'posting_date'}
MAX_INTEGER = 1_000_000_000  # Documented MVP safety bound; SQL aggregates use bigint.


class Rejected(Exception):
    pass


class Checks:
    def __init__(self):
        self.results = []

    def check(self, name, errors=None, **details):
        errors = errors or []
        self.results.append({'control': name, 'passed': not errors, 'details': {**details, 'errors': errors[:20]}})
        if errors:
            raise Rejected(name)


def load_delivery(path, checks):
    """Verify delivered bytes/counts before parsing values; return observed evidence."""
    path = Path(path)
    files, frames = [], {}
    try:
        manifest = json.loads((path / 'manifest.json').read_text())
        start, end = date.fromisoformat(manifest['start_date']), date.fromisoformat(manifest['end_date'])
        assert start <= end and (end-start).days < 366
        assert set(manifest['files']) == {f'{name}.csv' for name in FIELDS}
    except (OSError, ValueError, KeyError, AssertionError, TypeError):
        checks.check('source_delivery', ['Missing/invalid manifest, date range (maximum 366 days), or file list'])
    errors = []
    for name in FIELDS:
        filename = f'{name}.csv'
        try:
            content = (path / filename).read_bytes()
            rows = list(csv.reader(io.StringIO(content.decode('utf-8'))))
            actual = {'filename': filename, 'row_count': max(len(rows)-1,0), 'sha256': hashlib.sha256(content).hexdigest()}
            files.append(actual)
            expected = manifest['files'][filename]
            if actual['row_count'] != expected['row_count'] or actual['sha256'] != expected['sha256']:
                errors.append(f'{filename}: delivered count/hash differs from manifest')
            # Keep strings intact: no floats, no silent "NA" null conversion, no ID coercion.
            frames[name] = pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False)
            if not rows or rows[0] != FIELDS[name] or any(len(r) != len(FIELDS[name]) for r in rows):
                errors.append(f'{filename}: header/order or row width invalid')
        except (OSError, ValueError, KeyError, UnicodeError, pd.errors.ParserError):
            errors.append(f'{filename}: unreadable or malformed delivery')
    # Attach observed files even when delivery fails.
    checks.files = files
    checks.check('source_delivery', errors, files_observed=len(files))
    return frames, start, end


def validate(frames, start, end, checks):
    errors = []
    for name, frame in frames.items():
        if list(frame.columns) != FIELDS[name]:
            errors.append(f'{name}: missing or unexpected columns')
            continue
        if frame.empty and name in {'items', 'suppliers', 'purchase_order_lines', 'inventory_movements'}:
            errors.append(f'{name}: required source is empty')
        for col in frame:
            nullable = name == 'inventory_movements' and col == 'po_line_id'
            if not nullable and frame[col].str.strip().eq('').any():
                errors.append(f'{name}.{col}: null/blank required value')
            try:
                if col in INTEGER_FIELDS:
                    if not frame[col].str.fullmatch(r'-?\d+').all():
                        raise ValueError()
                    values = frame[col].map(int)
                    if values.abs().gt(MAX_INTEGER).any():
                        raise ValueError()
                    frame[col] = values.astype('int64')
                elif col in DATE_FIELDS:
                    frame[col] = frame[col].map(date.fromisoformat)
                elif col == 'event_time':
                    frame[col] = frame[col].map(datetime.fromisoformat)
                    if any(v.tzinfo is not None for v in frame[col]):
                        raise ValueError()
            except (ValueError, OverflowError, TypeError):
                errors.append(f'{name}.{col}: invalid type or outside supported bounds')
    checks.check('schema_validity', errors)
    errors = []
    for name, frame in frames.items():
        key = FIELDS[name][0]
        duplicates = frame.loc[frame.duplicated(key, keep=False), key].tolist()
        if duplicates:
            errors.append(f'{name}.{key}: duplicate IDs {duplicates[:5]}')
    finance = frames['finance_entries']
    if finance['movement_id'].duplicated().any():
        errors.append('finance_entries: duplicate posting for movement_id')
    checks.check('business_key_uniqueness', errors)
    items, suppliers, po, mov = (frames[n] for n in ['items','suppliers','purchase_order_lines','inventory_movements'])
    errors = []
    for child, col, parent, key in [(po,'item_id',items,'item_id'),(po,'supplier_id',suppliers,'supplier_id'),
                                    (mov,'item_id',items,'item_id'),(finance,'movement_id',mov,'movement_id')]:
        bad = child.loc[~child[col].isin(parent[key]), col].tolist()
        if bad:
            errors.append(f'{col}: unknown relationship IDs {bad[:5]}')
    receipts = mov[mov.movement_type == 'RECEIPT']
    po_items = po.set_index('po_line_id')['item_id']
    invalid = receipts[receipts.po_line_id.map(po_items) != receipts.item_id]
    if len(invalid):
        errors.append(f'Receipt PO missing or item mismatch: {invalid.movement_id.head().tolist()}')
    checks.check('relationships', errors)
    errors = []
    if not items.currency.eq('USD').all() or (items.unit_cost_cents <= 0).any():
        errors.append('Items require USD and positive fixed standard costs')
    if (po.ordered_qty <= 0).any():
        errors.append('PO ordered quantity must be positive')
    good = ((mov.movement_type == 'RECEIPT') & (mov.quantity_delta > 0) & mov.po_line_id.ne('')) | (
        (mov.movement_type == 'PRODUCTION_ISSUE') & (mov.quantity_delta < 0) & mov.po_line_id.eq(''))
    if not good.all():
        errors.append('Invalid movement type/sign/PO combination')
    if not finance.account_code.eq('1400').all():
        errors.append('Only inventory control account 1400 is supported')
    for values, label in [(mov.event_time.map(lambda d:d.date()), 'event_time'), (finance.posting_date, 'posting_date')]:
        if any(not start <= d <= end for d in values):
            errors.append(f'{label} outside declared reporting period')
    checks.check('business_rules', errors)
    mov.loc[mov.po_line_id.eq(''), 'po_line_id'] = None
