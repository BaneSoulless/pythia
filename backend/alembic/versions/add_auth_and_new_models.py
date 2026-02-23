"""
Database Migration: Add User, Alert, and BacktestResult Models

Revision ID: add_auth_and_new_models
Revises: initial
Create Date: 2025-11-22 20:45:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'add_auth_and_new_models'
down_revision = None  # Change this if you have previous migrations
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema"""
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    
    # Create portfolios table (or alter if exists)
    portfolios_exists = op.get_bind().dialect.has_table(op.get_bind(), 'portfolios')
    
    if not portfolios_exists:
        op.create_table(
            'portfolios',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('balance', sa.Float(), nullable=False, default=10000.0),
            sa.Column('total_value', sa.Float(), nullable=False, default=10000.0),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_portfolios_id'), 'portfolios', ['id'], unique=False)
    else:
        # Add user_id column to existing portfolios table
        op.add_column('portfolios', sa.Column('user_id', sa.Integer(), nullable=True))
        op.create_foreign_key(None, 'portfolios', 'users', ['user_id'], ['id'])
    
    # Create or alter positions table
    positions_exists = op.get_bind().dialect.has_table(op.get_bind(), 'positions')
    
    if not positions_exists:
        op.create_table(
            'positions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('portfolio_id', sa.Integer(), nullable=True),
            sa.Column('symbol', sa.String(), nullable=False),
            sa.Column('quantity', sa.Float(), nullable=False),
            sa.Column('average_price', sa.Float(), nullable=False),
            sa.Column('current_price', sa.Float(), nullable=False),
            sa.Column('unrealized_pnl', sa.Float(), nullable=True, default=0.0),
            sa.Column('stop_loss_price', sa.Float(), nullable=True),
            sa.Column('take_profit_price', sa.Float(), nullable=True),
            sa.Column('entry_price', sa.Float(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_positions_id'), 'positions', ['id'], unique=False)
        op.create_index(op.f('ix_positions_symbol'), 'positions', ['symbol'], unique=False)
    else:
        # Add new columns to existing positions table
        op.add_column('positions', sa.Column('stop_loss_price', sa.Float(), nullable=True))
        op.add_column('positions', sa.Column('take_profit_price', sa.Float(), nullable=True))
        op.add_column('positions', sa.Column('entry_price', sa.Float(), nullable=True))
    
    # Create or check trades table
    trades_exists = op.get_bind().dialect.has_table(op.get_bind(), 'trades')
    
    if not trades_exists:
        op.create_table(
            'trades',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('portfolio_id', sa.Integer(), nullable=True),
            sa.Column('symbol', sa.String(), nullable=False),
            sa.Column('side', sa.String(), nullable=False),
            sa.Column('quantity', sa.Float(), nullable=False),
            sa.Column('price', sa.Float(), nullable=False),
            sa.Column('commission', sa.Float(), nullable=True, default=0.0),
            sa.Column('pnl', sa.Float(), nullable=True),
            sa.Column('ai_confidence', sa.Float(), nullable=True),
            sa.Column('strategy_used', sa.String(), nullable=True),
            sa.Column('timestamp', sa.DateTime(), nullable=True),
            sa.Column('executed_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_trades_id'), 'trades', ['id'], unique=False)
        op.create_index(op.f('ix_trades_symbol'), 'trades', ['symbol'], unique=False)
    
    # Create alerts table
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('level', sa.String(), nullable=False),
        sa.Column('data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('read', sa.Boolean(), nullable=True, default=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alerts_id'), 'alerts', ['id'], unique=False)
    
    # Create backtest_results table
    op.create_table(
        'backtest_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=False),
        sa.Column('strategy', sa.String(), nullable=False),
        sa.Column('initial_balance', sa.Float(), nullable=False),
        sa.Column('final_balance', sa.Float(), nullable=True),
        sa.Column('total_return', sa.Float(), nullable=True),
        sa.Column('total_return_pct', sa.Float(), nullable=True),
        sa.Column('num_trades', sa.Integer(), nullable=True),
        sa.Column('win_rate', sa.Float(), nullable=True),
        sa.Column('max_drawdown', sa.Float(), nullable=True),
        sa.Column('sharpe_ratio', sa.Float(), nullable=True),
        sa.Column('status', sa.String(), nullable=True, default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_backtest_results_id'), 'backtest_results', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade database schema"""
    op.drop_index(op.f('ix_backtest_results_id'), table_name='backtest_results')
    op.drop_table('backtest_results')
    
    op.drop_index(op.f('ix_alerts_id'), table_name='alerts')
    op.drop_table('alerts')
    
    # Only drop if we created, otherwise just remove columns
    try:
        op.drop_column('positions', 'entry_price')
        op.drop_column('positions', 'take_profit_price')
        op.drop_column('positions', 'stop_loss_price')
    except:
        pass
    
    try:
        op.drop_column('portfolios', 'user_id')
    except:
        pass
    
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
