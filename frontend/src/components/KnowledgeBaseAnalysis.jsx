import React, { useMemo, useRef, useState } from 'react';
import { UploadCloud, FileText, RefreshCw, AlertTriangle } from 'lucide-react';

const INITIAL_DOCS = [
  { id: 'DOC-001', name: 'Enterprise_Security_Policy_v2.pdf', size: '2.4 MB', chunks: 42, qualityScore: 98, status: 'Ready', issuesCount: 0, lastUpdated: '2026-08-15' },
  { id: 'DOC-002', name: 'Legacy_API_Documentation_2023.pdf', size: '5.1 MB', chunks: 110, qualityScore: 62, status: 'Outdated file', issuesCount: 2, lastUpdated: '2023-11-04' },
  { id: 'DOC-003', name: 'Customer_Support_FAQ_Final.docx', size: '1.2 MB', chunks: 28, qualityScore: 74, status: 'Conflicting sources', issuesCount: 3, lastUpdated: '2026-07-20' },
  { id: 'DOC-004', name: 'Internal_HR_Benefits_Guide_2026.pdf', size: '3.8 MB', chunks: 85, qualityScore: 91, status: 'Duplicate text', issuesCount: 1, lastUpdated: '2026-09-01' },
];

const ISSUES = [
  {
    id: 'ISSUE-101', kind: 'conflict', type: 'Conflicting information', severity: 'High',
    docA: 'Customer_Support_FAQ_Final.docx (chunk #12)', docB: 'Enterprise_Security_Policy_v2.pdf (chunk #04)',
    details: 'Contradictory password reset SLAs: chunk #12 states "24 hours" while chunk #04 states "1 hour max".',
    recommendation: 'Deprecate chunk #12 in the Support FAQ or sync it with the Security Policy.',
  },
  {
    id: 'ISSUE-102', kind: 'duplicate', type: 'Duplicate chunk text', severity: 'Medium',
    docA: 'Internal_HR_Benefits_Guide_2026.pdf (chunk #44)', docB: 'Internal_HR_Benefits_Guide_2026.pdf (chunk #45)',
    details: 'Exact 100% vector embedding duplicate found across contiguous chunks.',
    recommendation: 'Deduplicate the vector index to improve retrieval latency.',
  },
  {
    id: 'ISSUE-103', kind: 'outdated', type: 'Outdated text', severity: 'High',
    docA: 'Legacy_API_Documentation_2023.pdf (all chunks)', docB: null,
    details: 'File timestamp is over 1000 days old and references deprecated OAuth 1.0 endpoints.',
    recommendation: 'Exclude this file before generating the RAG index.',
  },
  {
    id: 'ISSUE-104', kind: 'format', type: 'Formatting & encoding', severity: 'Low',
    docA: 'Customer_Support_FAQ_Final.docx (chunk #22)', docB: null,
    details: 'Unparsed special characters and broken table markup detected.',
    recommendation: 'Apply a UTF-8 sanitization filter before chunking.',
  },
];

const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'conflict', label: 'Conflicts' },
  { key: 'duplicate', label: 'Duplicates' },
  { key: 'outdated', label: 'Outdated' },
  { key: 'format', label: 'Formatting' },
];

const SEV_ORDER = { High: 0, Medium: 1, Low: 2 };
const SEV_BADGE = {
  High: 'bg-danger/15 text-danger border-danger/30',
  Medium: 'bg-warning/15 text-warning border-warning/30',
  Low: 'bg-raised text-ink-muted border-line-strong',
};
const qualityBadge = (q) =>
  q >= 90
    ? 'bg-success/15 text-success border-success/30'
    : q >= 70
    ? 'bg-warning/15 text-warning border-warning/30'
    : 'bg-danger/15 text-danger border-danger/30';

