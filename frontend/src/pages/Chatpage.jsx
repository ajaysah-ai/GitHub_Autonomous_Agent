import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { Send, CheckCircle2, XCircle, Ban } from 'lucide-react';
import { useAuth } from '../context/Authcontext.jsx';
import { useToast } from '../context/Toastcontext.jsx';
import { api, ApiError } from '../api/client.js';
import MessageList from '../components/Messagelist.jsx';
import PlanDiffCard from '../components/Plandiffcard.jsx';
import FeedbackModal from '../components/FeedbackModel.jsx';

const TERMINAL = { completed: true, blocked: true, cancelled: true, ended: true };

export default function ChatPage() {
  const { threadId: routeThreadId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { token } = useAuth();
  const { showToast } = useToast();

  const [threadId, setThreadId] = useState(routeThreadId !== 'new' ? routeThreadId : null);
  const [messages, setMessages] = useState([]);
  const [status, setStatus] = useState(routeThreadId === 'new' ? 'new' : 'loading');
  const [prompt, setPrompt] = useState(null);
  const [plan, setPlan] = useState(null);
  const [goalDraft, setGoalDraft] = useState('');
  const [replyDraft, setReplyDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [feedbackOpen, setFeedbackOpen] = useState(false);

  const applyResult = useCallback((tid, result) => {
    setThreadId(tid);
    setMessages(result.messages || []);
    setStatus(result.status);
    setPrompt(result.prompt || null);
    setPlan(result.plan || null);
  }, []);

  // Fresh "seed" passed via navigation state (right after starting a goal).
  useEffect(() => {
    if (location.state?.seed) {
      applyResult(location.state.seed.thread_id, location.state.seed);
    }
  }, [location.state, applyResult]);

  // Reload path: opened directly via a thread_id with no seed (e.g. from History).
  useEffect(() => {
    if (routeThreadId !== 'new' && !location.state?.seed && token) {
      (async () => {
        try {
          const res = await api.getThread(token, routeThreadId);
          setThreadId(routeThreadId);
          setMessages(res.messages || []);
          setStatus(res.awaiting_input ? 'awaiting_input' : res.completed ? 'completed' : 'ended');
        } catch (err) {
          setError(err instanceof ApiError ? err.message : 'Could not load this task.');
        }
      })();
    }
  }, [routeThreadId, location.state, token]);

  async function handleStart(e) {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      const result = await api.startGoal(token, goalDraft);
      navigate(`/chat/${result.thread_id}`, { state: { seed: result } });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not start this goal.');
    } finally {
      setBusy(false);
    }
  }

  async function handleReply(value) {
    setError('');
    setBusy(true);
    try {
      const result = await api.resumeGoal(token, threadId, value);
      applyResult(threadId, result);
      setReplyDraft('');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not send your reply.');
    } finally {
      setBusy(false);
    }
  }

  if (status === 'new') {
    return (
      <div>
        <div className="page-header">
          <h1 className="page-title">New goal</h1>
          <p className="page-subtitle">Describe what you want done — the agent plans, reviews itself, then asks for one approval before running anything.</p>
        </div>
        {error && <div className="error-banner">{error}</div>}
        <form onSubmit={handleStart} className="card">
          <div className="field">
            <label className="label">Goal</label>
            <textarea className="textarea" rows={3} autoFocus value={goalDraft}
              placeholder="create repo 'my-new-project'"
              onChange={(e) => setGoalDraft(e.target.value)} required />
          </div>
          <button className="btn btn-primary" type="submit" disabled={busy}>
            {busy ? <span className="spinner" /> : <><Send size={15} /> Send</>}
          </button>
        </form>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Task</h1>
        <StatusBadge status={status} />
      </div>

      {error && <div className="error-banner">{error}</div>}

      <MessageList messages={messages} />

      {status === 'awaiting_clarification' && prompt && (
        <>
          <div className="clarify-card">{prompt}</div>
          <ReplyBox value={replyDraft} onChange={setReplyDraft} onSend={() => handleReply(replyDraft)} busy={busy} placeholder="Add the missing details..." />
        </>
      )}

      {status === 'awaiting_approval' && (
        <PlanDiffCard
          plan={plan}
          disabled={busy}
          onApprove={() => handleReply('yes')}
          onCancel={() => handleReply('no')}
        />
      )}

      {status === 'awaiting_input' && (
        <ReplyBox value={replyDraft} onChange={setReplyDraft} onSend={() => handleReply(replyDraft)} busy={busy} placeholder="Continue this task..." />
      )}


      {TERMINAL[status] && (
        <div className="card" style={{ marginTop: 8, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--text-dim)', fontSize: '0.85rem' }}>
            {status === 'completed' ? 'Task finished.' : 'Task ended.'}
          </span>
          {threadId && (
            <button className="btn" onClick={() => setFeedbackOpen(true)}>Leave feedback</button>
          )}
        </div>
      )}

      {feedbackOpen && (
        <FeedbackModal
          threadId={threadId}
          onClose={() => setFeedbackOpen(false)}
          onSubmitted={() => { setFeedbackOpen(false); showToast('Feedback saved', 'ok'); }}
        />
      )}
    </div>
  );
}

function StatusBadge({ status }) {
  const map = {
    awaiting_clarification: ['badge-pending', 'Needs details'],
    awaiting_approval: ['badge-pending', 'Awaiting approval'],
    awaiting_input: ['badge-pending', 'Awaiting your reply'],
    completed: ['badge-ok', 'Completed'],
    blocked: ['badge-danger', 'Blocked'],
    cancelled: ['badge-danger', 'Cancelled'],
    ended: ['badge-neutral', 'Ended'],
    loading: ['badge-neutral', 'Loading...'],
  };
  const [cls, label] = map[status] || ['badge-neutral', status];
  const Icon = status === 'completed' ? CheckCircle2 : status === 'blocked' ? XCircle : status === 'cancelled' ? Ban : null;
  return <span className={`badge ${cls}`}>{Icon && <Icon size={12} />} {label}</span>;
}

function ReplyBox({ value, onChange, onSend, busy, placeholder }) {
  return (
    <div className="goal-input-row">
      <textarea className="textarea" rows={2} value={value} placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); if (value.trim()) onSend(); } }} />
      <button className="btn btn-primary" onClick={onSend} disabled={busy || !value.trim()}>
        {busy ? <span className="spinner" /> : <Send size={15} />}
      </button>
    </div>
  );
}