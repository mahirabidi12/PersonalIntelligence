import React, { useState } from 'react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const QUICK_USERS = [
  { email: 'saswata@whatsapp2.com', name: 'Saswata', avatar: '/img/109316527.jpg' },
  { email: 'ananya@whatsapp2.com', name: 'Ananya', avatar: '/img/girl-profile.jpg' },
  { email: 'arjun@whatsapp2.com', name: 'Arjun Mehta', avatar: '/img/arjun-profile.jpg' },
  { email: 'priya@whatsapp2.com', name: 'Priya Sharma', avatar: '/img/79feb1611dddcbce7910e0c1081df6e2.jpg' },
  { email: 'vikram@whatsapp2.com', name: 'Vikram Patel', avatar: '/img/e5wnacz2aaaa.jpg' },
];

export default function LoginPage({ onLogin }) {
  const [tab, setTab] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const url = tab === 'login'
        ? `${API_URL}/api/auth/login`
        : `${API_URL}/api/auth/register`;

      const body = tab === 'login'
        ? { email, password }
        : { email, password, username };

      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || 'Something went wrong');
        return;
      }

      onLogin(data.token, data);
    } catch (e) {
      setError('Connection failed');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = async (userEmail) => {
    setError('');
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: userEmail, password: 'password123' }),
      });
      const data = await res.json();
      if (res.ok) {
        onLogin(data.token, data);
      } else {
        setError(data.detail || 'Login failed');
      }
    } catch (e) {
      setError('Connection failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="wa-login-page" data-testid="login-page">
      <div className="wa-login-card">
        <div className="wa-login-logo">
          <img src="/img/icons8-whatsapp-48.png" alt="WhatsApp2" />
          <h1>WhatsApp2</h1>
        </div>

        <div className="wa-login-tabs">
          <button
            className={`wa-login-tab ${tab === 'login' ? 'active' : ''}`}
            onClick={() => setTab('login')}
            data-testid="login-tab"
          >
            Login
          </button>
          <button
            className={`wa-login-tab ${tab === 'register' ? 'active' : ''}`}
            onClick={() => setTab('register')}
            data-testid="register-tab"
          >
            Register
          </button>
        </div>

        <form className="wa-login-form" onSubmit={handleSubmit}>
          {tab === 'register' && (
            <input
              className="wa-login-input"
              type="text"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required={tab === 'register'}
              data-testid="register-username-input"
            />
          )}
          <input
            className="wa-login-input"
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            data-testid="login-email-input"
          />
          <input
            className="wa-login-input"
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            data-testid="login-password-input"
          />
          {error && <p className="wa-login-error" data-testid="login-error">{error}</p>}
          <button
            className="wa-login-btn"
            type="submit"
            disabled={loading}
            data-testid="login-submit-btn"
          >
            {loading ? 'Please wait...' : (tab === 'login' ? 'Login' : 'Register')}
          </button>
        </form>

        <div className="wa-login-quick">
          <h3>Quick Login</h3>
          <div className="wa-quick-users" data-testid="quick-login-users">
            {QUICK_USERS.map((u) => (
              <div
                key={u.email}
                className="wa-quick-user"
                onClick={() => handleQuickLogin(u.email)}
                data-testid={`quick-login-${u.name.toLowerCase().replace(/\s+/g, '-')}`}
              >
                <img src={u.avatar} alt={u.name} />
                <span>{u.name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
