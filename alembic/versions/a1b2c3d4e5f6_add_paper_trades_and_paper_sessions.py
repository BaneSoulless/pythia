"""add_paper_trades_and_paper_positions_tables

Revision ID: a1b2c3d4e5f6
Revises: f513ae046911
Create Date: 2026-04-15
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "f513ae046911"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "paper_trades",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("side", sa.String(4), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 8), nullable=False),
        sa.Column("entry_price", sa.Numeric(18, 8), nullable=False),
        sa.Column("exit_price", sa.Numeric(18, 8), nullable=True),
        sa.Column("pnl", sa.Numeric(18, 8), nullable=True),
        sa.Column("pnl_pct", sa.Numeric(10, 6), nullable=True),
        sa.Column("is_win", sa.Boolean, nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("alpaca_order_id", sa.String(64), nullable=True),
        sa.Column("signal_scores", sa.Text, nullable=True),
        sa.Column("evolved_config_used", sa.Boolean, default=False),
        sa.Column("evolved_node_id", sa.String(16), nullable=True),
        sa.Column("session_id", sa.String(64), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_index("ix_paper_trades_symbol", "paper_trades", ["symbol"])
    op.create_index("ix_paper_trades_opened_at", "paper_trades", ["opened_at"])
    op.create_index("ix_paper_trades_session_id", "paper_trades", ["session_id"])

    op.create_table(
        "paper_sessions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("initial_capital", sa.Numeric(18, 8), nullable=False),
        sa.Column("current_capital", sa.Numeric(18, 8), nullable=False),
        sa.Column("total_trades", sa.Integer, default=0),
        sa.Column("win_trades", sa.Integer, default=0),
        sa.Column("total_pnl", sa.Numeric(18, 8), default=0),
        sa.Column("sharpe_ratio", sa.Numeric(10, 6), nullable=True),
        sa.Column("max_drawdown", sa.Numeric(10, 6), nullable=True),
        sa.Column("status", sa.String(20), default="active"),
        sa.Column("promote_eligible", sa.Boolean, default=False),
        sa.Column("promoted_to_live", sa.Boolean, default=False),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("config_node_id", sa.String(16), nullable=True),
        sa.Column("config_score", sa.Numeric(10, 6), nullable=True),
    )


def downgrade() -> None:
    op.drop_index("ix_paper_trades_session_id", table_name="paper_trades")
    op.drop_index("ix_paper_trades_opened_at", table_name="paper_trades")
    op.drop_index("ix_paper_trades_symbol", table_name="paper_trades")
    op.drop_table("paper_sessions")
    op.drop_table("paper_trades")