export default function KnowledgeBaseAnalysis() {
  const [documents, setDocuments] = useState(INITIAL_DOCS);
  const [filter, setFilter] = useState('all');
  const [isScanning, setIsScanning] = useState(false);
  const fileInput = useRef(null);

  const count = (kind) => ISSUES.filter((i) => i.kind === kind).length;
  const health = useMemo(
    () => Math.round(documents.reduce((sum, d) => sum + d.qualityScore, 0) / documents.length),
    [documents]
  );
  const healthTone = health >= 90 ? 'text-success' : health >= 70 ? 'text-warning' : 'text-danger';

  const issues = ISSUES.filter((i) => filter === 'all' || i.kind === filter).sort(
    (a, b) => SEV_ORDER[a.severity] - SEV_ORDER[b.severity]
  );

  // Uses the real file names and sizes. Chunk counts and quality scores are mocked.
  const handleFiles = (e) => {
    const files = Array.from(e.target.files ?? []);
    e.target.value = '';
    if (files.length === 0) return;
    setIsScanning(true);
    setTimeout(() => {
      const added = files.map((file, i) => ({
        id: `DOC-${Date.now()}-${i}`,
        name: file.name,
        size: `${(file.size / (1024 * 1024)).toFixed(1)} MB`,
        chunks: Math.max(5, Math.round(file.size / 50000)),
        qualityScore: 85 + (file.size % 14),
        status: 'Ready',
        issuesCount: 0,
        lastUpdated: new Date().toISOString().slice(0, 10),
      }));
      setDocuments((prev) => [...added, ...prev]);
      setIsScanning(false);
    }, 1200);
  };

  const kpis = [
    { label: 'Corpus health', value: `${health}%`, tone: healthTone, hint: `${documents.length} documents` },
    { label: 'Conflicts', value: count('conflict'), tone: 'text-danger', hint: 'Contradictory facts' },
    { label: 'Duplicates', value: count('duplicate'), tone: 'text-warning', hint: 'Identical chunks' },
    { label: 'Outdated', value: count('outdated'), tone: 'text-danger', hint: 'Older than 3 years' },
  ];

  return (
    <div className="space-y-6">
      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map((k) => (
          <div key={k.label} className="rounded-xl border border-line bg-surface p-4">
            <p className="text-xs uppercase tracking-wider text-ink-muted font-semibold">{k.label}</p>
            <p className={`text-3xl font-bold font-mono mt-1 ${k.tone}`}>{k.value}</p>
            <p className="text-xs text-ink-faint mt-1">{k.hint}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Issues: the main task, so it comes first */}
        <section className="lg:col-span-7 bg-surface border border-line rounded-xl p-5">
          <div className="flex flex-wrap items-center justify-between gap-3 pb-3 mb-4 border-b border-line">
            <h2 className="text-base font-semibold text-ink">Issues to fix before indexing</h2>
            <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filter issues">
              {FILTERS.map((f) => (
                <button
                  key={f.key}
                  type="button"
                  aria-pressed={filter === f.key}
                  onClick={() => setFilter(f.key)}
                  className={`px-2.5 py-1 rounded-md border text-xs font-medium transition-colors ${
                    filter === f.key
                      ? 'bg-brand/10 border-brand text-ink'
                      : 'bg-canvas border-line text-ink-muted hover:text-ink hover:border-line-strong'
                  }`}
                >
                  {f.label}
                  {f.key !== 'all' && <span className="ml-1 text-ink-faint">{count(f.key)}</span>}
                </button>
              ))}
            </div>
          </div>

          {issues.length === 0 ? (
            <p className="py-8 text-center text-sm text-ink-muted">No issues in this category.</p>
          ) : (
            <ul className="space-y-3">
              {issues.map((issue) => (
                <li key={issue.id} className="rounded-lg border border-line bg-canvas p-4 space-y-2.5">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-semibold text-ink flex items-center gap-1.5">
                      <AlertTriangle className="w-4 h-4 text-warning" /> {issue.type}
                    </span>
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${SEV_BADGE[issue.severity]}`}>
                      {issue.severity}
                    </span>
                  </div>
                  <p className="text-sm text-ink-muted">{issue.details}</p>
                  <div className="text-xs font-mono text-ink-muted space-y-0.5">
                    <p className="truncate" title={issue.docA}>A: {issue.docA}</p>
                    {issue.docB && <p className="truncate" title={issue.docB}>B: {issue.docB}</p>}
                  </div>
                  <p className="text-sm text-ink pt-2 border-t border-line">
                    <span className="font-semibold text-brand">Fix: </span>
                    {issue.recommendation}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Documents */}
        <section className="lg:col-span-5 bg-surface border border-line rounded-xl p-5">
          <div className="flex items-center justify-between gap-3 pb-3 mb-4 border-b border-line">
            <h2 className="text-base font-semibold text-ink">Documents</h2>
            <button
              type="button"
              disabled={isScanning}
              onClick={() => fileInput.current?.click()}
              className="inline-flex items-center gap-1.5 rounded-lg bg-brand-strong hover:bg-brand disabled:bg-raised disabled:text-ink-muted text-canvas px-3 py-1.5 text-xs font-semibold transition-colors"
            >
              {isScanning ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Scanning...
                </>
              ) : (
                <>
                  <UploadCloud className="w-3.5 h-3.5" /> Add documents
                </>
              )}
            </button>
            <input
              ref={fileInput}
              type="file"
              multiple
              accept=".pdf,.docx,.txt,.md"
              onChange={handleFiles}
              className="hidden"
            />
          </div>

          <ul className="space-y-2.5">
            {documents.map((doc) => (
              <li key={doc.id} className="rounded-lg border border-line bg-canvas p-3 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-start gap-2 min-w-0">
                    <FileText className="w-4 h-4 text-ink-faint shrink-0 mt-0.5" />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-ink truncate" title={doc.name}>{doc.name}</p>
                      <p className="text-xs text-ink-muted font-mono">
                        {doc.size} · {doc.chunks} chunks
                      </p>
                    </div>
                  </div>
                  <span className={`shrink-0 text-xs font-semibold px-2 py-0.5 rounded border ${qualityBadge(doc.qualityScore)}`}>
                    {doc.qualityScore}%
                  </span>
                </div>
                <div className="flex justify-between items-center text-xs text-ink-muted pt-2 border-t border-line">
                  <span>{doc.status} · {doc.lastUpdated}</span>
                  <span className={doc.issuesCount > 0 ? 'text-warning font-semibold' : 'text-success'}>
                    {doc.issuesCount} {doc.issuesCount === 1 ? 'issue' : 'issues'}
                  </span>
                </div>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-ink-faint">Accepted: PDF, DOCX, TXT, MD</p>
        </section>
      </div>
    </div>
  );
}
