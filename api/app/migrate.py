"""Bring the database schema up to date at startup.

Postgres goes through Alembic (api/migrations). A database created by glosa 0.1.0, before
migrations existed, has the baseline schema but no version table: it is stamped as the
baseline and then upgraded, so its data is kept. SQLite (the tests) is created directly.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.db import Base, SessionLocal, engine
from app.models import LOCAL_USER_ID, User

ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"


def _config(connection) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(ALEMBIC_INI.parent / "migrations"))
    config.attributes["connection"] = connection
    return config


def upgrade() -> None:
    if engine.dialect.name == "sqlite":
        Base.metadata.create_all(engine)
        with SessionLocal() as session:
            if session.get(User, LOCAL_USER_ID) is None:
                session.add(User(id=LOCAL_USER_ID, name="", is_admin=True))
                session.commit()
        return
    with engine.begin() as connection:
        tables = set(inspect(connection).get_table_names())
        config = _config(connection)
        if "alembic_version" not in tables and "books" in tables:
            command.stamp(config, "0001")  # a 0.1.0 database: baseline schema, no history
        command.upgrade(config, "head")
