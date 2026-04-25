"""add email column to users

Revision ID: add_users_email_column
Revises: 4cc7f9f6d5a1
Create Date: 2026-04-25
"""

import sqlalchemy as sa
from alembic import op

revision = "add_users_email_column"
down_revision = "4cc7f9f6d5a1"
branch_labels = None
depends_on = None


def upgrade():
    # Add column (nullable first to avoid breaking existing rows)
    op.add_column("users", sa.Column("email", sa.String(length=255), nullable=True))

    # Backfill for existing data safety
    op.execute("""
        UPDATE users
        SET email = CONCAT(username, '@placeholder.com')
        WHERE email IS NULL OR email = ''
    """)

    # Enforce NOT NULL after backfill
    op.alter_column("users", "email", nullable=False, existing_type=sa.String(length=255))

    # Add unique constraint
    op.create_unique_constraint("uq_users_email", "users", ["email"])


def downgrade():
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.drop_column("users", "email")
