import { useState, useEffect, useRef } from 'react';

// FRONTEND SOVEREIGN v3
// AUTH: JWT REQUIRED
// ENDPOINT: http://localhost:8000

const API_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws';

export default function App() {
    const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
    const [isAuthenticated, setIsAuthenticated] = useState<boolean>(!!token);

    if (!isAuthenticated) {
        return <LoginScreen onLogin={(t) => {
            setToken(t);
            setIsAuthenticated(true);
            localStorage.setItem('token', t);
        }} />;
    }

    return <MonitorDashboard token={token!} onLogout={() => {
        setToken(null);
        setIsAuthenticated(false);
        localStorage.removeItem('token');
    }} />;
}

function LoginScreen({ onLogin }: { onLogin: (token: string) => void }) {
    const [username, setUsername] = useState('admin');
    const [password, setPassword] = useState('admin');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
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

            if (!res.ok) throw new Error('Invalid Credentials');

            const data = await res.json();
            onLogin(data.access_token);
        } catch (err) {
            setError(String(err));
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
                    <label>IDENTITY</label>
                    <input type="text" value={username} onChange={e => setUsername(e.target.value)}
                        style={{ width: '100%', padding: '8px', background: '#111', border: '1px solid #333', color: '#fff' }} />
                </div>
                <div style={{ marginBottom: '20px' }}>
                    <label>KEY</label>
                    <input type="password" value={password} onChange={e => setPassword(e.target.value)}
                        style={{ width: '100%', padding: '8px', background: '#111', border: '1px solid #333', color: '#fff' }} />
                </div>
                {error && <div style={{ color: 'red', marginBottom: '10px' }}>{error}</div>}
                <button type="submit" disabled={loading} style={{
                    width: '100%', padding: '10px', background: '#0f0', color: '#000', border: 'none', fontWeight: 'bold', cursor: 'pointer'
                }}>
                    {loading ? 'AUTHENTICATING...' : 'INITIATE UPLINK'}
                </button>
            </form>
        </div>
    );
}

function MonitorDashboard({ token, onLogout }: { token: string, onLogout: () => void }) {
    const [status, setStatus] = useState('CONNECTING...');
    const [logs, setLogs] = useState<string[]>([]);
    const ws = useRef<WebSocket | null>(null);

    useEffect(() => {
        let reconnectInterval: ReturnType<typeof setTimeout>;

        const connect = () => {
            setStatus('AUTHENTICATING UPLINK...');
            try {
                // SECURE HANDSHAKE
                const socket = new WebSocket(`${WS_URL}?token=${token}`);
                ws.current = socket;

                socket.onopen = () => {
                    setStatus('🟢 SECURE LINK ESTABLISHED');
                    setLogs(prev => [`[${new Date().toLocaleTimeString()}] >>> HANDSHAKE VERIFIED`, ...prev]);
                };

                socket.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    setLogs(prev => [`[${new Date().toLocaleTimeString()}] ${JSON.stringify(data, null, 2)}`, ...prev.slice(0, 50)]);
                };

                socket.onerror = (err) => {
                    console.error(err);
                    setStatus('🔴 CONNECTION ERROR');
                };

                socket.onclose = (e) => {
                    if (e.code === 4003) {
                        setStatus('⛔ ACCESS DENIED');
                        onLogout(); // Force logout on auth fail
                    } else {
                        setStatus('🟡 DISCONNECTED (RETRYING...)');
                        reconnectInterval = setTimeout(connect, 3000);
                    }
                };
            } catch (e) {
                setStatus('❌ CRITICAL FAILURE');
            }
        };

        connect();

        return () => {
            if (ws.current) ws.current.close();
            clearTimeout(reconnectInterval);
        };
    }, [token, onLogout]);

    return (
        <div style={{
            backgroundColor: '#000000',
            color: '#00ff41',
            fontFamily: '"Courier New", Courier, monospace',
            minHeight: '100vh',
            padding: '20px',
            overflow: 'hidden'
        }}>
            <div style={{
                borderBottom: '2px solid #00ff41',
                paddingBottom: '10px',
                marginBottom: '20px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
            }}>
                <h1 style={{ margin: 0, fontSize: '24px' }}>NEXUS MONITOR // SECURE</h1>
                <div>
                    <span style={{ fontWeight: 'bold', marginRight: '20px' }}>{status}</span>
                    <button onClick={onLogout} style={{ background: 'red', border: 'none', padding: '5px 10px', cursor: 'pointer' }}>LOGOUT</button>
                </div>
            </div>

            <div style={{
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
            </div>
        </div>
    );
}
