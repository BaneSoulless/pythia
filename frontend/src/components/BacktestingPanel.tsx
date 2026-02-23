import { useState } from 'react';

interface BacktestResult {
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
    status: string;
}

export default function BacktestingPanel() {
    const [symbol, setSymbol] = useState('AAPL');
    const [startDate, setStartDate] = useState('2024-01-01');
    const [endDate, setEndDate] = useState('2024-11-22');
    const [strategy, setStrategy] = useState('momentum');
    const [initialBalance, setInitialBalance] = useState(10000);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<BacktestResult | null>(null);
    const [error, setError] = useState('');

    const handleRunBacktest = async () => {
        setLoading(true);
        setError('');
        setResult(null);

        try {
            const token = localStorage.getItem('token');
            const response = await fetch('http://localhost:8000/api/backtest/run', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify({
                    symbol,
                    start_date: startDate,
                    end_date: endDate,
                    strategy,
                    initial_balance: initialBalance,
                }),
            });

            if (!response.ok) {
                throw new Error('Backtest failed');
            }

            const data = await response.json();

            // Poll for results
            const backtestId = data.backtest_id;
            let attempts = 0;
            const maxAttempts = 30;

            const pollResult = async () => {
                const resultResponse = await fetch(
                    `http://localhost:8000/api/backtest/${backtestId}`,
                    {
                        headers: {
                            'Authorization': `Bearer ${token}`,
                        },
                    }
                );

                if (resultResponse.ok) {
                    const resultData = await resultResponse.json();

                    if (resultData.status === 'completed') {
                        setResult(resultData);
                        setLoading(false);
                    } else if (resultData.status === 'failed') {
                        setError('Backtest failed');
                        setLoading(false);
                    } else if (attempts < maxAttempts) {
                        attempts++;
                        setTimeout(pollResult, 2000);
                    } else {
                        setError('Backtest timeout');
                        setLoading(false);
                    }
                }
            };

            pollResult();
        } catch (err: any) {
            setError(err.message);
            setLoading(false);
        }
    };

    return (
        <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-bold mb-6 text-gray-800">Backtesting Engine</h2>

            <div className="grid grid-cols-2 gap-4 mb-6">
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Symbol
                    </label>
                    <input
                        type="text"
                        value={symbol}
                        onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                        placeholder="AAPL"
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Strategy
                    </label>
                    <select
                        value={strategy}
                        onChange={(e) => setStrategy(e.target.value)}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    >
                        <option value="momentum">Momentum</option>
                        <option value="mean_reversion">Mean Reversion</option>
                        <option value="ai_dqn">AI DQN</option>
                    </select>
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Start Date
                    </label>
                    <input
                        type="date"
                        value={startDate}
                        onChange={(e) => setStartDate(e.target.value)}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        End Date
                    </label>
                    <input
                        type="date"
                        value={endDate}
                        onChange={(e) => setEndDate(e.target.value)}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                </div>

                <div className="col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Initial Balance ($)
                    </label>
                    <input
                        type="number"
                        value={initialBalance}
                        onChange={(e) => setInitialBalance(Number(e.target.value))}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                        min="100"
                    />
                </div>
            </div>

            <button
                onClick={handleRunBacktest}
                disabled={loading}
                className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 transition disabled:bg-gray-400 font-semibold"
            >
                {loading ? 'Running Backtest...' : 'Run Backtest'}
            </button>

            {error && (
                <div className="mt-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
                    {error}
                </div>
            )}

            {result && (
                <div className="mt-6 bg-gray-50 rounded-lg p-6">
                    <h3 className="text-xl font-bold mb-4 text-gray-800">Results</h3>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="bg-white p-4 rounded shadow">
                            <p className="text-sm text-gray-600">Initial Balance</p>
                            <p className="text-2xl font-bold">${result.initial_balance.toLocaleString()}</p>
                        </div>

                        <div className="bg-white p-4 rounded shadow">
                            <p className="text-sm text-gray-600">Final Balance</p>
                            <p className="text-2xl font-bold text-green-600">
                                ${result.final_balance?.toLocaleString() || 'N/A'}
                            </p>
                        </div>

                        <div className="bg-white p-4 rounded shadow">
                            <p className="text-sm text-gray-600">Total Return</p>
                            <p className={`text-2xl font-bold ${(result.total_return_pct || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                                }`}>
                                {result.total_return_pct?.toFixed(2)}%
                            </p>
                        </div>

                        <div className="bg-white p-4 rounded shadow">
                            <p className="text-sm text-gray-600">Win Rate</p>
                            <p className="text-2xl font-bold">
                                {result.win_rate ? `${(result.win_rate * 100).toFixed(1)}%` : 'N/A'}
                            </p>
                        </div>

                        <div className="bg-white p-4 rounded shadow">
                            <p className="text-sm text-gray-600">Trades</p>
                            <p className="text-2xl font-bold">{result.num_trades || 0}</p>
                        </div>

                        <div className="bg-white p-4 rounded shadow">
                            <p className="text-sm text-gray-600">Max Drawdown</p>
                            <p className="text-2xl font-bold text-red-600">
                                {result.max_drawdown ? `${(result.max_drawdown * 100).toFixed(2)}%` : 'N/A'}
                            </p>
                        </div>

                        <div className="bg-white p-4 rounded shadow col-span-2">
                            <p className="text-sm text-gray-600">Sharpe Ratio</p>
                            <p className="text-2xl font-bold">
                                {result.sharpe_ratio?.toFixed(2) || 'N/A'}
                            </p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
