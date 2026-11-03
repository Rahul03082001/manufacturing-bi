"""Credential-scoped database connections; URLs are never logged."""
import os
from sqlalchemy import URL, create_engine


def engine(user=None, password=None):
    return create_engine(URL.create(
        'postgresql+psycopg', username=user or os.environ['DB_USER'],
        password=password or os.environ['DB_PASSWORD'],
        host=os.getenv('DB_HOST', 'db'), database=os.getenv('DB_NAME', 'manufacturing'),
    ), pool_pre_ping=True, hide_parameters=True)
