import os
from pathlib import Path
import pytest
from src.db import engine
from src.generate import generate, write_dataset
from src.pipeline import run


@pytest.fixture(scope='session')
def db():
    # Never point destructive or isolated integration scenarios at the demo database.
    assert os.environ['DB_NAME'] == 'manufacturing_test'
    assert os.environ['DB_HOST'] == 'db-test'
    result = engine()
    yield result
    result.dispose()


@pytest.fixture(scope='session')
def datasets(tmp_path_factory):
    root = tmp_path_factory.mktemp('datasets')
    generate(root)
    return root


@pytest.fixture
def process(db, tmp_path):
    return lambda path: run(path, db, tmp_path/'evidence', tmp_path/'received')


@pytest.fixture
def tiny(tmp_path):
    # Hand-authored independent oracle: receipt 10*2500, issue -3*2500 => 17500.
    tables = {
        'items':[dict(item_id='A',item_name='Memory',unit_cost_cents=2500,currency='USD')],
        'suppliers':[dict(supplier_id='S',supplier_name='Supplier')],
        'purchase_order_lines':[dict(po_line_id='P',supplier_id='S',item_id='A',ordered_qty=10,promised_date='2026-01-01')],
        'inventory_movements':[
            dict(movement_id='M1',item_id='A',event_time='2026-01-01T08:00:00',movement_type='RECEIPT',quantity_delta=10,po_line_id='P'),
            dict(movement_id='M2',item_id='A',event_time='2026-01-02T09:00:00',movement_type='PRODUCTION_ISSUE',quantity_delta=-3,po_line_id='')],
        'finance_entries':[
            dict(entry_id='F1',movement_id='M1',posting_date='2026-01-01',account_code='1400',amount_cents=25000),
            dict(entry_id='F2',movement_id='M2',posting_date='2026-01-02',account_code='1400',amount_cents=-7500)],
    }
    path = tmp_path/'tiny'
    write_dataset(path,tables,'2026-01-01','2026-01-03')
    return path
