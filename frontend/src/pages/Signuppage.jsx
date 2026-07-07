import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Terminal, Info } from 'lucide-react';
import { useAuth } from '../context/Authcontext.jsx';
import { ApiError } from '../api/client.js';

export default function SignupPage() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: '', password: '', github_token: '', groq_api_key: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await signup(form);
      navigate('/chat/new');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Sign up failed. Please try again.');
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
          <h1 className="auth-title">Create account</h1>
          <p className="auth-sub">Your GitHub token and Groq key are collected once, here — never asked again mid-task.</p>

          {error && <div className="error-banner">{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="field">
              <label className="label">Username</label>
              <input className="input" value={form.username} autoFocus minLength={3}
                onChange={(e) => update('username', e.target.value)} required />
            </div>
            <div className="field">
              <label className="label">Password</label>
              <input className="input" type="password" value={form.password} minLength={6}
                onChange={(e) => update('password', e.target.value)} required />
            </div>
            <div className="field">
              <label className="label">GitHub personal access token</label>
              <input className="input" type="password" value={form.github_token} placeholder="ghp_..."
                onChange={(e) => update('github_token', e.target.value)} required />
            </div>
            <div className="field">
              <label className="label">Groq API key</label>
              <input className="input" type="password" value={form.groq_api_key} placeholder="gsk_..."
                onChange={(e) => update('groq_api_key', e.target.value)} required />
            </div>
            <div style={{ display: 'flex', gap: 8, color: 'var(--text-faint)', fontSize: '0.78rem', marginBottom: 18 }}>
              <Info size={14} style={{ flexShrink: 0, marginTop: 1 }} />
              <span>Both are encrypted before storage and only decrypted server-side when a task actually runs.</span>
            </div>
            <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: '100%', justifyContent: 'center' }}>
              {loading ? <span className="spinner" /> : 'Create account'}
            </button>
          </form>
        </div>
        <div className="auth-switch">
          Already have an account? <Link to="/login"><button type="button">Log in</button></Link>
        </div>
        <div className="auth-switch">
          <Link to="/about"><button type="button">How to get GitHub Personal Access Token & Groq API Key</button></Link>
        </div>
      </div>
    </div>
  );
}
