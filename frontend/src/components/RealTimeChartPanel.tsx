import { useState, useEffect } from 'react';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface PriceData {
    timestamp: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
}

interface ChartPanelProps {
    symbol: string;
    timeframe?: '1D' | '1W' | '1M' | '3M' | '1Y';
}

export default function RealTimeChartPanel({ symbol = 'AAPL', timeframe = '1D' }: ChartPanelProps) {
    const [data, setData] = useState<PriceData[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedTimeframe, setSelectedTimeframe] = useState(timeframe);
    const [chartType, setChartType] = useState<'line' | 'area'>('area');

    useEffect(() => {
        fetchChartData();
    }, [symbol, selectedTimeframe]);

    const fetchChartData = async () => {
        setLoading(true);
        const token = localStorage.getItem('token');

        try {
            const response = await fetch(
                `http://localhost:8000/api/market/chart/${symbol}?timeframe=${selectedTimeframe}`,
                {
                    headers: { 'Authorization': `Bearer ${token}` }
                }
            );

            if (response.ok) {
                const chartData = await response.json();
                setData(chartData);
            }
        } catch (error) {
            console.error('Failed to fetch chart data:', error);
            // Fallback to mock data for demo
            setData(generateMockData());
        } finally {
            setLoading(false);
        }
    };

    const generateMockData = (): PriceData[] => {
        const data: PriceData[] = [];
        let basePrice = 150;
        const now = new Date();

        for (let i = 30; i >= 0; i--) {
            const timestamp = new Date(now.getTime() - i * 24 * 60 * 60 * 1000);
            const change = (Math.random() - 0.5) * 5;
            basePrice += change;

            data.push({
                timestamp: timestamp.toISOString().split('T')[0],
                open: basePrice,
                high: basePrice + Math.random() * 3,
                low: basePrice - Math.random() * 3,
                close: basePrice + (Math.random() - 0.5) * 2,
                volume: Math.floor(Math.random() * 10000000)
            });
        }

        return data;
    };

    const timeframes = ['1D', '1W', '1M', '3M', '1Y'];

    const formatPrice = (value: number) => `$${value.toFixed(2)}`;
    const formatVolume = (value: number) => `${(value / 1000000).toFixed(1)}M`;

    const currentPrice = data.length > 0 ? data[data.length - 1].close : 0;
    const firstPrice = data.length > 0 ? data[0].close : 0;
    const priceChange = currentPrice - firstPrice;
    const priceChangePct = firstPrice > 0 ? (priceChange / firstPrice) * 100 : 0;

    return (
        <div className="bg-white rounded-lg shadow-lg p-6">
            {/* Header */}
            <div className="flex justify-between items-start mb-6">
                <div>
                    <h2 className="text-2xl font-bold text-gray-800">{symbol}</h2>
                    <div className="flex items-baseline gap-3 mt-2">
                        <span className="text-3xl font-bold">${currentPrice.toFixed(2)}</span>
                        <span className={`text-lg font-semibold ${priceChange >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {priceChange >= 0 ? '+' : ''}{priceChange.toFixed(2)} ({priceChangePct >= 0 ? '+' : ''}{priceChangePct.toFixed(2)}%)
                        </span>
                    </div>
                </div>

                {/* Timeframe Selector */}
                <div className="flex gap-2">
                    {timeframes.map((tf) => (
                        <button
                            key={tf}
                            onClick={() => setSelectedTimeframe(tf as any)}
                            className={`px-3 py-1 rounded ${selectedTimeframe === tf
                                    ? 'bg-blue-600 text-white'
                                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                }`}
                        >
                            {tf}
                        </button>
                    ))}
                </div>
            </div>

            {/* Chart Type Toggle */}
            <div className="mb-4 flex gap-2">
                <button
                    onClick={() => setChartType('area')}
                    className={`px-4 py-2 rounded ${chartType === 'area' ? 'bg-blue-600 text-white' : 'bg-gray-100'
                        }`}
                >
                    Area Chart
                </button>
                <button
                    onClick={() => setChartType('line')}
                    className={`px-4 py-2 rounded ${chartType === 'line' ? 'bg-blue-600 text-white' : 'bg-gray-100'
                        }`}
                >
                    Line Chart
                </button>
            </div>

            {/* Chart */}
            {loading ? (
                <div className="h-96 flex items-center justify-center">
                    <div className="text-gray-500">Loading chart data...</div>
                </div>
            ) : (
                <ResponsiveContainer width="100%" height={400}>
                    {chartType === 'area' ? (
                        <AreaChart data={data}>
                            <defs>
                                <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8} />
                                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis
                                dataKey="timestamp"
                                tick={{ fontSize: 12 }}
                                tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                            />
                            <YAxis
                                domain={['auto', 'auto']}
                                tick={{ fontSize: 12 }}
                                tickFormatter={formatPrice}
                            />
                            <Tooltip
                                formatter={(value: number) => formatPrice(value)}
                                labelFormatter={(label) => new Date(label).toLocaleDateString()}
                            />
                            <Area
                                type="monotone"
                                dataKey="close"
                                stroke="#3b82f6"
                                fillOpacity={1}
                                fill="url(#colorPrice)"
                            />
                        </AreaChart>
                    ) : (
                        <LineChart data={data}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis
                                dataKey="timestamp"
                                tick={{ fontSize: 12 }}
                                tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                            />
                            <YAxis
                                domain={['auto', 'auto']}
                                tick={{ fontSize: 12 }}
                                tickFormatter={formatPrice}
                            />
                            <Tooltip
                                formatter={(value: number) => formatPrice(value)}
                                labelFormatter={(label) => new Date(label).toLocaleDateString()}
                            />
                            <Legend />
                            <Line type="monotone" dataKey="high" stroke="#22c55e" strokeWidth={1} dot={false} name="High" />
                            <Line type="monotone" dataKey="close" stroke="#3b82f6" strokeWidth={2} name="Close" />
                            <Line type="monotone" dataKey="low" stroke="#ef4444" strokeWidth={1} dot={false} name="Low" />
                        </LineChart>
                    )}
                </ResponsiveContainer>
            )}

            {/* Stats */}
            <div className="grid grid-cols-4 gap-4 mt-6 pt-4 border-t">
                <div>
                    <p className="text-xs text-gray-500">Open</p>
                    <p className="text-sm font-semibold">${data[data.length - 1]?.open.toFixed(2)}</p>
                </div>
                <div>
                    <p className="text-xs text-gray-500">High</p>
                    <p className="text-sm font-semibold text-green-600">${data[data.length - 1]?.high.toFixed(2)}</p>
                </div>
                <div>
                    <p className="text-xs text-gray-500">Low</p>
                    <p className="text-sm font-semibold text-red-600">${data[data.length - 1]?.low.toFixed(2)}</p>
                </div>
                <div>
                    <p className="text-xs text-gray-500">Volume</p>
                    <p className="text-sm font-semibold">{formatVolume(data[data.length - 1]?.volume || 0)}</p>
                </div>
            </div>
        </div>
    );
}
