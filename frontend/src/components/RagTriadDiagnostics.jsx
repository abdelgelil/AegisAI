import React from 'react';
import { Gauge } from 'lucide-react';

const barColor = (score) => (score >= 0.85 ? 'bg-success' : score >= 0.7 ? 'bg-warning' : 'bg-danger');
const textColor = (score) => (score >= 0.85 ? 'text-success' : score >= 0.7 ? 'text-warning' : 'text-danger');

export default function RagTriadDiagnostics({ metrics = {}, rootCause }) {
  const items = [
    {
      title: 'Context relevance',
      hint: 'Quality of documents retrieved from the vector store',
      score: metrics.contextRelevance ?? 0,
    },
    {
      title: 'Faithfulness',
      hint: 'Factual alignment with the retrieved knowledge',
      score: metrics.faithfulness ?? 0,
    },
    {
      title: 'Question answered',
      hint: 'Directness and completeness relative to the prompt',
      score: metrics.factualGrounding ?? 0,
    },
  ];

  return (
    <section className="bg-surface border border-line rounded-xl p-5">
      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 mb-4 border-b border-line">
        <h2 className="text-base font-semibold text-ink flex items-center gap-2">
          <Gauge className="w-5 h-5 text-brand" /> RAG triad diagnostics
        </h2>
        <p className="text-xs text-ink-muted">
          Root cause: <span className="font-semibold text-ink">{rootCause}</span>
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {items.map((item) => (
          <div key={item.title} title={item.hint} className="rounded-lg border border-line bg-canvas p-3">
            <div className="flex items-baseline justify-between gap-2">
              <span className="text-sm font-medium text-ink">{item.title}</span>
              <span className={`text-sm font-bold font-mono ${textColor(item.score)}`}>
                {(item.score * 100).toFixed(0)}%
              </span>
            </div>
            <div className="mt-2 h-2 w-full rounded-full bg-raised overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${barColor(item.score)}`}
                style={{ width: `${item.score * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
