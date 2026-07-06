import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Terminal } from 'lucide-react';
import { useAuth } from '../context/Authcontext.jsx';
import { ApiError } from '../api/client.js';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(form);
      navigate('/chat/new');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="nav-brand" style={{ justifyContent: 'center', padding: '0 0 18px' }}>
          <Terminal size={18} /> agent.console
        </div>
        <div className="card">
          <h1 className="auth-title">Log in</h1>
          <p className="auth-sub">Resume where you left off — history, files, and credentials are already set up.</p>

          {error && <div className="error-banner">{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="field">
              <label className="label">Username</label>
              <input className="input" value={form.username} autoFocus
                onChange={(e) => setForm({ ...form, username: e.target.value })} required />
            </div>
            <div className="field">
              <label className="label">Password</label>
              <input className="input" type="password" value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })} required />
            </div>
            <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: '100%', justifyContent: 'center' }}>
              {loading ? <span className="spinner" /> : 'Log in'}
            </button>
          </form>
        </div>
        <div className="auth-switch">
          No account yet? <Link to="/signup"><button type="button">Sign up</button></Link>
        </div>
        <div className="auth-switch">
          <Link to="/about"><button type="button">About this agent</button></Link>
        </div>
      </div>
    </div>
  );
}