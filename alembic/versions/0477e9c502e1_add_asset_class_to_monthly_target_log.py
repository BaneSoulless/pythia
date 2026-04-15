"""add_asset_class_to_monthly_target_log

Revision ID: 0477e9c502e1
Revises: 45ca5126f62c
Create Date: 2026-04-15 03:42:39.792600
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '0477e9c502e1'
down_revision: Union[str, None] = '45ca5126f62c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "monthly_target_log",
        sa.Column("asset_class", sa.String(20), nullable=True,
                  server_default="CRYPTO"),
    )
    # Aggiorna unique constraint per includere asset_class
    op.drop_index("ix_monthly_target_year_month", "monthly_target_log")
    op.create_index(
        "ix_monthly_target_year_month",
        "monthly_target_log",
        ["year_month", "is_paper", "asset_class"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_monthly_target_year_month", "monthly_target_log")
    op.drop_column("monthly_target_log", "asset_class")
    op.create_index(
        "ix_monthly_target_year_month",
        "monthly_target_log",
        ["year_month", "is_paper"],
        unique=True,
    )
