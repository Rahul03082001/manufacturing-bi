"""Connection options and cloud entry-point checks; database tests stay local."""
import os
from pathlib import Path
from streamlit.testing.v1 import AppTest
from src.db import engine


def test_remote_connection_options(monkeypatch):
    monkeypatch.setenv('DB_HOST', 'db.example.invalid')
    monkeypatch.setenv('DB_PORT', '6543')
    monkeypatch.setenv('DB_SSLMODE', 'verify-full')
    monkeypatch.setenv('DB_SSLROOTCERT', '/etc/ssl/certs/ca-certificates.crt')
    db = engine()
    try:
        assert db.url.host == 'db.example.invalid'
        assert db.url.port == 6543
        assert db.url.query['sslmode'] == 'verify-full'
        assert db.url.query['sslrootcert'] == '/etc/ssl/certs/ca-certificates.crt'
        assert db.url.query['connect_timeout'] == '15'
    finally:
        db.dispose()


def test_cloud_entrypoint_rerenders(monkeypatch, process, tiny):
    process(tiny)
    monkeypatch.setenv('DB_USER', 'reporter')
    monkeypatch.setenv('DB_PASSWORD', os.environ['REPORTER_PASSWORD'])
    # The root entry point is copied into the shared image at build time.
    assert Path('streamlit_app.py').exists()
    app = AppTest.from_file('streamlit_app.py').run(timeout=20)
    assert not app.error and not app.exception
    assert app.metric[0].value == '$175.00'
    app.button[0].click().run()
    assert not app.error and not app.exception
    assert app.metric[0].value == '$175.00'
