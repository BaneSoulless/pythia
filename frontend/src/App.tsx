import { useState, useEffect, useRef, useCallback } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';

interface TokenPair {
    access_token: string;
    refresh_token: string;
    expires_in: number;
}

let inMemoryToken: string | null = null;
let inMemoryRefresh: string | null = null;

function getToken(): string | null {
    return inMemoryToken;
}

function setTokens(pair: TokenPair | null): void {
    if (pair) {
        inMemoryToken = pair.access_token;
        inMemoryRefresh = pair.refresh_token;
    } else {
        inMemoryToken = null;
        inMemoryRefresh = null;
    }
}

async function refreshAccessToken(): Promise<string | null> {
    if (!inMemoryRefresh) return null;
    try {
        const res = await fetch(`${API_URL}/api/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: inMemoryRefresh }),
        });
        if (!res.ok) return null;
        const data: TokenPair = await res.json();
        setTokens(data);
        return data.access_token;
    } catch {
        return null;
    }
}

export default function App() {
    const [isAuthenticated, setIsAuthenticated] = useState<boolean>(!!getToken());

    const handleLogin = useCallback((pair: TokenPair) => {
        setTokens(pair);
        setIsAuthenticated(true);
    }, []);

    const handleLogout = useCallback(() => {
        setTokens(null);
        setIsAuthenticated(false);
    }, []);

    if (!isAuthenticated) {
        return <LoginScreen onLogin={handleLogin} />;
    }

    return <MonitorDashboard onLogout={handleLogout} />;
}

function LoginScreen({ onLogin }: { onLogin: (pair: TokenPair) => void }) {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!username.trim() || !password.trim()) {
            setError('Username and password required');
            return;
        }
        setLoading(true);
        setError('');

        try {
            const formData = new URLSearchParams();
            formData.append('username', username);
            formData.append('password', password);

            const res = await fetch(`${API_URL}/api/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: formData
            });

            if (!res.ok) {
                setError('Invalid credentials');
                return;
            }

            const data: TokenPair = await res.json();
            onLogin(data);
        } catch {
            setError('Connection failed. Check server status.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{
            backgroundColor: '#000', color: '#0f0', height: '100vh', display: 'flex',
            justifyContent: 'center', alignItems: 'center', fontFamily: 'monospace'
        }}>
            <form onSubmit={handleLogin} style={{ border: '1px solid #333', padding: '40px', width: '300px' }}>
                <h2 style={{ textAlign: 'center', marginBottom: '20px' }}>ACCESS TERMINAL</h2>
                <div style={{ marginBottom: '10px' }}>
                    <label htmlFor="login-username">IDENTITY</label>
                    <input
                        id="login-username"
                        type="text"
                        value={username}
                        onChange={e => setUsername(e.target.value)}
                        autoComplete="username"
                        aria-label="Username"
                        style={{ width: '100%', padding: '8px', background: '#111', border: '1px solid #333', color: '#fff' }}
                    />
                </div>
                <div style={{ marginBottom: '20px' }}>
                    <label htmlFor="login-password">KEY</label>
                    <input
                        id="login-password"
                        type="password"
                        value={password}
                        onChange={e => setPassword(e.target.value)}
                        autoComplete="current-password"
                        aria-label="Password"
                        style={{ width: '100%', padding: '8px', background: '#111', border: '1px solid #333', color: '#fff' }}
                    />
                </div>
                {error && <div role="alert" style={{ color: '#f44', marginBottom: '10px' }}>{error}</div>}
                <button type="submit" disabled={loading} style={{
                    width: '100%', padding: '10px', background: '#0f0', color: '#000', border: 'none', fontWeight: 'bold', cursor: 'pointer'
                }}>
                    {loading ? 'AUTHENTICATING...' : 'INITIATE UPLINK'}
                </button>
            </form>
        </div>
    );
}

function MonitorDashboard({ onLogout }: { onLogout: () => void }) {
    const [connectionStatus, setConnectionStatus] = useState('CONNECTING...');
    const [logs, setLogs] = useState<string[]>([]);
    const ws = useRef<WebSocket | null>(null);

    useEffect(() => {
        let reconnectTimeout: ReturnType<typeof setTimeout>;
        let isMounted = true;

        const connect = async () => {
            if (!isMounted) return;
            setConnectionStatus('AUTHENTICATING UPLINK...');

            let token = getToken();
            if (!token) {
                token = await refreshAccessToken();
                if (!token) {
                    onLogout();
                    return;
                }
            }

            try {
                const socket = new WebSocket(`${WS_URL}`);
                ws.current = socket;

                socket.onopen = () => {
                    socket.send(JSON.stringify({ type: 'auth', token }));
                    setConnectionStatus('🟢 SECURE LINK ESTABLISHED');
                    if (isMounted) {
                        setLogs(prev => [`[${new Date().toLocaleTimeString()}] >>> HANDSHAKE VERIFIED`, ...prev]);
                    }
                };

                socket.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        if (isMounted) {
                            setLogs(prev => [
                                `[${new Date().toLocaleTimeString()}] ${JSON.stringify(data, null, 2)}`,
                                ...prev.slice(0, 50)
                            ]);
                        }
                    } catch {
                        /* ignore malformed messages */
                    }
                };

                socket.onerror = () => {
                    if (isMounted) setConnectionStatus('🔴 CONNECTION ERROR');
                };

                socket.onclose = (e) => {
                    if (!isMounted) return;
                    if (e.code === 4003) {
                        setConnectionStatus('⛔ ACCESS DENIED');
                        onLogout();
                    } else {
                        setConnectionStatus('🟡 DISCONNECTED (RETRYING...)');
                        reconnectTimeout = setTimeout(connect, 3000);
                    }
                };
            } catch {
                if (isMounted) setConnectionStatus('❌ CRITICAL FAILURE');
            }
        };

        connect();

        return () => {
            isMounted = false;
            if (ws.current) ws.current.close();
            clearTimeout(reconnectTimeout);
        };
    }, [onLogout]);

    return (
        <div style={{
            backgroundColor: '#000000',
            color: '#00ff41',
            fontFamily: '"Courier New", Courier, monospace',
            minHeight: '100vh',
            padding: '20px',
            overflow: 'hidden'
        }}>
            <header style={{
                borderBottom: '2px solid #00ff41',
                paddingBottom: '10px',
                marginBottom: '20px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
            }}>
                <h1 style={{ margin: 0, fontSize: '24px' }}>NEXUS MONITOR // SECURE</h1>
                <div>
                    <span style={{ fontWeight: 'bold', marginRight: '20px' }}>{connectionStatus}</span>
                    <button
                        onClick={onLogout}
                        aria-label="Logout"
                        style={{ background: 'red', border: 'none', padding: '5px 10px', cursor: 'pointer', color: '#fff' }}
                    >
                        LOGOUT
                    </button>
                </div>
            </header>

            <main style={{
                backgroundColor: '#0a0a0a',
                border: '1px solid #333',
                height: '80vh',
                overflowY: 'auto',
                padding: '10px',
                whiteSpace: 'pre-wrap'
            }}>
                {logs.length === 0 && <div style={{ color: '#666' }}> Waiting for Encrypted Data Stream...</div>}
                {logs.map((log, i) => (
                    <div key={i} style={{ borderBottom: '1px solid #111', padding: '4px 0' }}>{log}</div>
                ))}
            </main>
        </div>
    );
}
