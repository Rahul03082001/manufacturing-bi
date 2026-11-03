"""Full-snapshot processing. Exit 2 means a rejected candidate; last success is retained."""
import argparse
import json
import os
import re
import shutil
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4
from sqlalchemy import text
from src.controls import Checks, Rejected, load_delivery, validate
from src.db import engine
from src.generate import FIELDS


def sql(conn, statement, **params):
    return conn.execute(text(statement), params)


def record_checks(conn, run_id, results):
    for check in results:
        sql(conn, 'INSERT INTO audit.checks(run_id,control,passed,details) VALUES (:id,:control,:passed,CAST(:details AS jsonb))',
            id=run_id, control=check['control'], passed=check['passed'], details=json.dumps(check['details'], default=str))


def run(dataset, db=None, evidence_dir=None, received_dir=None):
    db = db or engine()
    run_id = str(uuid4())
    checks = Checks()
    checks.files = []
    dataset = Path(dataset)
    received = Path(received_dir or os.getenv('RECEIVED_DIR', 'data/received')) / run_id
    received.mkdir(parents=True)
    # Read subsequent inputs only from this retained copy, so a changed delivery cannot
    # change bytes between the manifest check and candidate ingestion.
    for name in [*(f'{n}.csv' for n in FIELDS), 'manifest.json']:
        if (dataset / name).is_file():
            shutil.copyfile(dataset / name, received / name)
    start = end = date(1970, 1, 1)
    try:
        manifest = json.loads((received / 'manifest.json').read_text())
        start, end = date.fromisoformat(manifest['start_date']), date.fromisoformat(manifest['end_date'])
    except (OSError, ValueError, KeyError, TypeError):
        pass
    git_sha = os.getenv('GIT_SHA', 'unknown')
    if not re.fullmatch('[0-9a-f]{40}', git_sha):
        git_sha = 'unknown'
    with db.begin() as conn:
        sql(conn, 'INSERT INTO audit.runs(run_id,dataset,git_sha,start_date,end_date) VALUES (:id,:dataset,:sha,:start,:end)',
            id=run_id, dataset=dataset.name, sha=git_sha, start=start, end=end)
    outcome = 'FAILED'
    try:
        frames, start, end = load_delivery(received, checks)
        with db.begin() as conn:
            for name, frame in frames.items():
                file = next(f for f in checks.files if f['filename'] == f'{name}.csv')
                rows = [{'id':run_id,'file':file['filename'],'hash':file['sha256'],'row':i+2,'payload':json.dumps(row)}
                        for i,row in enumerate(frame.to_dict('records'))]
                if rows:
                    conn.execute(text('INSERT INTO raw.records(run_id,source_filename,source_hash,source_row,payload) '
                        'VALUES (:id,:file,:hash,:row,CAST(:payload AS jsonb))'), rows)
        validate(frames, start, end, checks)
        with db.begin() as conn:
            for name, frame in frames.items():
                rows = [{'run_id':run_id,**row} for row in frame.to_dict('records')]
                columns = ['run_id', *FIELDS[name]]  # Constants, never source-provided SQL identifiers.
                if rows:
                    conn.execute(text(f"INSERT INTO candidate.{name} ({','.join(columns)}) VALUES ({','.join(':'+c for c in columns)})"), rows)
            for statement in Path('sql/models.sql').read_text().split(';'):
                if statement.strip():
                    conn.execute(text(statement), {'run_id':run_id})
        with db.connect() as conn:
            over = sql(conn, 'SELECT po_line_id,ordered_qty,received_qty FROM candidate.po_receipts '
                       'WHERE run_id=:id AND received_qty>ordered_qty', id=run_id).mappings().all()
            checks.check('receipt_quantities', [dict(r) for r in over])
            negative = sql(conn, 'SELECT movement_id,item_id,running_qty FROM candidate.movement_balances '
                           'WHERE run_id=:id AND running_qty<0 ORDER BY event_time,movement_id', id=run_id).mappings().all()
            checks.check('negative_inventory', [dict(r) for r in negative], violation_count=len(negative))
            diffs = sql(conn, 'SELECT day,inventory_value_cents,finance_balance_cents,difference_cents '
                        'FROM candidate.reconciliation WHERE run_id=:id AND difference_cents<>0 ORDER BY day', id=run_id).mappings().all()
            checks.check('reconciliation', [dict(r) for r in diffs], difference_days=len(diffs))
        outcome = 'SUCCESS'
    except Rejected:
        pass
    except Exception as exc:
        # Do not expose connection URLs, bind values, or credentials in evidence/UI.
        checks.results.append({'control':'processing_error','passed':False,
                               'details':{'errors':[f'Processing failed ({type(exc).__name__}); inspect retained inputs and server logs.']}})
    # Completion and publication are atomic. A failed attempt only appends evidence.
    with db.begin() as conn:
        for file in checks.files:
            sql(conn, 'INSERT INTO audit.files(run_id,filename,row_count,sha256) VALUES (:id,:filename,:row_count,:sha256)', id=run_id, **file)
        record_checks(conn, run_id, checks.results)
        sql(conn, 'INSERT INTO audit.outcomes(run_id,outcome) VALUES (:id,:outcome)', id=run_id, outcome=outcome)
        if outcome == 'SUCCESS':
            sql(conn, 'INSERT INTO reporting.publication(singleton,run_id) VALUES (true,:id) '
                'ON CONFLICT(singleton) DO UPDATE SET run_id=EXCLUDED.run_id,published_at=clock_timestamp()', id=run_id)
        timestamps = sql(conn, 'SELECT r.started_at,o.completed_at FROM audit.runs r '
                         'JOIN audit.outcomes o USING(run_id) WHERE run_id=:id', id=run_id).mappings().one()
    evidence = {'run_id':run_id,'outcome':outcome,'dataset':dataset.name,'git_sha':git_sha,
                **dict(timestamps),'files':checks.files,'checks':checks.results}
    destination = Path(evidence_dir or os.getenv('EVIDENCE_DIR', 'evidence'))
    destination.mkdir(parents=True, exist_ok=True)
    (destination / f'{run_id}.json').write_text(json.dumps(evidence, indent=2, default=str) + '\n')
    return evidence


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', default='data/clean')
    result = run(parser.parse_args().dataset)
    print(json.dumps({'run_id':result['run_id'],'outcome':result['outcome'],
        'failed_controls':[c['control'] for c in result['checks'] if not c['passed']]}))
    raise SystemExit(0 if result['outcome'] == 'SUCCESS' else 2)
