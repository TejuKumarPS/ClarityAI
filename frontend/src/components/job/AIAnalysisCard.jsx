export function AIAnalysisCard({ analysis }) {
  if (!analysis) return null

  const getSentimentBadge = (sentiment) => {
    const s = (sentiment || '').toLowerCase()
    switch (s) {
      case 'positive':
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-800/60">
            Positive
          </span>
        )
      case 'negative':
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-950/80 text-rose-300 border border-rose-800/60">
            Negative
          </span>
        )
      case 'mixed':
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-purple-950/80 text-purple-300 border border-purple-800/60">
            Mixed
          </span>
        )
      default:
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700">
            {sentiment || 'Neutral'}
          </span>
        )
    }
  }

  const getRiskSeverityBadge = (severity) => {
    const s = (severity || '').toLowerCase()
    switch (s) {
      case 'high':
      case 'critical':
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-950/80 text-rose-300 border border-rose-800/60">
            High Severity
          </span>
        )
      case 'medium':
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-950/80 text-amber-300 border border-amber-800/60">
            Medium Severity
          </span>
        )
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-950/80 text-blue-300 border border-blue-800/60">
            Low Severity
          </span>
        )
    }
  }

  return (
    <div className="space-y-6">
      {/* Executive Summary & Sentiment */}
      <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-6 md:p-8 shadow-xl">
        <div className="flex items-start sm:items-center justify-between gap-4 pb-4 border-b border-slate-800/80">
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">Executive Meeting Summary</h2>
            <p className="text-xs text-slate-400 mt-0.5">Grounded AI analysis from transcript context</p>
          </div>
          {analysis.sentiment && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">Sentiment:</span>
              {getSentimentBadge(analysis.sentiment)}
            </div>
          )}
        </div>

        <div className="mt-4 text-sm leading-relaxed text-slate-200 bg-slate-950/40 p-4 rounded-xl border border-slate-800/60">
          {analysis.summary}
        </div>
      </div>

      {/* Key Points */}
      {analysis.key_points && analysis.key_points.length > 0 && (
        <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-6 shadow-xl space-y-4">
          <h3 className="text-base font-semibold text-white flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-blue-400"></span>
            Key Points & Takeaways
          </h3>
          <ul className="space-y-2 text-sm text-slate-300">
            {analysis.key_points.map((point, idx) => (
              <li key={idx} className="flex items-start gap-3 bg-slate-950/40 p-3 rounded-xl border border-slate-800/60">
                <span className="text-blue-400 font-mono text-xs mt-0.5">•</span>
                <span className="leading-relaxed">{point}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Decisions & Action Items Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Decisions */}
        <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-6 shadow-xl space-y-4">
          <h3 className="text-base font-semibold text-white flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            Decisions ({analysis.decisions?.length || 0})
          </h3>
          {(!analysis.decisions || analysis.decisions.length === 0) ? (
            <p className="text-xs text-slate-500 italic p-3 bg-slate-950/40 rounded-xl border border-slate-800/40">
              No explicit decisions recorded in transcript.
            </p>
          ) : (
            <div className="space-y-3">
              {analysis.decisions.map((dec, idx) => (
                <div key={idx} className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1.5">
                  <p className="text-sm font-medium text-slate-100">{dec.decision}</p>
                  {dec.rationale && (
                    <p className="text-xs text-slate-400">
                      <span className="text-slate-500 font-medium">Rationale:</span> {dec.rationale}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Action Items */}
        <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-6 shadow-xl space-y-4">
          <h3 className="text-base font-semibold text-white flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-indigo-400"></span>
            Action Items ({analysis.action_items?.length || 0})
          </h3>
          {(!analysis.action_items || analysis.action_items.length === 0) ? (
            <p className="text-xs text-slate-500 italic p-3 bg-slate-950/40 rounded-xl border border-slate-800/40">
              No action items identified.
            </p>
          ) : (
            <div className="space-y-3">
              {analysis.action_items.map((item, idx) => (
                <div key={idx} className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 flex items-start justify-between gap-3">
                  <div className="space-y-1">
                    <p className="text-sm font-medium text-slate-100">{item.task}</p>
                  </div>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 shrink-0 border border-slate-700">
                    {item.owner ? `@${item.owner}` : 'Unassigned'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Risks & Open Questions Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Risks */}
        <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-6 shadow-xl space-y-4">
          <h3 className="text-base font-semibold text-white flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-rose-400"></span>
            Identified Risks ({analysis.risks?.length || 0})
          </h3>
          {(!analysis.risks || analysis.risks.length === 0) ? (
            <p className="text-xs text-slate-500 italic p-3 bg-slate-950/40 rounded-xl border border-slate-800/40">
              No significant risks identified.
            </p>
          ) : (
            <div className="space-y-3">
              {analysis.risks.map((risk, idx) => (
                <div key={idx} className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 flex items-start justify-between gap-3">
                  <p className="text-sm text-slate-200 leading-relaxed">{risk.description}</p>
                  <div className="shrink-0">{getRiskSeverityBadge(risk.severity)}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Open Questions */}
        <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-6 shadow-xl space-y-4">
          <h3 className="text-base font-semibold text-white flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-purple-400"></span>
            Open Questions ({analysis.open_questions?.length || 0})
          </h3>
          {(!analysis.open_questions || analysis.open_questions.length === 0) ? (
            <p className="text-xs text-slate-500 italic p-3 bg-slate-950/40 rounded-xl border border-slate-800/40">
              No unresolved open questions.
            </p>
          ) : (
            <div className="space-y-3">
              {analysis.open_questions.map((q, idx) => (
                <div key={idx} className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 flex items-start justify-between gap-3">
                  <p className="text-sm text-slate-200 leading-relaxed">{q.question}</p>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 shrink-0 border border-slate-700">
                    {q.owner ? `@${q.owner}` : 'Unassigned'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
