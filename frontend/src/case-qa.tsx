import {useEffect, useState} from 'react';
import {api, type Report} from './api';
import {text} from './workspace-api';
export type QuestionSourceRef = {
  kind: 'record' | 'inventory';
  snapshot_hash: string;
  record_id: string | null;
  group: string;
  record_count?: number;
  collection_hash?: string;
  scope?: {account_ids?: string[]; entity_ids?: string[]; direction?: string; currency?: string};
};
type Answer = {
  id?: string; status?: string; answer?: string; facts?: unknown[];
  evidence_ids?: string[]; source_refs?: QuestionSourceRef[]; limitations?: string[];
  [key: string]: unknown;
};
type Props = {
  runId?: string; report?: Report; inspectEvidence: (id: string) => void;
  inspectSource: (id: string) => void; inspectInventory: (ref: QuestionSourceRef) => void;
};
export function CaseQA({runId, report, inspectEvidence, inspectSource, inspectInventory}: Props) {
  const [question, setQuestion] = useState('');
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    let live = true;
    setAnswers([]); setError('');
    if (runId) api<{items: Answer[]}>(`/runs/${runId}/questions`)
      .then(value => {if (live) setAnswers(value.items);})
      .catch(caught => {if (live) setError(caught.message);});
    return () => {live = false;};
  }, [runId]);
  async function ask() {
    if (!runId || !report) return;
    setBusy(true); setError('');
    try {
      const answer = await api<Answer>(`/runs/${runId}/questions`, {
        question, expected_report_hash: report.hash, idempotency_key: crypto.randomUUID(),
      });
      setAnswers(old => [...old, answer]); setQuestion('');
    } catch (caught) {setError((caught as Error).message);}
    finally {setBusy(false);}
  }
  return <section className="panel">
    <span className="eyebrow">BOUNDED PINNED-RUN RETRIEVAL</span><h2>Case Q&A</h2>
    <p className="muted">Ask about supplied evidence, alternatives or gaps. Exact amounts and transaction reasons come from deterministic tools. Unsupported or cross-case questions are declined; answers never approve a disposition.</p>
    {error && <p role="alert">{error}</p>}
    {!report ? <p className="empty">Select a completed run to ask evidence-grounded questions.</p> :
      <form onSubmit={event => {event.preventDefault(); void ask();}}>
        <label>Question<textarea required maxLength={2000} value={question} onChange={event => setQuestion(event.target.value)}/></label>
        <button disabled={busy || !question.trim()}>{busy ? 'Checking evidence…' : 'Ask this run'}</button>
      </form>}
    {answers.map((answer, index) => <article className="finding-card" key={answer.id || index}>
      <p className="coverage">{answer.status || 'Answer'}</p><p>{answer.answer || text(answer)}</p>
      {answer.facts?.map((fact, factIndex) => <pre key={factIndex}>{text(fact)}</pre>)}
      <div className="citation-row">
        {answer.evidence_ids?.map(id => <button key={id} onClick={() => inspectEvidence(id)}>{id}</button>)}
        {answer.source_refs?.map((ref, refIndex) => ref.kind === 'record' && ref.record_id ?
          <button key={`source-${refIndex}`} onClick={() => inspectSource(ref.record_id!)}>Source {ref.record_id}</button> :
          <button key={`inventory-${refIndex}`} onClick={() => inspectInventory(ref)}>Pinned {ref.group} inventory ({ref.record_count ?? 'unknown'})</button>)}
      </div>
      <ul>{answer.limitations?.map((limitation, limitationIndex) => <li key={limitationIndex}>{limitation}</li>)}</ul>
    </article>)}
  </section>;
}
