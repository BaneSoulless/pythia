"""add_monthly_target_log

Revision ID: 45ca5126f62c
Revises: a1b2c3d4e5f6
Create Date: 2026-04-15 03:36:43.996949
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '45ca5126f62c'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "monthly_target_log",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("year_month", sa.String(7), nullable=False),  # "2026-04"
        sa.Column("initial_capital", sa.Numeric(18,8), nullable=False),
        sa.Column("current_capital", sa.Numeric(18,8), nullable=False),
        sa.Column("target_return_pct", sa.Numeric(6,4), default=0.10),
        sa.Column("actual_return_pct", sa.Numeric(10,6), nullable=True),
        sa.Column("run_rate_pct", sa.Numeric(10,6), nullable=True),
        sa.Column("status", sa.String(20), default="on_track"),
        sa.Column("total_trades", sa.Integer, default=0),
        sa.Column("kelly_factor", sa.Numeric(8,6), nullable=True),
        sa.Column("sizing_mode", sa.String(20), default="half_kelly"),
        sa.Column("is_paper", sa.Boolean, default=True),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_monthly_target_year_month",
        "monthly_target_log",
        ["year_month", "is_paper"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("monthly_target_log")
