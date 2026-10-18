import type {Evidence, Report, Run} from './api';
import {readable} from './format-label';

export function InvestigationTimeline({run, busy}: {run?: Run; busy: boolean}) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div><span className="eyebrow">EXECUTION RECORD</span><h2>Investigation timeline</h2></div>
        {busy && <span className="live-label">Running</span>}
      </div>
      {!run?.events.length ? (
        <p className="empty">Start an investigation to see specialist tools and evidence appear here.</p>
      ) : (
        <ol className="timeline">
          {run.events.map(event => (
            <li key={event.index}>
              <span className={`timeline-dot ${event.status === 'gap' ? 'warning' : ''}`} />
              <div><strong>{readable(event.role)} specialist</strong><span>{readable(event.status)}</span></div>
              <time>{new Date(event.at).toLocaleTimeString('en-GB')}</time>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

type ReportPanelProps = {
  report: Report;
  runId?: string;
  onSelectEvidence: (evidence?: Evidence) => void;
};

export function ReportPanel({report, runId, onSelectEvidence}: ReportPanelProps) {
  return (
    <section className="panel report-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">REPORT V{report.version} / HUMAN REVIEW REQUIRED</span>
          <h2>Investigator assessment</h2>
        </div>
        <div className="export-controls"><a className="text-link" href={`/api/runs/${runId}/report`} download="casemind-report.json">JSON</a><a className="text-link" href={`/api/runs/${runId}/exports/report.html`} download>Printable HTML</a><a className="text-link" href={`/api/runs/${runId}/exports/report.html?lang=vi`} download>HTML Tiếng Việt / English</a><a className="text-link" href={`/api/runs/${runId}/exports/report.pdf`} download>PDF</a></div>
      </div>
      <p className="assessment-label">AI interpretation · verify against the evidence below</p>
      <p className="report-summary">{report.synthesis.summary}</p>
      {report.priority && <details><summary>Follow-up priority: {readable(report.priority.level)} · {report.priority.score}/100</summary><p className="muted">{report.priority.interpretation}</p><ul className="prose-list">{report.priority.contributors.map(c => <li key={c.tool}>{readable(c.tool)}: {c.weight} points from {c.evidence_ids.length} indicator(s)</li>)}</ul></details>}
      <h3>Hypotheses for follow-up</h3>
      {report.synthesis.hypotheses.map((claim, index) => (
        <div className="hypothesis" key={index}>
          <span className="hypothesis-number">H{index + 1}</span>
          <div>
            <p>{claim.text}</p>
            <div className="citation-row">
              {claim.evidence_ids.map(id => (
                <button key={id} className="citation" onClick={() => onSelectEvidence(report.evidence.find(item => item.id === id))}>
                  {report.evidence.findIndex(item => item.id === id) + 1}. Evidence
                </button>
              ))}
            </div>
          </div>
        </div>
      ))}
      <h3>Legitimate alternatives</h3>
      <ul className="prose-list">{report.synthesis.alternatives.map((text, index) => <li key={index}>{text}</li>)}</ul>
      <h3>Unresolved questions</h3>
      <ul className="prose-list">{report.synthesis.unresolved.map((text, index) => <li key={index}>{text}</li>)}</ul>
      {!!report.gaps.length && (
        <p className="gap-label">This report has {report.gaps.length} specialist gap(s). Review coverage before approving.</p>
      )}
      <div className="report-meta">
        {report.model} · {report.usage.tool_calls} tool calls · {report.usage.input_tokens + report.usage.output_tokens} tokens · {report.usage.elapsed_seconds}s
      </div>
    </section>
  );
}
