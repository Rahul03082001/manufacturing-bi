import os
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from src.db import engine


@pytest.mark.parametrize('statement', [
    'SELECT * FROM raw.records', 'SELECT * FROM candidate.items', 'SELECT * FROM audit.runs',
    'SELECT * FROM reporting.publication', "UPDATE reporting.publication SET published_at=now()",
    "DELETE FROM reporting.inventory", "INSERT INTO candidate.items(run_id,item_id) VALUES (gen_random_uuid(),'X')",
])
def test_reporter_denied(db, statement):
    reporter = engine('reporter', os.environ['REPORTER_PASSWORD'])
    try:
        with reporter.begin() as conn, pytest.raises(DBAPIError) as error:
            conn.execute(text(statement))
        assert error.value.orig.sqlstate in ({'55000'} if statement == 'DELETE FROM reporting.inventory' else {'42501'})
    finally:
        reporter.dispose()


def test_reporter_allowed_approved_views(db):
    reporter = engine('reporter', os.environ['REPORTER_PASSWORD'])
    try:
        with reporter.connect() as conn:
            for name in ['inventory','daily_summary','reconciliation','status','recent_failures']:
                conn.execute(text(f'SELECT * FROM reporting.{name}')).all()
            assert conn.execute(text("SELECT NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole FROM pg_roles WHERE rolname=current_user")).scalar_one()
    finally:
        reporter.dispose()


@pytest.mark.parametrize('table', ['runs','files','checks','outcomes'])
@pytest.mark.parametrize('operation', ['DELETE FROM','UPDATE','TRUNCATE'])
def test_pipeline_cannot_alter_audit(db, table, operation):
    statement = f'{operation} audit.{table}'
    if operation == 'UPDATE':
        statement += ' SET run_id=run_id'
    with db.begin() as conn, pytest.raises(DBAPIError) as error:
        conn.execute(text(statement))
    assert error.value.orig.sqlstate == '42501'


def test_reporter_has_no_view_write_privileges(db):
    reporter = engine('reporter', os.environ['REPORTER_PASSWORD'])
    with reporter.connect() as conn:
        for view in ['inventory','daily_summary','reconciliation','status','recent_failures']:
            for privilege in ['INSERT','UPDATE','DELETE','TRUNCATE']:
                assert not conn.execute(text('SELECT has_table_privilege(current_user,:view,:privilege)'),
                                        {'view':f'reporting.{view}','privilege':privilege}).scalar_one()
    reporter.dispose()
