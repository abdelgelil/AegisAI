import React, { useEffect, useRef, useState } from "react";
import {
  LayoutDashboard,
  FlaskConical,
  ShieldAlert,
  Database,
  FileCheck,
  Cpu,
  Activity,
  Menu,
  LogOut,
} from "lucide-react";
import { mockEvaluationResult, mockVulnerabilities } from "../mockData";
import { useAuth } from "./AuthContext";
import { canAccess, homeFor } from "./roles";
import Overview from "./Overview";
import EvaluatePage from "./EvaluatePage";
import VulnerabilityMatrix from "./VulnerabilityMatrix";
import KnowledgeBaseAnalysis from "./KnowledgeBaseAnalysis";
import ComplianceExporter from "./ComplianceExporter";

// Navigation is grouped by what the user is trying to do.
const NAV_GROUPS = [
  {
    title: "Monitor",
    items: [
      { id: "overview", label: "Overview", description: "System health at a glance.", Icon: LayoutDashboard },
    ],
  },
  {
    title: "Test",
    items: [
      {
        id: "evaluate",
        label: "Evaluate",
        description: "Test a prompt and see which sentences are supported by your knowledge base.",
        Icon: FlaskConical,
      },
    ],
  },
  {
    title: "Protect",
    items: [
      {
        id: "threats",
        label: "Threat Matrix",
        description: "Red-team results mapped to the OWASP Top 10 for LLM applications.",
        Icon: ShieldAlert,
      },
    ],
  },
  {
    title: "Data",
    items: [
      {
        id: "knowledge-base",
        label: "Knowledge Base",
        description: "Find conflicts, duplicates and outdated content before indexing.",
        Icon: Database,
      },
    ],
  },
  {
    title: "Report",
    items: [
      {
        id: "compliance",
        label: "Compliance",
        description: "Generate signed audit reports for the framework you choose.",
        Icon: FileCheck,
      },
    ],
  },
];

const initials = (name = "") =>
  name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("") || "?";

const verdictOf = (e) => (e.isBlocked ? "blocked" : e.isSelfCorrected ? "corrected" : "verified");

const toHistoryEntry = (e) => ({
  id: `${Date.now()}-${Math.random()}`,
  query: e.query,
  verdict: verdictOf(e),
  score: e.metrics?.overallTrustScore ?? null,
  time: new Date().toISOString(),
});

