"""create users and transactions

Revision ID: 0001_create_users_transactions
Revises: 
Create Date: 2026-06-16 00:00:00.000000
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
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("monthly_allowance", sa.Float(), nullable=False),
        sa.Column("feeding_budget", sa.Float(), nullable=False),
        sa.Column("dietary_pref", sa.String(), nullable=True),
        sa.Column("allowance_period", sa.String(), nullable=False, server_default="monthly"),
        sa.Column("meals_per_day", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("meal_times", postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.PrimaryKeyConstraint("email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_email", sa.String(), nullable=False),
        sa.Column("date", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("vendor", sa.String(), nullable=False),
        sa.Column("item", sa.String(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["user_email"], ["users.email"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_transactions_user_email"), "transactions", ["user_email"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_transactions_user_email"), table_name="transactions")
    op.drop_table("transactions")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
