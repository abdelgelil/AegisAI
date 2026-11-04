import React from 'react';
import { Cpu, ShieldCheck, FlaskConical, FileCheck } from 'lucide-react';

const POINTS = [
  { Icon: ShieldCheck, text: 'Verify every sentence the AI writes against your own documents' },
  { Icon: FlaskConical, text: 'Test your chatbot against real attacks before you launch it' },
  { Icon: FileCheck, text: 'Export audit-ready compliance reports in one click' },
];

// Split screen: brand panel on the left (desktop only), form on the right.
export default function AuthLayout({ children, wide = false }) {
  return (
    <div className="min-h-screen grid lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)] bg-canvas text-ink font-sans">
      <aside className="hidden lg:flex flex-col justify-between bg-brand-strong text-canvas p-12">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-canvas/15 border border-canvas/30">
            <Cpu className="w-6 h-6" />
          </div>
          <span className="text-lg font-bold tracking-wide">AegisAI</span>
        </div>

        <div className="space-y-8">
          <h2 className="text-3xl font-semibold leading-tight">Trust every answer your AI gives.</h2>
          <ul className="space-y-4">
            {POINTS.map(({ Icon, text }) => (
              <li key={text} className="flex items-start gap-3 text-canvas/85">
                <Icon className="w-5 h-5 mt-0.5 shrink-0" />
                <span>{text}</span>
              </li>
            ))}
          </ul>
        </div>

        <p className="text-sm text-canvas/85">Enterprise LLM Trust &amp; Safety Platform</p>
      </aside>

      <main className="flex items-center justify-center px-4 py-10 sm:px-8">
        <div className={`w-full ${wide ? 'max-w-xl' : 'max-w-md'}`}>
          {/* Brand mark on small screens, where the side panel is hidden */}
          <div className="lg:hidden mb-8 flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-brand/10 border border-brand/30">
              <Cpu className="w-5 h-5 text-brand" />
            </div>
            <span className="font-bold tracking-wide">AegisAI</span>
          </div>
          {children}
        </div>
      </main>
    </div>
  );
}
