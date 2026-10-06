"""accounts: users, sessions, invites, and an owner for every piece of personal data

Everything that existed before accounts (books, vocabulary, settings, saved API keys, AI
usage) is given to the local user, id 1, so a self-hosted install keeps working unchanged.
Caches (dictionary, translations, audio) stay shared: they hold no personal data.

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

LOCAL = 1


def upgrade() -> None:
    users = op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("password_hash", sa.String(length=200), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.bulk_insert(users, [{"id": LOCAL, "email": None, "password_hash": None, "name": "", "is_admin": True}])
    if op.get_bind().dialect.name == "postgresql":  # the next account gets id 2
        op.execute("SELECT setval(pg_get_serial_sequence('users', 'id'), 1)")

    op.create_table(
        "auth_sessions",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_auth_sessions_user", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("token_hash"),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_table(
        "invites",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("note", sa.String(length=200), nullable=False),
        sa.Column("used_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_invites_created_by", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["used_by"], ["users.id"], name="fk_invites_used_by", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("code"),
    )

    # Owned data: existing rows go to the local user, then the default is dropped so new rows
    # always say whose they are.
    for table, ondelete in (("books", "CASCADE"), ("terms", "CASCADE"), ("settings", "CASCADE"), ("api_keys", "CASCADE")):
        op.add_column(table, sa.Column("user_id", sa.Integer(), nullable=False, server_default=str(LOCAL)))
        op.alter_column(table, "user_id", server_default=None)
        op.create_foreign_key(f"fk_{table}_user", table, "users", ["user_id"], ["id"], ondelete=ondelete)
    op.create_index("ix_books_user_id", "books", ["user_id"])
    op.create_index("ix_terms_user_id", "terms", ["user_id"])

    op.add_column("ai_usage", sa.Column("user_id", sa.Integer(), nullable=True))
    op.execute(f"UPDATE ai_usage SET user_id = {LOCAL}")
    op.create_foreign_key("fk_ai_usage_user", "ai_usage", "users", ["user_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_ai_usage_user_id", "ai_usage", ["user_id"])

    # A word is unique per reader, not globally; settings and keys are per reader too.
    op.drop_constraint("terms_language_key_key", "terms", type_="unique")
    op.create_unique_constraint("uq_terms_user_language_key", "terms", ["user_id", "language", "key"])
    op.drop_constraint("settings_pkey", "settings", type_="primary")
    op.create_primary_key("settings_pkey", "settings", ["user_id", "key"])
    op.drop_constraint("api_keys_pkey", "api_keys", type_="primary")
    op.create_primary_key("api_keys_pkey", "api_keys", ["user_id", "provider"])


def downgrade() -> None:
    # Only the local user's data fits the single-user schema.
    for table in ("books", "terms", "settings", "api_keys"):
        op.execute(f"DELETE FROM {table} WHERE user_id <> {LOCAL}")
    op.drop_constraint("api_keys_pkey", "api_keys", type_="primary")
    op.create_primary_key("api_keys_pkey", "api_keys", ["provider"])
    op.drop_constraint("settings_pkey", "settings", type_="primary")
    op.create_primary_key("settings_pkey", "settings", ["key"])
    op.drop_constraint("uq_terms_user_language_key", "terms", type_="unique")
    op.create_unique_constraint("terms_language_key_key", "terms", ["language", "key"])
    op.drop_index("ix_ai_usage_user_id", table_name="ai_usage")
    op.drop_constraint("fk_ai_usage_user", "ai_usage", type_="foreignkey")
    op.drop_column("ai_usage", "user_id")
    op.drop_index("ix_terms_user_id", table_name="terms")
    op.drop_index("ix_books_user_id", table_name="books")
    for table in ("books", "terms", "settings", "api_keys"):
        op.drop_constraint(f"fk_{table}_user", table, type_="foreignkey")
        op.drop_column(table, "user_id")
    op.drop_table("invites")
    op.drop_index("ix_auth_sessions_user_id", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_table("users")
