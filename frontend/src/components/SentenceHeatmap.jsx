import React, { useState } from 'react';
import { FileText, CheckCircle2, AlertTriangle, XCircle, Info } from 'lucide-react';

// One place that defines how each grounding status looks.
const STATUS = {
  grounded: {
    label: 'Grounded',
    legend: 'Grounded (verified)',
    Icon: CheckCircle2,
    badge: 'bg-success/15 text-success border-success/30',
    hover: 'hover:bg-success/25',
    text: 'text-success',
    dot: 'bg-success',
  },
  unverified: {
    label: 'Unverified',
    legend: 'Unverified / partial',
    Icon: AlertTriangle,
    badge: 'bg-warning/15 text-warning border-warning/30',
    hover: 'hover:bg-warning/25',
    text: 'text-warning',
    dot: 'bg-warning',
  },
  hallucinated: {
    label: 'Hallucinated',
    legend: 'Hallucinated / fabricated',
    Icon: XCircle,
    badge: 'bg-danger/15 text-danger border-danger/30',
    hover: 'hover:bg-danger/25',
    text: 'text-danger',
    dot: 'bg-danger',
  },
};

const FALLBACK = {
  label: 'Unknown',
  Icon: Info,
  badge: 'bg-raised text-ink border-line-strong',
  hover: 'hover:bg-line',
  text: 'text-ink-muted',
  dot: 'bg-ink-faint',
};

export default function SentenceHeatmap({ sentences = [], query }) {
  // First sentence is selected on load so the evidence is never empty.
  // The parent passes a `key`, so this resets when a new evaluation arrives.
  const [selected, setSelected] = useState(sentences[0] ?? null);
  const selectedStatus = selected ? STATUS[selected.status] ?? FALLBACK : null;

  return (
    <section className="bg-surface border border-line rounded-xl p-5">
      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 mb-4 border-b border-line">
        <h2 className="text-base font-semibold text-ink flex items-center gap-2">
          <FileText className="w-5 h-5 text-brand" /> Sentence-level verification
        </h2>
        <span className="text-xs text-ink-muted">Click a sentence to see its source</span>
      </div>

      <p className="mb-3 text-sm text-ink-muted">
        <span className="font-semibold text-ink">Prompt: </span>"{query}"
      </p>

      {/* Sentences */}
      <div className="flex flex-col items-start gap-2">
        {sentences.map((item, idx) => {
          const s = STATUS[item.status] ?? FALLBACK;
          const isSelected = selected?.text === item.text;
          return (
            <button
              key={idx}
              type="button"
              onClick={() => setSelected(item)}
              aria-pressed={isSelected}
              className={`text-left text-sm border px-3 py-2 rounded-lg transition-colors ${s.badge} ${s.hover} ${
                isSelected ? 'ring-2 ring-brand ring-offset-2 ring-offset-surface' : ''
              }`}
            >
              <s.Icon className="w-4 h-4 inline mr-1.5 -mt-0.5" />
              {item.text}
            </button>
          );
        })}
      </div>

      {/* Evidence for the selected sentence */}
      <div className="mt-4 rounded-lg border border-line bg-canvas p-4" aria-live="polite">
        {selected ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs uppercase tracking-wider text-ink-muted font-semibold">Evidence</p>
              <div className="flex items-center gap-2">
                <span className={`text-lg font-bold font-mono ${selectedStatus.text}`}>
                  {(selected.score * 100).toFixed(0)}%
                </span>
                <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${selectedStatus.badge}`}>
                  {selectedStatus.label}
                </span>
              </div>
            </div>
            <p className="text-sm text-ink-muted">Source attribution</p>
            <p className="text-sm text-ink font-mono leading-relaxed -mt-2">{selected.citation}</p>
          </div>
        ) : (
          <p className="text-sm text-ink-muted">Select a sentence to see its supporting source chunk.</p>
        )}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-2 mt-4 pt-3 border-t border-line text-xs text-ink-muted">
        {Object.entries(STATUS).map(([key, s]) => (
          <span key={key} className="flex items-center gap-1.5">
            <span className={`w-2.5 h-2.5 rounded-full ${s.dot}`} /> {s.legend}
          </span>
        ))}
      </div>
    </section>
  );
}
