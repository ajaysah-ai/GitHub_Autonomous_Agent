import { Check, X } from 'lucide-react';

export default function PlanDiffCard({ plan, onApprove, onCancel, disabled }) {
  const steps = (plan || []).filter(([name]) => name !== 'finish');

  return (
    <div className="diff-card">
      <div className="diff-head">
        <span>plan.diff</span>
        <span>{steps.length} step{steps.length === 1 ? '' : 's'}</span>
      </div>
      <div className="diff-body">
        {steps.length === 0 && <div className="diff-empty">// nothing to execute</div>}
        {steps.map(([name, args], i) => (
          <div className="diff-line add" key={i}>
            <span>+ {name}(</span>
            <span className="args">{Object.entries(args || {}).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(', ')}</span>
            <span>)</span>
          </div>
        ))}
      </div>
      <div className="approval-actions">
        <button className="btn btn-primary" onClick={onApprove} disabled={disabled}>
          <Check size={15} /> Approve &amp; run
        </button>
        <button className="btn btn-danger" onClick={onCancel} disabled={disabled}>
          <X size={15} /> Cancel task
        </button>
      </div>
    </div>
  );
}