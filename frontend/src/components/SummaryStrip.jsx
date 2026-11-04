import React from 'react';
import { ShieldCheck, ShieldAlert, RefreshCw } from 'lucide-react';

// Same green / amber / red as the sentence heatmap.
const VERDICTS = {
  verified: {
    label: 'Verified',
    note: 'Every sentence is supported by the knowledge base.',
    Icon: ShieldCheck,
    text: 'text-success',
    box: 'bg-success/10 border-success/30',
  },
  corrected: {
    label: 'Self-corrected',
    note: 'An ungrounded answer was detected and regenerated.',
    Icon: RefreshCw,
    text: 'text-warning',
    box: 'bg-warning/10 border-warning/30',
  },
  blocked: {
    label: 'Blocked',
    note: 'The request was intercepted by the circuit breaker.',
    Icon: ShieldAlert,
    text: 'text-danger',
    box: 'bg-danger/10 border-danger/30',
  },
};

const scoreColor = (score) =>
  score >= 0.85 ? 'text-success' : score >= 0.7 ? 'text-warning' : 'text-danger';

export default function SummaryStrip({ evaluation }) {
  const { isBlocked, isSelfCorrected, metrics = {}, sentences = [] } = evaluation;

  const verdict = VERDICTS[isBlocked ? 'blocked' : isSelfCorrected ? 'corrected' : 'verified'];
  const trust = metrics.overallTrustScore;
  const grounded = sentences.filter((s) => s.status === 'grounded').length;

  return (
    <div className="grid grid-cols-2 gap-4">
      {/* Verdict */}
      <div className={`col-span-2 rounded-xl border p-4 flex items-center gap-4 ${verdict.box}`}>
        <verdict.Icon className={`w-8 h-8 shrink-0 ${verdict.text}`} />
        <div>
          <p className="text-xs uppercase tracking-wider text-ink-muted font-semibold">Verdict</p>
          <p className={`text-xl font-bold ${verdict.text}`}>{verdict.label}</p>
          <p className="text-sm text-ink-muted mt-0.5">{verdict.note}</p>
        </div>
      </div>

      <div className="rounded-xl border border-line bg-surface p-4">
        <p className="text-xs uppercase tracking-wider text-ink-muted font-semibold">Trust Score</p>
        <p className={`text-3xl font-bold font-mono mt-1 ${trust == null ? 'text-ink-faint' : scoreColor(trust)}`}>
          {trust == null ? '—' : `${Math.round(trust * 100)}%`}
        </p>
      </div>

      <div className="rounded-xl border border-line bg-surface p-4">
        <p className="text-xs uppercase tracking-wider text-ink-muted font-semibold">Grounded Sentences</p>
        <p className="text-3xl font-bold font-mono mt-1 text-ink">
          {grounded}
          <span className="text-ink-faint text-xl"> / {sentences.length}</span>
        </p>
      </div>
    </div>
  );
}
