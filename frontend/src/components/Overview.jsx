import React from 'react';
import { ArrowRight, FlaskConical } from 'lucide-react';

const VERDICT_BADGE = {
  verified: { label: 'Verified', cls: 'bg-success/15 text-success border-success/30' },
  corrected: { label: 'Self-corrected', cls: 'bg-warning/15 text-warning border-warning/30' },
  blocked: { label: 'Blocked', cls: 'bg-danger/15 text-danger border-danger/30' },
};

const SEVERITY_BADGE = {
  Critical: 'bg-danger/15 text-danger border-danger/30',
  High: 'bg-warning/15 text-warning border-warning/30',
  Medium: 'bg-raised text-ink border-line-strong',
};

const scoreColor = (score) =>
  score == null ? 'text-ink-faint' : score >= 0.85 ? 'text-success' : score >= 0.7 ? 'text-warning' : 'text-danger';

// Demo values. They mirror the mock data on the Knowledge Base and Compliance pages.
const KB_HEALTH = 81;
const COMPLIANCE_READINESS = 92.4;
const KB_ATTENTION = [
  { id: 'kb-1', title: 'Conflicting password-reset SLAs', meta: 'Support FAQ vs Security Policy', severity: 'High', page: 'knowledge-base' },
  { id: 'kb-2', title: 'Outdated API documentation', meta: 'Legacy_API_Documentation_2023.pdf', severity: 'High', page: 'knowledge-base' },
];

// Renders a link only when the signed-in role may open that page; otherwise a plain box.
function Linked({ href, className, children }) {
  return href ? (
    <a href={href} className={className}>{children}</a>
  ) : (
    <div className={className}>{children}</div>
  );
}

function Kpi({ href, label, value, tone = 'text-ink', hint }) {
  return (
    <Linked
      href={href}
      className={`group rounded-xl border border-line bg-surface p-4 transition-colors ${href ? 'hover:border-line-strong' : ''}`}
    >
      <p className="text-xs uppercase tracking-wider text-ink-muted font-semibold">{label}</p>
      <p className={`text-3xl font-bold font-mono mt-1 ${tone}`}>{value}</p>
      <p className="text-xs text-ink-faint mt-1 flex items-center gap-1">
        {hint}
        {href && <ArrowRight className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />}
      </p>
    </Linked>
  );
}

export default function Overview({ history = [], latest, vulnerabilities = [], can = () => true }) {
  const link = (page) => (can(page) ? `#/${page}` : undefined);

  const sentences = latest?.sentences ?? [];
  const grounded = sentences.filter((s) => s.status === 'grounded').length;
  const groundedPct = sentences.length ? Math.round((grounded / sentences.length) * 100) : null;
  const trust = latest?.metrics?.overallTrustScore ?? null;
  const blockedInSession = history.filter((h) => h.verdict === 'blocked').length;

  const attention = [
    ...KB_ATTENTION,
    ...vulnerabilities
      .filter((v) => v.severity === 'Critical' || v.severity === 'High')
      .slice(0, 2)
      .map((v) => ({ id: v.id, title: v.type, meta: v.owaspCategory, severity: v.severity, page: 'threats' })),
  ];

  return (
    <div className="space-y-6">
      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <Kpi
          href={link('evaluate')}
          label="Trust Score"
          value={trust == null ? '—' : `${Math.round(trust * 100)}%`}
          tone={scoreColor(trust)}
          hint="Latest evaluation"
        />
        <Kpi
          href={link('threats')}
          label="Threats Blocked"
          value={vulnerabilities.length + blockedInSession}
          hint="Red-team + live"
        />
        <Kpi
          href={link('evaluate')}
          label="Grounded"
          value={groundedPct == null ? '—' : `${groundedPct}%`}
          tone={scoreColor(groundedPct == null ? null : groundedPct / 100)}
          hint="Sentences verified"
        />
        <Kpi href={link('knowledge-base')} label="KB Health" value={`${KB_HEALTH}%`} tone="text-warning" hint="Pre-index scan" />
        <Kpi
          href={link('compliance')}
          label="Compliance"
          value={`${COMPLIANCE_READINESS}%`}
          tone="text-success"
          hint="Controls passed"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Recent evaluations */}
        <section className="lg:col-span-7 bg-surface border border-line rounded-xl p-5">
          <div className="flex items-center justify-between gap-3 pb-3 mb-3 border-b border-line">
            <h2 className="text-base font-semibold text-ink">Recent evaluations</h2>
            {can('evaluate') && (
              <a
                href="#/evaluate"
                className="inline-flex items-center gap-1.5 rounded-lg bg-brand-strong hover:bg-brand text-canvas px-3 py-1.5 text-xs font-semibold transition-colors"
              >
                <FlaskConical className="w-3.5 h-3.5" /> New evaluation
              </a>
            )}
          </div>

          {history.length === 0 ? (
            <p className="py-8 text-center text-sm text-ink-muted">No evaluations yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase tracking-wider text-ink-muted">
                  <tr>
                    <th className="py-2 pr-3 font-semibold">Prompt</th>
                    <th className="py-2 pr-3 font-semibold">Verdict</th>
                    <th className="py-2 pr-3 font-semibold text-right">Score</th>
                    <th className="py-2 font-semibold text-right">Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {history.slice(0, 6).map((h) => {
                    const badge = VERDICT_BADGE[h.verdict];
                    return (
                      <tr key={h.id}>
                        <td className="py-2.5 pr-3 text-ink max-w-[16rem] truncate" title={h.query}>
                          {h.query}
                        </td>
                        <td className="py-2.5 pr-3">
                          <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${badge.cls}`}>
                            {badge.label}
                          </span>
                        </td>
                        <td className={`py-2.5 pr-3 text-right font-mono font-semibold ${scoreColor(h.score)}`}>
                          {h.score == null ? '—' : `${Math.round(h.score * 100)}%`}
                        </td>
                        <td className="py-2.5 text-right text-ink-muted font-mono text-xs">
                          {new Date(h.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* Needs attention */}
        <section className="lg:col-span-5 bg-surface border border-line rounded-xl p-5">
          <h2 className="text-base font-semibold text-ink pb-3 mb-3 border-b border-line">Needs attention</h2>
          <ul className="space-y-2">
            {attention.map((entry) => (
              <li key={entry.id}>
                <Linked
                  href={link(entry.page)}
                  className={`flex items-center justify-between gap-3 rounded-lg border border-line bg-canvas px-3 py-2.5 transition-colors ${
                    link(entry.page) ? 'hover:border-line-strong' : ''
                  }`}
                >
                  <span className="min-w-0">
                    <span className="block text-sm font-medium text-ink truncate">{entry.title}</span>
                    <span className="block text-xs text-ink-muted truncate">{entry.meta}</span>
                  </span>
                  <span
                    className={`shrink-0 text-xs font-semibold px-2 py-0.5 rounded border ${
                      SEVERITY_BADGE[entry.severity] ?? 'bg-raised text-ink-muted border-line'
                    }`}
                  >
                    {entry.severity}
                  </span>
                </Linked>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
