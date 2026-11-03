"""Read-only deployment smoke check using only the hosted reporter credential."""
import json
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from src.db import engine


def main():
    db = engine()
    try:
        with db.connect() as conn:
            assert conn.execute(text('SELECT current_user')).scalar_one() == 'reporter'
            result = conn.execute(text('SELECT * FROM reporting.reconciliation ORDER BY day DESC LIMIT 1')).mappings().one()
            assert conn.execute(text('SELECT bool_and(difference_cents=0) FROM reporting.reconciliation')).scalar_one()
            print(json.dumps(dict(result), default=str))
        for query in ['SELECT * FROM raw.records', 'SELECT * FROM candidate.items',
                      'UPDATE reporting.publication SET published_at=now()']:
            try:
                with db.begin() as conn:
                    conn.execute(text(query))
            except DBAPIError as error:
                assert error.orig.sqlstate == '42501'
            else:
                raise AssertionError('Reporter unexpectedly has a restricted permission')
        print('Hosted balances and denied raw/candidate reads and publication writes verified.')
    finally:
        db.dispose()


if __name__ == '__main__':
    main()
