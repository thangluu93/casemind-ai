import type {CaseData, Evidence, RecordData, Report, Review} from './api';
import {readable} from './format-label';

type EvidenceColumnProps = {
  data?: CaseData;
  report?: Report;
  review?: Review;
  evidence?: Evidence;
  source?: RecordData;
  action: string;
  reason: string;
  reviewBusy: boolean;
  onActionChange: (value: string) => void;
  onReasonChange: (value: string) => void;
  onSelectEvidence: (evidence: Evidence) => void;
  onInspectSource: (id: string) => void;
  onCloseDetail: () => void;
  onSaveReview: () => void;
};

export function EvidenceColumn(props: EvidenceColumnProps) {
  const {data, report, review, evidence, source} = props;

  return (
    <aside className="evidence-column">
      <EvidenceLedger report={report} selectedId={evidence?.id} onSelect={props.onSelectEvidence} />
      {(evidence || source) && (
        <SourceDetail
          data={data}
          runId={(report as Report & {run_id?: string})?.run_id}
          evidence={evidence}
          source={source}
          onInspect={props.onInspectSource}
          onClose={props.onCloseDetail}
        />
      )}
      {report && (
        <ReviewPanel
          report={report}
          review={review}
          action={props.action}
          reason={props.reason}
          busy={props.reviewBusy}
          onActionChange={props.onActionChange}
          onReasonChange={props.onReasonChange}
          onSave={props.onSaveReview}
        />
      )}
    </aside>
  );
}

function EvidenceLedger({report, selectedId, onSelect}: {report?: Report; selectedId?: string; onSelect: (evidence: Evidence) => void}) {
  return (
    <section className="panel evidence-panel">
      <div className="panel-heading">
        <div><span className="eyebrow">SOURCE-SUPPORTED OBSERVATIONS</span><h2>Evidence ledger</h2></div>
        <span className="count">{report?.evidence.length || 0}</span>
      </div>
      {!report ? (
        <p className="empty">Verified tool findings will appear after the investigation. Select a graph record to inspect the supplied data.</p>
      ) : (
        <div className="evidence-list">
          {report.evidence.map((item, index) => (
            <button
              key={item.id}
              className={`evidence-item ${selectedId === item.id ? 'active' : ''}`}
              onClick={() => onSelect(item)}
            >
              <span className="evidence-number">{String(index + 1).padStart(2, '0')}</span>
              <span><strong>{readable(item.tool)}</strong><small>{item.claim_kind} · {item.refs.length} source records</small></span>
              <span aria-hidden="true">↗</span>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

type SourceDetailProps = {
  data?: CaseData;
  runId?: string;
  evidence?: Evidence;
  source?: RecordData;
  onInspect: (id: string) => void;
  onClose: () => void;
};

function SourceDetail({data, runId, evidence, source, onInspect, onClose}: SourceDetailProps) {
  return (
    <section className="panel source-panel">
      <div className="panel-heading">
        <h2>{source ? 'Source record' : 'Evidence detail'}</h2>
        <button className="close-button" onClick={onClose} aria-label="Close detail">×</button>
      </div>
      {source ? (
        <>
          <p className="record-id">{source.id}</p>
          <pre>{JSON.stringify(source, null, 2)}</pre>
          {data?.documents.some(document => document.id === source.id) && (
            <a className="text-link" target="_blank" rel="noreferrer" href={runId ? `/api/runs/${runId}/documents/${source.id}.pdf` : `/api/cases/${data.id}/documents/${source.id}.pdf`}>
              Open source PDF ↗
            </a>
          )}
        </>
      ) : evidence && (
        <>
          <span className="assessment-label">Deterministic tool output</span>
          <p className="muted">{readable(evidence.verification_status)} · {evidence.source_kind} · {evidence.tool} v{evidence.tool_version}</p>
          <pre>{JSON.stringify(evidence.payload, null, 2)}</pre>
          {!!Object.keys(evidence.parameters).length && <details><summary>Derivation parameters</summary><pre>{JSON.stringify(evidence.parameters, null, 2)}</pre></details>}
          {evidence.limitations.map((text, index) => <p key={index} className="muted">{text}</p>)}
          <h3>Original sources</h3>
          <div className="source-list">
            {evidence.refs.map(id => <button key={id} onClick={() => onInspect(id)}>{id.split(':').at(-1)} · Inspect source ↗</button>)}
          </div>
        </>
      )}
    </section>
  );
}

type ReviewPanelProps = {
  report: Report;
  review?: Review;
  action: string;
  reason: string;
  busy: boolean;
  onActionChange: (value: string) => void;
  onReasonChange: (value: string) => void;
  onSave: () => void;
};

function ReviewPanel({report, review, action, reason, busy, onActionChange, onReasonChange, onSave}: ReviewPanelProps) {
  return (
    <section className="panel review-panel">
      <span className="eyebrow">INVESTIGATOR DECISION</span>
      <h2>Review this version</h2>
      {review?.action !== 'pending' ? (
        <div className="review-result">
          <strong>{readable(review?.action || '')}</strong>
          <p>{review?.reason}</p>
          <small>Bound to report v{report.version} · {report.hash.slice(0, 12)}</small>
        </div>
      ) : (
        <form onSubmit={event => {event.preventDefault(); onSave();}}>
          <label htmlFor="action">Decision</label>
          <select id="action" value={action} onChange={event => onActionChange(event.target.value)}>
            <option value="needs_follow_up">Request follow-up</option>
            <option value="approved">Approve assessment</option>
            <option value="rejected">Reject assessment</option>
          </select>
          <label htmlFor="reason">Reason</label>
          <textarea
            id="reason"
            minLength={5}
            maxLength={2000}
            required
            value={reason}
            onChange={event => onReasonChange(event.target.value)}
            placeholder="Explain your decision and next steps."
          />
          <p className="muted">This review is saved permanently against this report version.</p>
          <button disabled={busy || reason.trim().length < 5}>{busy ? 'Saving…' : 'Save review'}</button>
        </form>
      )}
    </section>
  );
}
