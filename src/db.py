"""Credential-scoped database connections; URLs are never logged."""
import os
from sqlalchemy import URL, create_engine


def engine(user=None, password=None):
    # Local Compose uses an isolated network. Remote deployments can explicitly
    # require TLS and certificate verification without changing application code.
    options = {'connect_timeout': os.getenv('DB_CONNECT_TIMEOUT', '15')}
    if os.getenv('DB_SSLMODE'):
        options['sslmode'] = os.environ['DB_SSLMODE']
    if os.getenv('DB_SSLROOTCERT'):
        options['sslrootcert'] = os.environ['DB_SSLROOTCERT']
    return create_engine(URL.create(
        'postgresql+psycopg', username=user or os.environ['DB_USER'],
        password=password or os.environ['DB_PASSWORD'],
        host=os.getenv('DB_HOST', 'db'), port=int(os.getenv('DB_PORT', '5432')),
        database=os.getenv('DB_NAME', 'manufacturing'), query=options,
    ), pool_pre_ping=True, hide_parameters=True)