const readHash = () => window.location.hash.replace(/^#\/?/, "");

function Sidebar({ groups, route, onNavigate }) {
  return (
    <div className="flex h-full flex-col justify-between p-5">
      <div className="space-y-7">
        <div className="flex items-center gap-3 px-2 py-1">
          <div className="p-2 bg-brand/10 border border-brand/30 rounded-xl">
            <Cpu className="w-6 h-6 text-brand" />
          </div>
          <div>
            <p className="font-bold text-base tracking-wide text-ink">AegisAI</p>
            <p className="text-xs text-ink-muted">Governance Platform</p>
          </div>
        </div>

        <nav aria-label="Main" className="space-y-5">
          {groups.map((group) => (
            <div key={group.title}>
              <p className="px-2 mb-1.5 text-xs uppercase font-semibold tracking-wider text-ink-faint">
                {group.title}
              </p>
              <ul className="space-y-1">
                {group.items.map(({ id, label, Icon }) => {
                  const active = route === id;
                  return (
                    <li key={id}>
                      <a
                        href={`#/${id}`}
                        onClick={onNavigate}
                        aria-current={active ? "page" : undefined}
                        className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                          active
                            ? "bg-brand/10 text-ink font-semibold"
                            : "text-ink-muted font-medium hover:bg-raised hover:text-ink"
                        }`}
                      >
                        <Icon className={`w-5 h-5 shrink-0 ${active ? "text-brand" : "text-ink-faint"}`} />
                        {label}
                      </a>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>
      </div>

      <p className="px-2 text-xs text-ink-faint font-mono">AI Safety Engine v2.4</p>
    </div>
  );
}

export default function Dashboard() {
  const { user, logout } = useAuth();

  // Each role only sees its own pages
  const groups = NAV_GROUPS.map((group) => ({
    ...group,
    items: group.items.filter((item) => canAccess(user.role, item.id)),
  })).filter((group) => group.items.length > 0);
  const items = groups.flatMap((group) => group.items);
  const home = homeFor(user.role);

  // Hash routing: every page has an address (#/evaluate). A page the role may not open falls back to home.
  const [hash, setHash] = useState(readHash);
  useEffect(() => {
    const onChange = () => setHash(readHash());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  const route = items.some((item) => item.id === hash) ? hash : home;
  const item = items.find((i) => i.id === route) ?? items[0];
  const can = (pageId) => canAccess(user.role, pageId);

  // Keep the address bar honest (cosmetic: rendering never depends on it)
  useEffect(() => {
    if (hash !== route) window.location.hash = `/${route}`;
  }, [hash, route]);

  const [menuOpen, setMenuOpen] = useState(false);
  const scrollRef = useRef(null);
  const mainRef = useRef(null);

  // Evaluation state (shared by Overview, Evaluate and Compliance)
  const [evaluationData, setEvaluationData] = useState(mockEvaluationResult);
  const [history, setHistory] = useState(() => [toHistoryEntry(mockEvaluationResult)]);
  const [isLoading, setIsLoading] = useState(false);

  // Start every page at the top
  useEffect(() => {
    scrollRef.current?.scrollTo?.(0, 0);
  }, [route]);

  // Simulated AI Evaluation Runner
  const handleRunEvaluation = (newQuery, enableSelfCorrection) => {
    setIsLoading(true);

    setTimeout(() => {
      const isAdversarial = newQuery.toLowerCase().includes("ignore");
      const hasHallucination = newQuery.length % 2 === 0;

      const next = {
        query: newQuery,
        isBlocked: isAdversarial,
        isSelfCorrected: !isAdversarial && hasHallucination && enableSelfCorrection,
        rootCause: isAdversarial
          ? "Adversarial Prompt Injection Intercepted"
          : hasHallucination
          ? "Incomplete Vector Index Coverage (Resolved via Self-Correction)"
          : "None (Fully Grounded)",
        metrics: {
          overallTrustScore: isAdversarial ? 0.12 : 0.94,
          contextRelevance: isAdversarial ? 0.2 : 0.91,
          faithfulness: isAdversarial ? 0.1 : 0.96,
          factualGrounding: isAdversarial ? 0.05 : 0.95,
        },
        sentences: [
          {
            text: `Evaluation context regarding "${newQuery.slice(0, 30)}...".`,
            status: isAdversarial ? "hallucinated" : "grounded",
            score: isAdversarial ? 0.12 : 0.96,
            citation: "Source Document: Security_Policy_v2.pdf (Page 4)",
          },
          {
            text: "Additional factual context retrieved from vector embedding store.",
            status: isAdversarial ? "hallucinated" : "grounded",
            score: isAdversarial ? 0.15 : 0.92,
            citation: "Source Document: Knowledge_Base_Chunk_01.pdf (Page 12)",
          },
        ],
      };

      setEvaluationData(next);
      setHistory((prev) => [toHistoryEntry(next), ...prev].slice(0, 20));
      setIsLoading(false);
    }, 1200);
  };

  const signOut = async () => {
    await logout();
    window.location.hash = "/login";
  };

  return (
    <div className="flex h-screen bg-canvas text-ink font-sans overflow-hidden">
      {/* Skip link (keyboard users). preventDefault keeps the hash route unchanged. */}
      <a
        href="#main"
        onClick={(e) => {
          e.preventDefault();
          mainRef.current?.focus();
        }}
        className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:m-3 focus:rounded-lg focus:bg-brand-strong focus:px-4 focus:py-2 focus:text-sm focus:text-canvas"
      >
        Skip to content
      </a>

      {/* Desktop sidebar */}
      <aside className="hidden lg:block w-64 shrink-0 bg-surface border-r border-line">
        <Sidebar groups={groups} route={route} />
      </aside>

      {/* Mobile drawer */}
      {menuOpen && (
        <div className="lg:hidden fixed inset-0 z-40 flex">
          <div className="w-64 bg-surface border-r border-line">
            <Sidebar groups={groups} route={route} onNavigate={() => setMenuOpen(false)} />
          </div>
          <button
            type="button"
            aria-label="Close menu"
            onClick={() => setMenuOpen(false)}
            className="flex-1 bg-ink/40"
          />
        </div>
      )}

      <div ref={scrollRef} className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* Page header: title, one-line purpose, system status, signed-in user */}
        <header className="sticky top-0 z-10 border-b border-line bg-surface/90 backdrop-blur px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <button
              type="button"
              aria-label="Open menu"
              onClick={() => setMenuOpen(true)}
              className="lg:hidden p-2 -ml-2 rounded-lg text-ink-muted hover:bg-raised"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="min-w-0">
              <h1 className="text-xl font-semibold text-ink truncate">{item.label}</h1>
              <p className="text-sm text-ink-muted truncate">{item.description}</p>
            </div>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <div className="hidden md:flex items-center gap-2 bg-canvas px-3 py-1.5 rounded-lg border border-line text-xs">
              <Activity className="w-3.5 h-3.5 text-ink-faint" />
              <span className="text-ink-muted">Engine</span>
              <span className="flex items-center gap-1.5 text-success font-semibold">
                <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
                Online
              </span>
            </div>

            <div className="flex items-center gap-2.5 pl-3 border-l border-line">
              <span
                aria-hidden="true"
                className="flex h-9 w-9 items-center justify-center rounded-full bg-brand/10 border border-brand/30 text-sm font-semibold text-brand"
              >
                {initials(user.fullName)}
              </span>
              <div className="hidden sm:block leading-tight">
                <p className="text-sm font-medium text-ink">{user.fullName}</p>
                <p className="text-xs text-ink-muted">{user.position}</p>
              </div>
              <button
                type="button"
                onClick={signOut}
                aria-label="Sign out"
                title="Sign out"
                className="p-2 rounded-lg text-ink-muted hover:bg-raised hover:text-ink transition-colors"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        </header>

        <main
          id="main"
          ref={mainRef}
          tabIndex={-1}
          className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full space-y-6 outline-none"
        >
          {route === "overview" && (
            <Overview
              history={history}
              latest={evaluationData}
              vulnerabilities={mockVulnerabilities}
              can={can}
            />
          )}

          {route === "evaluate" && (
            <EvaluatePage
              evaluation={evaluationData}
              isLoading={isLoading}
              onEvaluate={handleRunEvaluation}
            />
          )}

          {route === "threats" && <VulnerabilityMatrix vulnerabilities={mockVulnerabilities} />}

          {route === "knowledge-base" && <KnowledgeBaseAnalysis />}

          {route === "compliance" && (
            <ComplianceExporter
              evaluationData={evaluationData}
              vulnerabilities={mockVulnerabilities}
            />
          )}
        </main>
      </div>
    </div>
  );
}
