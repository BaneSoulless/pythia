"""create evolution_runs table

Revision ID: c67d8e21092b
Revises: b504e529187a
Create Date: 2026-04-15 04:15:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c67d8e21092b'
down_revision = 'b504e529187a'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'evolution_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('triggered_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('trigger_reason', sa.String(length=255), nullable=True),
        sa.Column('warmstart_path', sa.String(length=512), nullable=True),
        sa.Column('trade_count_at_trigger', sa.Integer(), nullable=True),
        sa.Column('monthly_return_at_trigger', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='triggered', nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('evolution_runs')
