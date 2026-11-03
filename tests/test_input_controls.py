import csv
import pytest
from src.generate import FIELDS, write_dataset


@pytest.mark.parametrize('mutation,expected', [
    ('blank_key','schema_validity'), ('fractional_qty','schema_validity'),
    ('overflow','schema_validity'), ('bad_date','schema_validity'),
    ('po_mismatch','relationships'), ('supplier_orphan','relationships'),
    ('wrong_sign','business_rules'), ('wrong_account','business_rules'),
    ('outside_period','business_rules'), ('over_receipt','receipt_quantities'),
    ('missing_column','source_delivery'),
])
def test_input_rejections(process, tiny, mutation, expected):
    tables = {}
    for name in FIELDS:
        with (tiny/f'{name}.csv').open() as f:
            tables[name] = list(csv.DictReader(f))
    if mutation == 'blank_key':
        tables['inventory_movements'][0]['movement_id'] = ''
    elif mutation == 'fractional_qty':
        tables['inventory_movements'][0]['quantity_delta'] = '10.5'
    elif mutation == 'overflow':
        tables['inventory_movements'][0]['quantity_delta'] = '9223372036854775808'
    elif mutation == 'bad_date':
        tables['finance_entries'][0]['posting_date'] = 'yesterday'
    elif mutation == 'po_mismatch':
        tables['inventory_movements'][0]['po_line_id'] = 'OTHER'
    elif mutation == 'supplier_orphan':
        tables['purchase_order_lines'][0]['supplier_id'] = 'UNKNOWN'
    elif mutation == 'wrong_sign':
        tables['inventory_movements'][0]['quantity_delta'] = '-10'
    elif mutation == 'wrong_account':
        tables['finance_entries'][0]['account_code'] = '9999'
    elif mutation == 'outside_period':
        tables['finance_entries'][0]['posting_date'] = '2025-01-01'
    elif mutation == 'over_receipt':
        tables['purchase_order_lines'][0]['ordered_qty'] = '9'
    write_dataset(tiny,tables,'2026-01-01','2026-01-03')
    if mutation == 'missing_column':
        file = tiny/'items.csv'
        file.write_text('item_id\nA\n')
    result = process(tiny)
    assert result['outcome'] == 'FAILED'
    assert [c['control'] for c in result['checks'] if not c['passed']] == [expected]


def test_delivery_hash_mismatch(process, tiny):
    with (tiny/'items.csv').open('a') as f:
        f.write('B,Extra,100,USD\n')
    result = process(tiny)
    assert result['checks'][0]['control'] == 'source_delivery'
    assert not result['checks'][0]['passed']
