"""create users and transactions

Revision ID: 0001_create_users_transactions
Revises: 
Create Date: 2026-05-18 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_create_users_transactions"
down_revision = None
branch_labels = None
depend_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("monthly_allowance", sa.Float(), nullable=False),
        sa.Column("feeding_budget", sa.Float(), nullable=False),
        sa.Column("campus_zone", sa.String(length=255), nullable=True),
        sa.Column("dietary_pref", sa.String(length=255), nullable=True),
    )
    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("category", sa.String(length=255), nullable=False),
        sa.Column("vendor", sa.String(length=255), nullable=False),
        sa.Column("item", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("transactions")
    op.drop_table("users")
