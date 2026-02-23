export interface Portfolio {
    id: number;
    balance: number;
    total_value: number;
    created_at: string;
    updated_at: string;
}

export interface Position {
    id: number;
    portfolio_id: number;
    symbol: string;
    quantity: number;
    avg_entry_price: number;
    current_price: number;
    unrealized_pnl: number;
    stop_loss_price?: number;
    take_profit_price?: number;
    trailing_stop_pct?: number;
    created_at: string;
    updated_at: string;
}

export interface Trade {
    id: number;
    portfolio_id: number;
    symbol: string;
    side: 'buy' | 'sell';
    quantity: number;
    price: number;
    commission?: number;
    pnl?: number;
    ai_confidence?: number;
    strategy_used?: string;
    executed_at: string;
    timestamp: string;
}

export interface AIStatus {
    is_training: boolean;
    epsilon: number;
    total_episodes: number;
    avg_reward: number;
}

export interface BacktestResult {
    id: number;
    symbol: string;
    start_date: string;
    end_date: string;
    strategy: string;
    initial_balance: number;
    final_balance: number | null;
    total_return_pct: number | null;
    num_trades: number | null;
    win_rate: number | null;
    max_drawdown: number | null;
    sharpe_ratio: number | null;
    status: 'pending' | 'running' | 'completed' | 'failed';
}

export interface Alert {
    id: number;
    type: 'info' | 'warning' | 'error' | 'success';
    message: string;
    details?: Record<string, any>;
    created_at: string;
    is_read: boolean;
}

export interface User {
    id: number;
    username: string;
    email: string;
    is_active: boolean;
    is_superuser: boolean;
    created_at: string;
}
