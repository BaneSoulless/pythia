import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import LoginForm from './components/LoginForm';
import RegisterForm from './components/RegisterForm';
import BacktestingPanel from './components/BacktestingPanel';
import Dashboard from './Dashboard'; // Your existing dashboard

function App() {
    const [isAuthenticated, setIsAuthenticated] = useState(false);

    useEffect(() => {
        // Check if user has token
        const token = localStorage.getItem('token');
        setIsAuthenticated(!!token);
    }, []);

    return (
        <BrowserRouter>
            <Routes>
                {/* Public routes */}
                <Route
                    path="/login"
                    element={
                        isAuthenticated ?
                            <Navigate to="/dashboard" /> :
                            <LoginForm onSuccess={() => setIsAuthenticated(true)} />
                    }
                />
                <Route
                    path="/register"
                    element={
                        isAuthenticated ?
                            <Navigate to="/dashboard" /> :
                            <RegisterForm />
                    }
                />

                {/* Protected routes */}
                <Route
                    path="/dashboard"
                    element={
                        isAuthenticated ?
                            <Dashboard /> :
                            <Navigate to="/login" />
                    }
                />
                <Route
                    path="/backtest"
                    element={
                        isAuthenticated ?
                            <BacktestingPanel /> :
                            <Navigate to="/login" />
                    }
                />

                {/* Default route */}
                <Route
                    path="/"
                    element={
                        isAuthenticated ?
                            <Navigate to="/dashboard" /> :
                            <Navigate to="/login" />
                    }
                />

                {/* 404 catch-all */}
                <Route path="*" element={<Navigate to="/" />} />
            </Routes>
        </BrowserRouter>
    );
}

export default App;
