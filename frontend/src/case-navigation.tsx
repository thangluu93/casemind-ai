import type {CaseData, CaseSummary, Review, Run} from './api';
import {readable} from './format-label';

type SidebarProps = {
  cases: CaseSummary[];
  currentCaseId?: string;
  busy: boolean;
  onSelect: (id: string) => void;
};

export function Sidebar({cases, currentCaseId, busy, onSelect}: SidebarProps) {
  return (
    <aside className="sidebar">
      <a className="brand" href="/" aria-label="CaseMind home">
        <span className="brand-mark">C</span>
        <span>
          CaseMind<span className="brand-sub">INVESTIGATOR WORKSPACE</span>
        </span>
      </a>
      <div className="case-nav">
        <span className="eyebrow">CASE QUEUE / {cases.length.toString().padStart(2, '0')}</span>
        <nav aria-label="Synthetic investigations">
          {cases.map((caseSummary, index) => (
            <button
              key={caseSummary.id}
              className={`case-button ${currentCaseId === caseSummary.id ? 'active' : ''}`}
              disabled={busy}
              onClick={() => onSelect(caseSummary.id)}
            >
              <span className="case-number">0{index + 1}</span>
              <span>
                <strong>{caseSummary.title}</strong>
                <small>
                  {caseSummary.transaction_count} transfers · {caseSummary.document_count} documents
                </small>
              </span>
            </button>
          ))}
        </nav>
      </div>
      <div className="sidebar-note">
        <span className="eyebrow">DEMO BOUNDARY</span>
        <p>Every person, company and record is fictional. Findings support investigator review.</p>
        <span className="status-dot" /> Human decision required
      </div>
    </aside>
  );
}

type CaseHeaderProps = {
  cases: CaseSummary[];
  data?: CaseData;
  run?: Run;
  review?: Review;
  reportReady: boolean;
  busy: boolean;
  onStart: () => void;
};

export function CaseHeader({cases, data, run, review, reportReady, busy, onStart}: CaseHeaderProps) {
  const disposition = review?.action && review.action !== 'pending'
    ? readable(review.action)
    : run
      ? readable(run.status)
      : 'Ready to investigate';

  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">CASE FILE / {cases.findIndex(item => item.id === data?.id) + 1 || '—'}</span>
          <h1>{data?.title || 'Loading case file…'}</h1>
          <p className="muted">Trace the records. Test the hypothesis. Keep the decision human.</p>
        </div>
        <button className="primary" disabled={!data || busy} onClick={onStart}>
          {busy ? 'Investigating…' : reportReady ? 'Run again' : 'Start investigation'}
          <span aria-hidden="true"> ↗</span>
        </button>
      </div>
      <div className="case-strip">
        <div><span className="eyebrow">TRANSFERS</span><strong>{data?.transactions.length ?? '—'}</strong></div>
        <div><span className="eyebrow">ENTITIES</span><strong>{data?.entities.length ?? '—'}</strong></div>
        <div><span className="eyebrow">DOCUMENTS</span><strong>{data?.documents.length ?? '—'}</strong></div>
        <div className="strip-status">
          <span className="eyebrow">DISPOSITION</span>
          <strong>{disposition}</strong>
        </div>
      </div>
    </>
  );
}
