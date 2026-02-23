import { useState, useEffect } from 'react';

interface WatchlistSymbol {
    symbol: string;
    score: number;
    allocation_pct: number;
    current_price: number;
    daily_change_pct: number;
}

export default function MultiSymbolWatchlistPanel() {
    const [watchlist, setWatchlist] = useState<WatchlistSymbol[]>([]);
    const [newSymbol, setNewSymbol] = useState('');
    const [loading, setLoading] = useState(false);
    const [rebalancing, setRebalancing] = useState(false);

    useEffect(() => {
        fetchWatchlist();
    }, []);

    const fetchWatchlist = async () => {
        const token = localStorage.getItem('token');

        try {
            const response = await fetch('http://localhost:8000/api/watchlist', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const data = await response.json();
                setWatchlist(data.symbols || []);
            }
        } catch (error) {
            console.error('Failed to fetch watchlist:', error);
        }
    };

    const addSymbol = async () => {
        if (!newSymbol.trim()) return;

        const token = localStorage.getItem('token');
        setLoading(true);

        try {
            const response = await fetch('http://localhost:8000/api/watchlist/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ symbol: newSymbol.toUpperCase() })
            });

            if (response.ok) {
                setNewSymbol('');
                fetchWatchlist();
            }
        } catch (error) {
            console.error('Failed to add symbol:', error);
        } finally {
            setLoading(false);
        }
    };

    const removeSymbol = async (symbol: string) => {
        const token = localStorage.getItem('token');

        try {
            const response = await fetch(`http://localhost:8000/api/watchlist/${symbol}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                fetchWatchlist();
            }
        } catch (error) {
            console.error('Failed to remove symbol:', error);
        }
    };

    const handleRebalance = async () => {
        const token = localStorage.getItem('token');
        setRebalancing(true);

        try {
            const response = await fetch('http://localhost:8000/api/watchlist/rebalance', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const data = await response.json();
                alert(`Rebalancing complete: ${data.message}`);
                fetchWatchlist();
            }
        } catch (error) {
            console.error('Failed to rebalance:', error);
        } finally {
            setRebalancing(false);
        }
    };

    const categories = {
        Tech: ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'META'],
        Finance: ['JPM', 'BAC', 'WFC', 'GS', 'MS'],
        Energy: ['XOM', 'CVX', 'COP', 'SLB', 'EOG'],
        Healthcare: ['UNH', 'JNJ', 'PFE', 'ABBV', 'TMO']
    };

    return (
        <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-bold mb-6 text-gray-800">Multi-Symbol Watchlist</h2>

            {/* Add Symbol */}
            <div className="mb-6">
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={newSymbol}
                        onChange={(e) => setNewSymbol(e.target.value.toUpperCase())}
                        onKeyPress={(e) => e.key === 'Enter' && addSymbol()}
                        placeholder="Enter symbol (e.g., AAPL)"
                        className="flex-1 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                    <button
                        onClick={addSymbol}
                        disabled={loading || !newSymbol.trim()}
                        className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
                    >
                        {loading ? 'Adding...' : 'Add'}
                    </button>
                </div>

                {/* Quick Add Categories */}
                <div className="mt-3 flex flex-wrap gap-2">
                    {Object.entries(categories).map(([category, symbols]) => (
                        <div key={category} className="flex items-center gap-1">
                            <span className="text-sm font-medium text-gray-600">{category}:</span>
                            {symbols.slice(0, 3).map((sym) => (
                                <button
                                    key={sym}
                                    onClick={() => {
                                        setNewSymbol(sym);
                                        setTimeout(() => addSymbol(), 100);
                                    }}
                                    className="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded"
                                >
                                    {sym}
                                </button>
                            ))}
                        </div>
                    ))}
                </div>
            </div>

            {/* Watchlist Table */}
            {watchlist.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                    <p className="text-lg mb-2">No symbols in watchlist</p>
                    <p className="text-sm">Add symbols above to start tracking</p>
                </div>
            ) : (
                <>
                    <div className="overflow-x-auto mb-4">
                        <table className="min-w-full">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Symbol</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Score</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Allocation</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Price</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Change</th>
                                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-200">
                                {watchlist.map((item) => (
                                    <tr key={item.symbol} className="hover:bg-gray-50">
                                        <td className="px-4 py-3">
                                            <span className="font-semibold text-blue-600">{item.symbol}</span>
                                        </td>
                                        <td className="px-4 py-3">
                                            <div className="flex items-center">
                                                <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                                                    <div
                                                        className="bg-blue-600 h-2 rounded-full"
                                                        style={{ width: `${Math.min(item.score * 100, 100)}%` }}
                                                    />
                                                </div>
                                                <span className="text-sm">{(item.score * 100).toFixed(0)}</span>
                                            </div>
                                        </td>
                                        <td className="px-4 py-3">
                                            <div className="flex items-center">
                                                <div className="w-24 bg-gray-200 rounded-full h-2 mr-2">
                                                    <div
                                                        className="bg-green-600 h-2 rounded-full"
                                                        style={{ width: `${item.allocation_pct}%` }}
                                                    />
                                                </div>
                                                <span className="text-sm">{item.allocation_pct.toFixed(1)}%</span>
                                            </div>
                                        </td>
                                        <td className="px-4 py-3 text-sm">
                                            ${item.current_price?.toFixed(2) || 'N/A'}
                                        </td>
                                        <td className="px-4 py-3">
                                            <span className={`text-sm font-medium ${item.daily_change_pct >= 0 ? 'text-green-600' : 'text-red-600'
                                                }`}>
                                                {item.daily_change_pct >= 0 ? '+' : ''}
                                                {item.daily_change_pct?.toFixed(2)}%
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-right">
                                            <button
                                                onClick={() => removeSymbol(item.symbol)}
                                                className="text-red-600 hover:text-red-800 text-sm"
                                            >
                                                Remove
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {/* Rebalance Button */}
                    <div className="flex justify-between items-center mt-6 pt-4 border-t">
                        <div className="text-sm text-gray-600">
                            <p><strong>{watchlist.length}</strong> symbols tracked</p>
                            <p className="text-xs mt-1">Max allocation per symbol: 15%</p>
                        </div>
                        <button
                            onClick={handleRebalance}
                            disabled={rebalancing}
                            className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-400"
                        >
                            {rebalancing ? 'Rebalancing...' : 'Rebalance Portfolio'}
                        </button>
                    </div>
                </>
            )}
        </div>
    );
}
