import React from 'react';
import PromptPlayground from './PromptPlayground';
import SummaryStrip from './SummaryStrip';
import CircuitBreakerAlert from './CircuitBreakerAlert';
import SentenceHeatmap from './SentenceHeatmap';
import RagTriadDiagnostics from './RagTriadDiagnostics';

// Input on the left, result on the right: everything fits one screen without scrolling.
export default function EvaluatePage({ evaluation, isLoading, onEvaluate }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      <div className="lg:col-span-5 lg:sticky lg:top-28">
        <PromptPlayground onEvaluate={onEvaluate} isLoading={isLoading} />
      </div>

      {/* While loading we dim the old result instead of removing it, so the layout does not jump. */}
      <div
        aria-busy={isLoading}
        className={`lg:col-span-7 space-y-4 transition-opacity ${isLoading ? 'opacity-50' : 'opacity-100'}`}
      >
        <SummaryStrip evaluation={evaluation} />

        <CircuitBreakerAlert
          isBlocked={evaluation.isBlocked}
          isSelfCorrected={evaluation.isSelfCorrected}
          originalQuery={evaluation.query}
        />

        {/* key resets the selected sentence whenever a new evaluation arrives */}
        <SentenceHeatmap
          key={evaluation.query}
          sentences={evaluation.sentences}
          query={evaluation.query}
        />

        <RagTriadDiagnostics metrics={evaluation.metrics} rootCause={evaluation.rootCause} />
      </div>
    </div>
  );
}
