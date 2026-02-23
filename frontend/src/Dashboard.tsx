import { useState, useEffect } from 'react'
import './App.css'

interface Portfolio {
    id: number
    balance: number
    total_value: number
}

interface Position {
    id: number
    symbol: string
    quantity: number
    average_price: number
    current_price: number
    unrealized_pnl: number
}

interface Trade {
    id: number
    symbol: string
    side: string
    quantity: number
    price: number
    timestamp: string
    pnl?: number
}

interface AIStatus {
    is_training: boolean
    epsilon: number
    total_episodes: number
    avg_reward: number
}

function Dashboard() {
    const [portfolio, setPortfolio] = useState<Portfolio | null>(null)
    const [positions, setPositions] = useState<Position[]>([])
    const [trades, setTrades] = useState<Trade[]>([])
    const [aiStatus, setAIStatus] = useState<AIStatus | null>(null)

    useEffect(() => {
        const token = localStorage.getItem('token')
        const websocket = new WebSocket(`ws://localhost:8000/ws?token=${token}`)

        websocket.onmessage = (event: MessageEvent) => {
            const data = JSON.parse(event.data)

            if (data.type === 'portfolio_update') {
                setPortfolio(data.portfolio)
                setPositions(data.portfolio.positions || [])
            } else if (data.type === 'trade_executed') {
                setTrades((prev: Trade[]) => [data.trade, ...prev].slice(0, 10))
            } else if (data.type === 'ai_status_update') {
                setAIStatus(data.ai_status)
            }
        }

        websocket.onerror = (error) => {
            console.error('WebSocket error:', error)
        }

        return () => {
            websocket.close()
        }
    }, [])

    const handleLogout = () => {
        localStorage.removeItem('token')
        window.location.href = '/login'
    }

return (
    <div className="min-h-screen bg-gray-100">
        {/* Header */}
        <header className="bg-white shadow">
            <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8 flex justify-between items-center">
                <h1 className="text-3xl font-bold text-gray-900">AI Trading Bot Dashboard</h1>
                <div className="flex gap-4">
                    <a href="/backtest" className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
                        Backtesting
                    </a>
                    <button onClick={handleLogout} className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700">
                        Logout
                    </button>
                </div>
            </div>
        </header>

        <main className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
            {/* Portfolio Overview */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                <div className="bg-white overflow-hidden shadow rounded-lg">
                    <div className="px-4 py-5 sm:p-6">
                        <dt className="text-sm font-medium text-gray-500 truncate">Total Value</dt>
                        <dd className="mt-1 text-3xl font-semibold text-gray-900">
                            ${portfolio?.total_value.toFixed(2) || '0.00'}
                        </dd>
                    </div>
                </div>

                <div className="bg-white overflow-hidden shadow rounded-lg">
                    <div className="px-4 py-5 sm:p-6">
                        <dt className="text-sm font-medium text-gray-500 truncate">Cash Balance</dt>
                        <dd className="mt-1 text-3xl font-semibold text-gray-900">
                            ${portfolio?.balance.toFixed(2) || '0.00'}
                        </dd>
                    </div>
                </div>

                <div className="bg-white overflow-hidden shadow rounded-lg">
                    <div className="px-4 py-5 sm:p-6">
                        <dt className="text-sm font-medium text-gray-500 truncate">Open Positions</dt>
                        <dd className="mt-1 text-3xl font-semibold text-gray-900">
                            {positions.length}
                        </dd>
                    </div>
                </div>
            </div>

            {/* AI Status */}
            {aiStatus && (
                <div className="bg-white shadow rounded-lg p-6 mb-6">
                    <h2 className="text-xl font-bold mb-4">AI Status</h2>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div>
                            <p className="text-sm text-gray-600">Status</p>
                            <p className="text-lg font-semibold">
                                {aiStatus.is_training ? '🟢 Training' : '⚪ Idle'}
                            </p>
                        </div>
                        <div>
                            <p className="text-sm text-gray-600">Epsilon</p>
                            <p className="text-lg font-semibold">{aiStatus.epsilon.toFixed(3)}</p>
                        </div>
                        <div>
                            <p className="text-sm text-gray-600">Episodes</p>
                            <p className="text-lg font-semibold">{aiStatus.total_episodes}</p>
                        </div>
                        <div>
                            <p className="text-sm text-gray-600">Avg Reward</p>
                            <p className="text-lg font-semibold">{aiStatus.avg_reward.toFixed(2)}</p>
                        </div>
                    </div>
                </div>
            )}

            {/* Positions */}
            <div className="bg-white shadow rounded-lg p-6 mb-6">
                <h2 className="text-xl font-bold mb-4">Current Positions</h2>
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead>
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Symbol</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Quantity</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Avg Price</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Current</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">P&L</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200">
                            {positions.map(pos => (
                                <tr key={pos.id}>
                                    <td className="px-6 py-4 whitespace-nowrap font-medium">{pos.symbol}</td>
                                    <td className="px-6 py-4 whitespace-nowrap">{pos.quantity}</td>
                                    <td className="px-6 py-4 whitespace-nowrap">${pos.average_price.toFixed(2)}</td>
                                    <td className="px-6 py-4 whitespace-nowrap">${pos.current_price.toFixed(2)}</td>
                                    <td className={`px-6 py-4 whitespace-nowrap font-semibold ${pos.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'
                                        }`}>
                                        ${pos.unrealized_pnl.toFixed(2)}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    {positions.length === 0 && (
                        <p className="text-center text-gray-500 py-4">No open positions</p>
                    )}
                </div>
            </div>

            {/* Recent Trades */}
            <div className="bg-white shadow rounded-lg p-6">
                <h2 className="text-xl font-bold mb-4">Recent Trades</h2>
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead>
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Symbol</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Side</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Quantity</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Price</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">P&L</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200">
                            {trades.map(trade => (
                                <tr key={trade.id}>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                                        {new Date(trade.timestamp).toLocaleTimeString()}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap font-medium">{trade.symbol}</td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className={`px-2 py-1 rounded ${trade.side === 'buy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                                            }`}>
                                            {trade.side.toUpperCase()}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">{trade.quantity}</td>
                                    <td className="px-6 py-4 whitespace-nowrap">${trade.price.toFixed(2)}</td>
                                    <td className={`px-6 py-4 whitespace-nowrap ${(trade.pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                                        }`}>
                                        {trade.pnl ? `$${trade.pnl.toFixed(2)}` : '-'}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    {trades.length === 0 && (
                        <p className="text-center text-gray-500 py-4">No trades yet</p>
                    )}
                </div>
            </div>
        </main>
    </div>
)
}

export default Dashboard
