"""add_sharpe_ratio_to_monthly_target_log

Revision ID: b504e529187a
Revises: 0477e9c502e1
Create Date: 2026-04-15 03:50:49

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = 'b504e529187a'
down_revision: Union[str, None] = '0477e9c502e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "monthly_target_log",
        sa.Column(
            "sharpe_ratio",
            sa.Numeric(10, 6),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("monthly_target_log", "sharpe_ratio")
