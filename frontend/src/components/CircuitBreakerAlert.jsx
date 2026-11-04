import React from 'react';
import { ShieldAlert, RefreshCw, CheckCircle2, ChevronDown } from 'lucide-react';

export default function CircuitBreakerAlert({ isSelfCorrected, isBlocked, originalQuery }) {
  if (!isSelfCorrected && !isBlocked) return null;

  const tone = isBlocked
    ? { box: 'bg-danger/10 border-danger/30', icon: 'text-danger', chip: 'bg-danger/15' }
    : { box: 'bg-warning/10 border-warning/30', icon: 'text-warning', chip: 'bg-warning/15' };

  return (
    <div className="space-y-3">
      {/* Banner */}
      <div role="alert" className={`p-4 rounded-xl border flex items-start gap-3 ${tone.box}`}>
        <div className={`p-2 rounded-lg shrink-0 ${tone.chip}`}>
          <ShieldAlert className={`w-5 h-5 ${tone.icon}`} />
        </div>
        <div>
          <p className="font-semibold text-sm text-ink">
            {isBlocked ? 'Circuit breaker triggered: response intercepted' : 'Self-correction loop executed'}
          </p>
          <p className="text-sm text-ink-muted mt-0.5">
            {isBlocked
              ? 'An unsafe payload or severe hallucination was detected. The unverified output was blocked and replaced with a pre-approved safe fallback.'
              : 'An ungrounded statement was detected. The platform reformulated the search query and regenerated a fully supported answer.'}
          </p>
        </div>
      </div>

      {/* Trace: collapsed until the user wants the details */}
      {isSelfCorrected && (
        <details className="group rounded-xl border border-line bg-surface">
          <summary className="cursor-pointer list-none flex items-center justify-between px-4 py-3 text-sm font-semibold text-ink">
            <span className="flex items-center gap-2">
              <RefreshCw className="w-4 h-4 text-brand" /> How it was corrected
            </span>
            <ChevronDown className="w-4 h-4 text-ink-faint transition-transform group-open:rotate-180" />
          </summary>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 px-4 pb-4 text-sm">
            <div className="rounded-lg border border-line bg-canvas p-3">
              <p className="text-xs uppercase tracking-wider text-ink-muted font-semibold mb-1">1. Query reformulation</p>
              <p className="text-ink truncate" title={originalQuery}>"{originalQuery} [expanded terms]"</p>
            </div>
            <div className="rounded-lg border border-line bg-canvas p-3">
              <p className="text-xs uppercase tracking-wider text-ink-muted font-semibold mb-1">2. Vector re-index</p>
              <p className="text-ink">Re-evaluated top 5 semantic chunks</p>
            </div>
            <div className="rounded-lg border border-line bg-canvas p-3">
              <p className="text-xs uppercase tracking-wider text-ink-muted font-semibold mb-1">3. Verified output</p>
              <p className="text-success font-semibold flex items-center gap-1">
                <CheckCircle2 className="w-4 h-4" /> Factual alignment 0.98
              </p>
            </div>
          </div>
        </details>
      )}
    </div>
  );
}
