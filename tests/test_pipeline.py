from sqlalchemy import text
from src.generate import generate


def test_same_seed_same_bytes(tmp_path):
    generate(tmp_path/'a', seed=99)
    generate(tmp_path/'b', seed=99)
    for file in (tmp_path/'a').rglob('*'):
        if file.is_file():
            assert file.read_bytes() == (tmp_path/'b'/file.relative_to(tmp_path/'a')).read_bytes()


def test_hand_calculated_fixture(process, tiny, db):
    result = process(tiny)
    assert result['outcome'] == 'SUCCESS', result
    with db.connect() as conn:
        inventory = conn.execute(text('SELECT closing_qty,inventory_value_cents FROM reporting.inventory ORDER BY day')).all()
        assert inventory == [(10,25000),(7,17500),(7,17500)]
        reconciliation = conn.execute(text('SELECT inventory_value_cents,finance_balance_cents,difference_cents FROM reporting.reconciliation ORDER BY day')).all()
        assert reconciliation == [(25000,25000,0),(17500,17500,0),(17500,17500,0)]


def test_clean_publish(process, datasets, db):
    result = process(datasets/'clean')
    assert result['outcome'] == 'SUCCESS', result
    with db.connect() as conn:
        assert conn.execute(text('SELECT count(*) FROM reporting.inventory')).scalar_one() == 600
        assert conn.execute(text('SELECT count(*) FROM reporting.reconciliation WHERE difference_cents<>0')).scalar_one() == 0


def published(conn):
    pointer = conn.execute(text('SELECT run_id FROM reporting.publication')).scalar_one()
    rows = conn.execute(text('SELECT day,item_id,closing_qty,inventory_value_cents FROM reporting.inventory ORDER BY day,item_id')).all()
    return pointer, rows


def test_identical_rerun_is_idempotent(process, datasets, db):
    first = process(datasets/'clean')
    with db.connect() as conn:
        old_id, old_rows = published(conn)
    second = process(datasets/'clean')
    assert first['run_id'] != second['run_id']
    assert second['outcome'] == 'SUCCESS'
    with db.connect() as conn:
        new_id, new_rows = published(conn)
        assert old_id != new_id
        assert old_rows == new_rows
        assert conn.execute(text('SELECT count(*)=count(DISTINCT (day,item_id)) FROM reporting.inventory')).scalar_one()


import pytest


@pytest.mark.parametrize('scenario,control', [
    ('duplicate_movement','business_key_uniqueness'), ('unknown_item','relationships'),
    ('missing_finance','reconciliation'), ('negative_inventory','negative_inventory'),
])
def test_fault_preserves_publication_and_recovers(process, datasets, db, scenario, control):
    assert process(datasets/'clean')['outcome'] == 'SUCCESS'
    with db.connect() as conn:
        before = published(conn)
    result = process(datasets/scenario)
    assert result['outcome'] == 'FAILED'
    assert [c['control'] for c in result['checks'] if not c['passed']] == [control]
    with db.connect() as conn:
        assert published(conn) == before
        assert conn.execute(text('SELECT latest_outcome FROM reporting.status')).scalar_one() == 'FAILED'
        assert conn.execute(text('SELECT count(*) FROM audit.files WHERE run_id=:id'), {'id':result['run_id']}).scalar_one() == 5
    assert process(datasets/'clean')['outcome'] == 'SUCCESS'
    with db.connect() as conn:
        after = published(conn)
    assert after[0] != before[0]
    assert after[1] == before[1]


def test_missing_finance_exact_difference(process, tiny, db):
    import csv
    from src.generate import FIELDS, write_dataset
    tables = {}
    for name in FIELDS:
        with (tiny/f'{name}.csv').open() as f:
            tables[name] = list(csv.DictReader(f))
    tables['finance_entries'].pop(1)  # Omit known -$75 issue posting.
    write_dataset(tiny,tables,'2026-01-01','2026-01-03')
    result = process(tiny)
    assert result['outcome'] == 'FAILED'
    with db.connect() as conn:
        rows = conn.execute(text('SELECT difference_cents FROM candidate.reconciliation WHERE run_id=:id ORDER BY day'), {'id':result['run_id']}).scalars().all()
    assert rows == [0,-7500,-7500]


def test_publication_rollback(process, tiny, db):
    process(tiny)
    with db.connect() as conn:
        before = published(conn)
        conn.rollback()
        with pytest.raises(RuntimeError):
            with conn.begin():
                conn.execute(text("UPDATE reporting.publication SET published_at='2000-01-01'"))
                raise RuntimeError('simulate transaction interruption')
        assert published(conn) == before
        assert conn.execute(text("SELECT published_at>'2000-01-02' FROM reporting.publication")).scalar_one()


def test_repeatable_read_pins_dashboard_snapshot(process, tiny, datasets, db):
    process(tiny)
    with db.connect().execution_options(isolation_level='REPEATABLE READ') as reader:
        with reader.begin():
            before = published(reader)
            assert process(datasets/'clean')['outcome'] == 'SUCCESS'
            assert published(reader) == before
    with db.connect() as conn:
        assert published(conn)[0] != before[0]


def test_database_rejects_publication_of_failed_run(process, tiny, datasets, db):
    from sqlalchemy.exc import DBAPIError
    process(tiny)
    failure = process(datasets/'missing_finance')
    with db.connect() as conn:
        before = published(conn)
    with db.begin() as conn, pytest.raises(DBAPIError) as error:
        conn.execute(text('UPDATE reporting.publication SET run_id=:id'), {'id':failure['run_id']})
    assert error.value.orig.sqlstate == '23514'
    with db.connect() as conn:
        assert published(conn) == before


def test_database_business_key_constraint(process, tiny, db):
    from sqlalchemy.exc import DBAPIError
    result = process(tiny)
    with db.begin() as conn, pytest.raises(DBAPIError) as error:
        conn.execute(text('INSERT INTO candidate.items SELECT * FROM candidate.items WHERE run_id=:id'), {'id':result['run_id']})
    assert error.value.orig.sqlstate == '23505'
