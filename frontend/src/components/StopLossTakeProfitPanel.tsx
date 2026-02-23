import { useState } from 'react';
import { Position } from '../types';

interface StopLossTakeProfitPanelProps {
    positions: Position[];
    onUpdate?: () => void;
}

export default function StopLossTakeProfitPanel({ positions, onUpdate }: StopLossTakeProfitPanelProps) {
    const [editingPosition, setEditingPosition] = useState<number | null>(null);
    const [stopLossPct, setStopLossPct] = useState(2.0);
    const [takeProfitPct, setTakeProfitPct] = useState(5.0);
    const [trailing, setTrailing] = useState(false);

    const handleSetLevels = async (positionId: number) => {
        const token = localStorage.getItem('token');

        try {
            const response = await fetch(`http://localhost:8000/api/stop-loss/${positionId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    stop_loss_pct: stopLossPct / 100,
                    take_profit_pct: takeProfitPct / 100,
                    trailing_stop: trailing
                })
            });

            if (response.ok) {
                setEditingPosition(null);
                if (onUpdate) onUpdate();
            }
        } catch (error) {
            console.error('Failed to set stop-loss/take-profit:', error);
        }
    };

    const quickPresets = [
        { label: 'Conservative', sl: 1.0, tp: 2.0 },
        { label: 'Moderate', sl: 2.0, tp: 5.0 },
        { label: 'Aggressive', sl: 5.0, tp: 10.0 }
    ];

    return (
        <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-bold mb-6 text-gray-800">Stop-Loss & Take-Profit</h2>

            {positions.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No open positions</p>
            ) : (
                <div className="space-y-4">
                    {positions.map((position) => (
                        <div key={position.id} className="border rounded-lg p-4">
                            <div className="flex justify-between items-start mb-3">
                                <div>
                                    <h3 className="text-lg font-semibold">{position.symbol}</h3>
                                    <p className="text-sm text-gray-600">
                                        {position.quantity} shares @ ${position.avg_entry_price.toFixed(2)}
                                    </p>
                                    <p className="text-sm text-gray-600">
                                        Current: ${position.current_price.toFixed(2)}
                                    </p>
                                </div>
                                <div className="text-right">
                                    {position.stop_loss_price && (
                                        <div className="text-sm">
                                            <span className="text-red-600">SL: ${position.stop_loss_price.toFixed(2)}</span>
                                        </div>
                                    )}
                                    {position.take_profit_price && (
                                        <div className="text-sm">
                                            <span className="text-green-600">TP: ${position.take_profit_price.toFixed(2)}</span>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {editingPosition === position.id ? (
                                <div className="space-y-3 bg-gray-50 p-4 rounded">
                                    <div className="flex gap-2 justify-center mb-2">
                                        {quickPresets.map((preset) => (
                                            <button
                                                key={preset.label}
                                                onClick={() => {
                                                    setStopLossPct(preset.sl);
                                                    setTakeProfitPct(preset.tp);
                                                }}
                                                className="px-3 py-1 text-xs bg-blue-100 hover:bg-blue-200 rounded"
                                            >
                                                {preset.label}
                                            </button>
                                        ))}
                                    </div>

                                    <div className="grid grid-cols-2 gap-3">
                                        <div>
                                            <label className="block text-sm font-medium mb-1">Stop-Loss %</label>
                                            <input
                                                type="number"
                                                value={stopLossPct}
                                                onChange={(e) => setStopLossPct(Number(e.target.value))}
                                                className="w-full px-3 py-2 border rounded"
                                                step="0.1"
                                                min="0.1"
                                                max="50"
                                            />
                                            <p className="text-xs text-gray-500 mt-1">
                                                ${(position.avg_entry_price * (1 - stopLossPct / 100)).toFixed(2)}
                                            </p>
                                        </div>

                                        <div>
                                            <label className="block text-sm font-medium mb-1">Take-Profit %</label>
                                            <input
                                                type="number"
                                                value={takeProfitPct}
                                                onChange={(e) => setTakeProfitPct(Number(e.target.value))}
                                                className="w-full px-3 py-2 border rounded"
                                                step="0.1"
                                                min="0.1"
                                                max="100"
                                            />
                                            <p className="text-xs text-gray-500 mt-1">
                                                ${(position.avg_entry_price * (1 + takeProfitPct / 100)).toFixed(2)}
                                            </p>
                                        </div>
                                    </div>

                                    <div className="flex items-center">
                                        <input
                                            type="checkbox"
                                            id={`trailing-${position.id}`}
                                            checked={trailing}
                                            onChange={(e) => setTrailing(e.target.checked)}
                                            className="mr-2"
                                        />
                                        <label htmlFor={`trailing-${position.id}`} className="text-sm">
                                            Trailing Stop-Loss
                                        </label>
                                    </div>

                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => handleSetLevels(position.id)}
                                            className="flex-1 bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
                                        >
                                            Apply
                                        </button>
                                        <button
                                            onClick={() => setEditingPosition(null)}
                                            className="flex-1 bg-gray-300 text-gray-700 py-2 rounded hover:bg-gray-400"
                                        >
                                            Cancel
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <button
                                    onClick={() => setEditingPosition(position.id)}
                                    className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
                                >
                                    Set Stop-Loss & Take-Profit
                                </button>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
