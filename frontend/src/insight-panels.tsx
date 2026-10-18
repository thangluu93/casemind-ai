import {useEffect, useState, type ReactNode} from 'react';
import {api, type CaseData, type Report} from './api';
import {FlowGraph} from './flow-graph';
import {readable} from './format-label';
import {text} from './workspace-api';

type Inspect = (id: string) => void;
type Limited = {limitations?: string[]};

function usePinned<T>(path?: string) {
  const [value, setValue] = useState<T>();
  const [error, setError] = useState('');
  useEffect(() => {
    let live = true;
    setValue(undefined); setError('');
    if (path) api<T>(path).then(next => {if (live) setValue(next);}).catch(caught => {if (live) setError(caught.message);});
    return () => {live = false;};
  }, [path]);
  return {value, error};
}

function Limitations({items}: {items?: string[]}) {
  return items?.length ? <ul className="prose-list muted">{items.map((item, index) => <li key={index}>{item}</li>)}</ul> : null;
}

function NeedsRun({runId, children}: {runId?: string; children: ReactNode}) {
  return runId ? <>{children}</> : <p className="empty">Select a completed run; this view derives from its pinned evidence.</p>;
}

function SourceButtons({ids, inspect, label = 'Inspect'}: {ids: string[]; inspect: Inspect; label?: string}) {
  return <div className="citation-row">{[...new Set(ids)].map(id => <button key={id} onClick={() => inspect(id)}>{label} {id}</button>)}</div>;
}

type Typology = {id: string; name: string; family: string; state: string; observed_indicator_count: number;
  indicators: {tool: string; description: string; state: string; evidence_ids: string[]}[]};

export function TypologyMap({runId, inspectEvidence}: {runId?: string; inspectEvidence: Inspect}) {
  const {value, error} = usePinned<{typologies: Typology[]; evaluated_families: string[]} & Limited>(runId && `/runs/${runId}/typologies`);
  return <section className="panel">
    <span className="eyebrow">DETERMINISTIC MAPPING / PINNED EVIDENCE</span><h2>Typology indicators</h2>
    <p className="muted">Each recorded indicator is mapped to a public money-laundering typology category. Not evaluated means the responsible specialist did not run or failed.</p>
    <NeedsRun runId={runId}>
      {error && <p role="alert">{error}</p>}
      {!value && !error && <p role="status">Mapping evidence…</p>}
      {value && <>
        <p className="coverage">Evaluated specialists: {value.evaluated_families.map(readable).join(', ') || 'none'}</p>
        {value.typologies.map(typology => <article className="finding-card" key={typology.id}>
          <div className="panel-heading"><h3>{typology.name}</h3><span className={`state-chip ${typology.state}`}>{readable(typology.state)}</span></div>
          <ul className="indicator-list">{typology.indicators.map((indicator, index) => <li key={index}>
            <span className={`state-chip ${indicator.state}`}>{readable(indicator.state)}</span> {indicator.description}
            <small> · {readable(indicator.tool)}</small>
            {!!indicator.evidence_ids.length && <SourceButtons ids={indicator.evidence_ids} inspect={inspectEvidence} label="Evidence"/>}
          </li>)}</ul>
        </article>)}
        <Limitations items={value.limitations}/>
      </>}
    </NeedsRun>
  </section>;
}

const RULE_FIELDS: {key: string; label: string; step: string}[] = [
  {key: 'flow_minimum_amount', label: 'Flow minimum amount', step: '1'},
  {key: 'flow_window_hours', label: 'Flow window (hours)', step: '1'},
  {key: 'flow_minimum_retained_ratio', label: 'Minimum retained ratio', step: '0.01'},
  {key: 'flow_maximum_retained_ratio', label: 'Maximum retained ratio', step: '0.01'},
  {key: 'structuring_threshold', label: 'Structuring threshold', step: '1'},
  {key: 'structuring_window_hours', label: 'Structuring window (hours)', step: '1'},
  {key: 'structuring_minimum_count', label: 'Structuring minimum count', step: '1'},
  {key: 'activity_median_multiple', label: 'Activity median multiple', step: '1'},
];
const INTEGER_RULES = new Set(['flow_window_hours', 'structuring_window_hours', 'structuring_minimum_count', 'activity_median_multiple']);
type Simulation = {changed: boolean; parameters: Record<string, string>; defaults: Record<string, string>;
  tools: {tool: string; recorded_flagged: string[]; simulated_flagged: string[]; added: string[]; removed: string[]}[]} & Limited;

export function WhatIfSimulator({runId, inspect}: {runId?: string; inspect: Inspect}) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [result, setResult] = useState<Simulation>();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {setValues({}); setResult(undefined);}, [runId]);
  async function simulate(next = values) {
    if (!runId) return;
    setBusy(true); setError('');
    const body = Object.fromEntries(Object.entries(next).filter(([, v]) => v !== '').map(([k, v]) => [k, INTEGER_RULES.has(k) ? Number(v) : v]));
    try {
      const value = await api<Simulation>(`/runs/${runId}/what-if`, body);
      setResult(value);
      if (!Object.keys(next).length) setValues(value.defaults);
    } catch (caught) {setError((caught as Error).message);}
    finally {setBusy(false);}
  }
  useEffect(() => {if (runId) void simulate({});}, [runId]);
  return <section className="panel">
    <span className="eyebrow">SIMULATION ONLY / REPORT UNCHANGED</span><h2>Threshold what-if</h2>
    <p className="muted">Change a demonstration rule and see which transactions would enter or leave each indicator. The pinned report and its review never change.</p>
    <NeedsRun runId={runId}>
      <form className="filter-row" onSubmit={event => {event.preventDefault(); void simulate();}}>
        {RULE_FIELDS.map(field => <label key={field.key}>{field.label}
          <input type="number" min="0" step={field.step} value={values[field.key] ?? ''} onChange={event => setValues(old => ({...old, [field.key]: event.target.value}))}/>
        </label>)}
        <button className="primary" disabled={busy}>{busy ? 'Simulating…' : 'Run simulation'}</button>
        <button type="button" disabled={busy || !result} onClick={() => result && setValues(result.defaults)}>Reset to recorded rules</button>
      </form>
      {error && <p role="alert">{error}</p>}
      {result && <>
        <p className="coverage">{result.changed ? 'Classification changes under these parameters.' : 'No transaction changes classification.'}</p>
        {result.tools.map(tool => <article className="finding-card" key={tool.tool}>
          <h3>{readable(tool.tool)}</h3>
          <div className="fact-line"><strong>Recorded</strong><span>{tool.recorded_flagged.length} transaction(s)</span></div>
          <div className="fact-line"><strong>Simulated</strong><span>{tool.simulated_flagged.length} transaction(s)</span></div>
          {!!tool.added.length && <><p>Would be added</p><SourceButtons ids={tool.added} inspect={inspect}/></>}
          {!!tool.removed.length && <><p>Would be removed</p><SourceButtons ids={tool.removed} inspect={inspect}/></>}
        </article>)}
        <Limitations items={result.limitations}/>
      </>}
    </NeedsRun>
  </section>;
}

type Driver = {id: string; question: string; request_type: string; affects_evidence_ids: string[]; source_refs: string[]; effect: string; impact_score: number; rationale: string};
type Check = {evidence_id: string; alternative: string; status: string; facts: Record<string, unknown>; source_refs: string[]; note: string};
type Advisory = {id: string; kind: string; state: string; error?: string; status?: string; question?: string; abstained?: boolean;
  points?: {evidence_ids: string[]; legitimate_explanation: string; what_would_falsify: string}[]; overall_caution?: string;
  drafts?: {recipient_role: string; subject: string; body: string; requested_items: string[]; evidence_ids: string[]; driver_ids: string[]}[];
  rationale?: string; query?: Record<string, unknown> | null};

function useAdvisories(runId: string | undefined, kind: string) {
  const [items, setItems] = useState<Advisory[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    let live = true;
    setItems([]); setError('');
    if (runId) api<{items: Advisory[]}>(`/runs/${runId}/advisories`).then(value => {if (live) setItems(value.items.filter(item => item.kind === kind));}).catch(caught => {if (live) setError(caught.message);});
    return () => {live = false;};
  }, [runId, kind]);
  async function request(report: Report, question = '') {
    if (!runId) return undefined;
    setBusy(true); setError('');
    try {
      const value = await api<Advisory>(`/runs/${runId}/advisories/${kind}`, {expected_report_hash: report.hash, idempotency_key: crypto.randomUUID(), question});
      setItems(old => [...old, value]);
      return value;
    } catch (caught) {setError((caught as Error).message); return undefined;}
    finally {setBusy(false);}
  }
  return {items, busy, error, request};
}

export function ChallengeWorkspace({runId, report, inspect, inspectEvidence}: {runId?: string; report?: Report; inspect: Inspect; inspectEvidence: Inspect}) {
  const drivers = usePinned<{drivers: Driver[]; ranking_policy: string} & Limited>(runId && `/runs/${runId}/change-drivers`);
  const checks = usePinned<{checks: Check[]} & Limited>(runId && `/runs/${runId}/alternative-checks`);
  const advisory = useAdvisories(runId, 'challenge');
  return <section className="panel">
    <span className="eyebrow">DEVIL'S ADVOCATE / HYPOTHESES UNDER TEST</span><h2>Challenge the hypotheses</h2>
    <p className="muted">Deterministic checks test the most common legitimate explanation for each indicator. The ranked list shows which missing information would most change the picture. A bounded Gemini call can then argue the opposing view with cited evidence.</p>
    <NeedsRun runId={runId}>
      <h3>Legitimate-explanation checks</h3>
      {checks.error && <p role="alert">{checks.error}</p>}
      {checks.value?.checks.length === 0 && <p className="empty">No indicators to challenge in this run.</p>}
      {checks.value?.checks.map((check, index) => <article className="finding-card" key={index}>
        <div className="panel-heading"><strong>{check.alternative}</strong><span className={`state-chip ${check.status}`}>{readable(check.status)}</span></div>
        {Object.entries(check.facts).map(([key, value]) => <div className="fact-line" key={key}><strong>{readable(key)}</strong><span>{text(value)}</span></div>)}
        <p className="muted">{check.note}</p>
        <div className="citation-row"><button onClick={() => inspectEvidence(check.evidence_id)}>Evidence {check.evidence_id}</button></div>
        <SourceButtons ids={check.source_refs.slice(0, 12)} inspect={inspect}/>
      </article>)}
      <Limitations items={checks.value?.limitations}/>
      <h3>What would change the conclusion</h3>
      {drivers.error && <p role="alert">{drivers.error}</p>}
      {drivers.value && <p className="coverage">{drivers.value.ranking_policy}</p>}
      <ol className="driver-list">{drivers.value?.drivers.map(driver => <li key={driver.id} className="finding-card">
        <div className="panel-heading"><strong>{driver.question}</strong><span className="count">{driver.impact_score}</span></div>
        <p className="muted">{readable(driver.request_type)} · {readable(driver.effect)} · {driver.rationale}</p>
        <SourceButtons ids={driver.affects_evidence_ids} inspect={inspectEvidence} label="Evidence"/>
      </li>)}</ol>
      <Limitations items={drivers.value?.limitations}/>
      <h3>Model counter-argument</h3>
      {advisory.error && <p role="alert">{advisory.error}</p>}
      <button className="primary" disabled={!report || advisory.busy} onClick={() => report && void advisory.request(report)}>{advisory.busy ? 'Arguing the other side…' : 'Ask Gemini for the strongest legitimate explanation'}</button>
      {advisory.items.map(item => <article className="finding-card" key={item.id}>
        <p className="coverage">{readable(item.status || item.state)} · hypothesis, not evidence</p>
        {item.error && <p role="alert">{item.error}</p>}
        {item.overall_caution && <p>{item.overall_caution}</p>}
        {item.points?.map((point, index) => <div className="hypothesis" key={index}><span className="hypothesis-number">C{index + 1}</span><div>
          <p><strong>Legitimate explanation:</strong> {point.legitimate_explanation}</p>
          <p><strong>Would falsify the hypothesis:</strong> {point.what_would_falsify}</p>
          <SourceButtons ids={point.evidence_ids} inspect={inspectEvidence} label="Evidence"/>
        </div></div>)}
      </article>)}
    </NeedsRun>
  </section>;
}

export function RfiDrafts({runId, report, inspectEvidence}: {runId?: string; report?: Report; inspectEvidence: Inspect}) {
  const advisory = useAdvisories(runId, 'rfi');
  const [edited, setEdited] = useState<Record<string, string>>({});
  return <section className="panel">
    <span className="eyebrow">DRAFTS ONLY / NEVER SENT BY CASEMIND</span><h2>Requests for information</h2>
    <p className="muted">Gemini drafts neutral requests from the ranked change drivers. Edit and copy a draft into your own channel. CaseMind does not send messages or tip off the customer.</p>
    <NeedsRun runId={runId}>
      {advisory.error && <p role="alert">{advisory.error}</p>}
      <button className="primary" disabled={!report || advisory.busy} onClick={() => report && void advisory.request(report)}>{advisory.busy ? 'Drafting…' : 'Draft requests from change drivers'}</button>
      {advisory.items.map(item => <div key={item.id}>
        <p className="coverage">{readable(item.status || item.state)}</p>
        {item.error && <p role="alert">{item.error}</p>}
        {item.drafts?.map((draft, index) => {
          const key = `${item.id}:${index}`;
          const body = edited[key] ?? `${draft.subject}\n\n${draft.body}\n\nRequested:\n${draft.requested_items.map(entry => `- ${entry}`).join('\n')}`;
          return <article className="finding-card" key={key}>
            <div className="panel-heading"><strong>To: {readable(draft.recipient_role)}</strong><span className="synthetic-label">Draft · not sent</span></div>
            <label>Editable draft<textarea rows={8} value={body} onChange={event => setEdited(old => ({...old, [key]: event.target.value}))}/></label>
            <div className="citation-row"><button onClick={() => void navigator.clipboard?.writeText(body)}>Copy draft</button></div>
            <SourceButtons ids={draft.evidence_ids} inspect={inspectEvidence} label="Evidence"/>
          </article>;
        })}
      </div>)}
    </NeedsRun>
  </section>;
}

type PathResult = {paths: {ordered_transaction_ids: string[]; accounts: string[]; amounts: string[]; currencies: string[]; elapsed_hours: number; hops: number}[]; path_count: number; truncated: boolean} & Limited;

export function GraphQueryPanel({runId, report, data, inspect}: {runId?: string; report?: Report; data: CaseData; inspect: Inspect}) {
  const [query, setQuery] = useState({start_id: '', end_id: '', max_hops: '3', currency: '', min_amount: '', window_hours: ''});
  const [question, setQuestion] = useState('');
  const [result, setResult] = useState<PathResult>();
  const [error, setError] = useState('');
  const advisory = useAdvisories(runId, 'graph_query_plan');
  const endpoints = [...data.accounts.map(a => ({id: a.id, label: `Account ${a.id}`})), ...data.entities.map(e => ({id: e.id, label: e.name}))];
  async function run() {
    if (!runId) return;
    setError('');
    try {
      setResult(await api<PathResult>(`/runs/${runId}/graph-query`, {
        start_id: query.start_id, end_id: query.end_id || null, max_hops: Number(query.max_hops),
        currency: query.currency || null, min_amount: query.min_amount || null,
        window_hours: query.window_hours ? Number(query.window_hours) : null}));
    } catch (caught) {setError((caught as Error).message);}
  }
  async function plan() {
    if (!report) return;
    const value = await advisory.request(report, question);
    const planned = value?.query as Record<string, unknown> | null | undefined;
    if (planned) setQuery({start_id: String(planned.start_id), end_id: String(planned.end_id ?? ''), max_hops: String(planned.max_hops),
      currency: String(planned.currency ?? ''), min_amount: String(planned.min_amount ?? ''), window_hours: String(planned.window_hours ?? '')});
  }
  return <section className="panel">
    <span className="eyebrow">MODEL PLANS · TOOLS COMPUTE</span><h2>Graph query</h2>
    <p className="muted">Describe a path question in words; Gemini proposes a bounded query that you review below before deterministic execution. You can also edit the query directly.</p>
    <NeedsRun runId={runId}>
      <form onSubmit={event => {event.preventDefault(); void plan();}}>
        <label>Question<input value={question} maxLength={1000} placeholder="Show transfers out of Harbor Trading within three hops" onChange={event => setQuestion(event.target.value)}/></label>
        <button disabled={!report || advisory.busy || question.trim().length < 5}>{advisory.busy ? 'Planning…' : 'Propose a query'}</button>
      </form>
      {advisory.error && <p role="alert">{advisory.error}</p>}
      {advisory.items.slice(-1).map(item => <p className="coverage" key={item.id}>{readable(item.status || item.state)}{item.rationale ? ` · ${item.rationale}` : ''}{item.error ? ` · ${item.error}` : ''}</p>)}
      <form className="filter-row" onSubmit={event => {event.preventDefault(); void run();}}>
        <label>Start<select required value={query.start_id} onChange={event => setQuery(old => ({...old, start_id: event.target.value}))}><option value="">Choose…</option>{endpoints.map(e => <option key={e.id} value={e.id}>{e.label}</option>)}</select></label>
        <label>End (optional)<select value={query.end_id} onChange={event => setQuery(old => ({...old, end_id: event.target.value}))}><option value="">Any</option>{endpoints.map(e => <option key={e.id} value={e.id}>{e.label}</option>)}</select></label>
        <label>Max hops<input type="number" min="1" max="4" value={query.max_hops} onChange={event => setQuery(old => ({...old, max_hops: event.target.value}))}/></label>
        <label>Currency<input value={query.currency} maxLength={8} onChange={event => setQuery(old => ({...old, currency: event.target.value}))}/></label>
        <label>Minimum amount<input value={query.min_amount} inputMode="decimal" onChange={event => setQuery(old => ({...old, min_amount: event.target.value}))}/></label>
        <label>Window (hours)<input type="number" min="1" max="720" value={query.window_hours} onChange={event => setQuery(old => ({...old, window_hours: event.target.value}))}/></label>
        <button className="primary" disabled={!query.start_id}>Run deterministic query</button>
      </form>
      {error && <p role="alert">{error}</p>}
      {result && <>
        <p className="coverage">{result.path_count} path(s){result.truncated ? ' · truncated at the work limit' : ''}</p>
        {result.paths.slice(0, 50).map((path, index) => <article className="finding-card" key={index}>
          <p>{path.accounts.join(' → ')}</p>
          <div className="fact-line"><strong>Amounts</strong><span>{path.amounts.join(' → ')} {path.currencies.join('/')}</span></div>
          <div className="fact-line"><strong>Elapsed</strong><span>{path.elapsed_hours} h · {path.hops} hop(s)</span></div>
          <SourceButtons ids={path.ordered_transaction_ids} inspect={inspect}/>
        </article>)}
        <Limitations items={result.limitations}/>
      </>}
    </NeedsRun>
  </section>;
}

export function TransferReplay({data, inspect}: {data: CaseData; inspect: Inspect}) {
  const ordered = [...data.transactions].sort((a, b) => a.timestamp.localeCompare(b.timestamp) || a.id.localeCompare(b.id));
  const [frame, setFrame] = useState(ordered.length);
  const [playing, setPlaying] = useState(false);
  useEffect(() => {setFrame(ordered.length); setPlaying(false);}, [data.id, ordered.length]);
  useEffect(() => {
    if (!playing) return;
    if (frame >= ordered.length) {setPlaying(false); return;}
    const timer = setTimeout(() => setFrame(value => value + 1), 700);
    return () => clearTimeout(timer);
  }, [playing, frame, ordered.length]);
  const visible = ordered.slice(0, frame);
  const current = visible[visible.length - 1];
  return <section className="panel">
    <span className="eyebrow">CHRONOLOGICAL REPLAY / SOURCE TRANSACTIONS</span><h2>Money-flow replay</h2>
    <p className="muted">Step through transfers in recorded time order. The graph shows only transfers up to the selected moment; the latest is highlighted.</p>
    <div className="filter-row">
      <button className="primary" onClick={() => {if (frame >= ordered.length) setFrame(0); setPlaying(value => !value);}}>{playing ? 'Pause' : 'Play'}</button>
      <label>Moment<input type="range" min={0} max={ordered.length} value={frame} onChange={event => {setPlaying(false); setFrame(Number(event.target.value));}}/></label>
      <span className="coverage">{frame} / {ordered.length} transfers{current ? ` · ${new Date(current.timestamp).toLocaleString('en-GB')}` : ''}</span>
    </div>
    {current && <p>{current.sender} → {current.receiver} · {current.amount} {current.currency} <button className="text-link" onClick={() => inspect(current.id)}>Inspect {current.id}</button></p>}
    <FlowGraph data={{...data, transactions: visible}} select={record => inspect(record.id)} highlighted={current ? [current.id] : []}/>
  </section>;
}

type TriageItem = {case_id: string; title: string; state: string; run_id?: string; score: number | null; level: string | null; review?: string; check?: string | null; contributors: {tool: string; weight: number}[]};

export function TriageQueue({openRun, openCase}: {openRun: (caseId: string, runId: string) => void; openCase: (caseId: string) => void}) {
  const {value, error} = usePinned<{items: TriageItem[]; policy: string; scope: string}>('/triage');
  return <section className="panel">
    <span className="eyebrow">ALERT QUEUE / RECORDED TRIAGE POLICY</span><h2>Triage queue</h2>
    {error && <p role="alert">{error}</p>}
    {value && <p className="muted">{value.policy} {value.scope}</p>}
    <table className="triage-table"><thead><tr><th>Case</th><th>Score</th><th>Level</th><th>Drivers</th><th>Review</th><th>Second check</th><th/></tr></thead>
      <tbody>{value?.items.map(item => <tr key={item.case_id}>
        <td>{item.title}</td><td>{item.score ?? '—'}</td><td>{item.level ? readable(item.level) : 'Not investigated'}</td>
        <td>{item.contributors.map(c => readable(c.tool)).join(', ') || '—'}</td>
        <td>{item.review ? readable(item.review) : '—'}</td><td>{item.check ? readable(item.check) : '—'}</td>
        <td>{item.run_id ? <button onClick={() => openRun(item.case_id, item.run_id!)}>Open run</button> : <button onClick={() => openCase(item.case_id)}>Open case</button>}</td>
      </tr>)}</tbody></table>
    <CheckerLookup/>
  </section>;
}

type CheckRecord = {id: string; run_id: string; report_hash: string; maker_action: string; is_maker?: boolean; state?: string;
  decision?: {decision: string; outcome: string; reason: string; at: string} | null; report_view?: {sections: {title: string; lines: string[]}[]}};

export function FourEyesPanel({runId, reviewed}: {runId?: string; reviewed: boolean}) {
  const [check, setCheck] = useState<CheckRecord>();
  const [error, setError] = useState('');
  useEffect(() => {
    let live = true;
    setCheck(undefined); setError('');
    if (runId) api<CheckRecord>(`/runs/${runId}/checks`).then(value => {if (live) setCheck(value);}).catch(caught => {if (live) setError(caught.message);});
    return () => {live = false;};
  }, [runId, reviewed]);
  async function request() {
    setError('');
    try {setCheck(await api<CheckRecord>(`/runs/${runId}/checks`, {}));} catch (caught) {setError((caught as Error).message);}
  }
  if (!runId) return null;
  return <section className="panel">
    <span className="eyebrow">MAKER-CHECKER / FOUR EYES</span><h2>Second review</h2>
    <p className="muted">After your immutable review, request a check. A different signed-in investigator concurs or disputes against the same report hash; disagreement escalates and never overwrites your review.</p>
    {error && <p role="alert">{error}</p>}
    {check?.id ? <>
      <div className="fact-line"><strong>Check ID</strong><span className="record-id">{check.id}</span></div>
      <div className="fact-line"><strong>Maker decision</strong><span>{readable(check.maker_action)}</span></div>
      <div className="fact-line"><strong>Checker outcome</strong><span>{check.decision ? `${readable(check.decision.outcome)} · ${check.decision.reason}` : 'Awaiting a second investigator'}</span></div>
    </> : <button disabled={!reviewed} onClick={() => void request()}>{reviewed ? 'Request second review' : 'Record your review first'}</button>}
  </section>;
}

function CheckerLookup() {
  const [id, setId] = useState('');
  const [check, setCheck] = useState<CheckRecord>();
  const [decision, setDecision] = useState('concur');
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  async function load() {
    setError(''); setCheck(undefined);
    try {setCheck(await api<CheckRecord>(`/checks/${encodeURIComponent(id.trim())}`));} catch (caught) {setError((caught as Error).message);}
  }
  async function decide() {
    if (!check) return;
    setError('');
    try {
      const value = await api<CheckRecord['decision']>(`/checks/${check.id}/decision`, {report_hash: check.report_hash, decision, reason});
      setCheck({...check, decision: value});
    } catch (caught) {setError((caught as Error).message);}
  }
  return <div className="checker-lookup">
    <h3>Check a colleague's review</h3>
    <p className="muted">Requires restricted investigator sign-in. You cannot check your own review.</p>
    <form className="filter-row" onSubmit={event => {event.preventDefault(); void load();}}>
      <label>Check ID<input value={id} onChange={event => setId(event.target.value)}/></label>
      <button disabled={!id.trim()}>Open check</button>
    </form>
    {error && <p role="alert">{error}</p>}
    {check && <article className="finding-card">
      <div className="fact-line"><strong>Report hash</strong><span className="record-id">{check.report_hash}</span></div>
      <div className="fact-line"><strong>Maker decision</strong><span>{readable(check.maker_action)}</span></div>
      {check.report_view?.sections.slice(0, 1).map(section => <details key={section.title}><summary>{section.title}</summary><pre>{section.lines.join('\n')}</pre></details>)}
      {check.decision ? <p className="coverage">{readable(check.decision.outcome)} · {check.decision.reason}</p> : check.is_maker ? <p className="empty">You made this review; another investigator must check it.</p> :
        <form onSubmit={event => {event.preventDefault(); void decide();}}>
          <div className="segmented"><button type="button" aria-pressed={decision === 'concur'} onClick={() => setDecision('concur')}>Concur</button><button type="button" aria-pressed={decision === 'dispute'} onClick={() => setDecision('dispute')}>Dispute</button></div>
          <label>Reason<textarea required minLength={5} value={reason} onChange={event => setReason(event.target.value)}/></label>
          <button className="primary" disabled={reason.trim().length < 5}>Record immutable check</button>
        </form>}
    </article>}
  </div>;
}

type EvaluationRun = {run: string; run_started_local: string; mode: string; split: string; case_count: number; repeats: number; attempts: number; completed: number;
  errors: Record<string, number>; true_positive_labels: number; false_positive_labels: number; false_negative_labels: number; precision: number | null; recall: number | null;
  control_attempts: number; control_attempts_with_false_positive: number; citation_scope_valid_rate: number | null; source_scope_valid_rate: number | null;
  mean_model_calls: number | null; mean_input_tokens: number | null; mean_output_tokens: number | null; mean_elapsed_seconds: number | null; extraction_quality_measured: boolean; scope: string; synthesis_semantic_support: string};
const percent = (value: number | null) => value === null ? 'Not measured' : `${(value * 100).toFixed(1)}%`;
const number = (value: number | null, digits = 0) => value === null ? 'Not measured' : value.toFixed(digits);

export function EvaluationScorecard() {
  const {value, error} = usePinned<{latest: Record<string, EvaluationRun>; history: {run: string; run_started_local: string; mode: string; split: string; completed: number; attempts: number; precision: number | null; recall: number | null}[]; interpretation: string}>('/evaluation');
  return <section className="panel">
    <span className="eyebrow">MEASURED / AGGREGATE ONLY</span><h2>Evaluation scorecard</h2>
    {error && <p role="alert">{error}</p>}
    {value && <>
      <p className="muted">{value.interpretation}</p>
      <div className="scorecard-grid">{(['live', 'offline'] as const).filter(mode => value.latest[mode]).map(mode => {
        const run = value.latest[mode];
        return <article className="finding-card" key={mode}>
          <span className="eyebrow">{mode === 'live' ? 'LIVE GEMINI + GOOGLE CLOUD' : 'OFFLINE DETERMINISTIC ANALYTICS'}</span>
          <h3>{run.split} split · {run.run_started_local}</h3>
          <div className="metric-row"><div><strong>{percent(run.precision)}</strong><span>Label precision</span></div><div><strong>{percent(run.recall)}</strong><span>Label recall</span></div><div><strong>{percent(run.citation_scope_valid_rate)}</strong><span>Citations in scope</span></div></div>
          <div className="fact-line"><strong>Attempts</strong><span>{run.completed} completed of {run.attempts} ({run.case_count} cases × {run.repeats})</span></div>
          <div className="fact-line"><strong>Labels</strong><span>{run.true_positive_labels} TP · {run.false_positive_labels} FP · {run.false_negative_labels} FN</span></div>
          <div className="fact-line"><strong>Control cases with a false positive</strong><span>{run.control_attempts_with_false_positive} of {run.control_attempts}</span></div>
          <div className="fact-line"><strong>Source scope valid</strong><span>{percent(run.source_scope_valid_rate)}</span></div>
          {mode === 'live' && <>
            <div className="fact-line"><strong>Mean model calls</strong><span>{number(run.mean_model_calls, 1)}</span></div>
            <div className="fact-line"><strong>Mean tokens in / out</strong><span>{number(run.mean_input_tokens)} / {number(run.mean_output_tokens)}</span></div>
            <div className="fact-line"><strong>Mean elapsed</strong><span>{number(run.mean_elapsed_seconds, 1)} s</span></div>
          </>}
          <div className="fact-line"><strong>Errors</strong><span>{Object.entries(run.errors).map(([k, v]) => `${k}: ${v}`).join(', ') || 'None'}</span></div>
          <div className="fact-line"><strong>OCR quality measured</strong><span>{run.extraction_quality_measured ? 'Yes' : 'No'}</span></div>
          <p className="muted">{run.synthesis_semantic_support}</p>
        </article>;
      })}</div>
      <details><summary>All recorded runs ({value.history.length}), including failed ones</summary>
        <table className="triage-table"><thead><tr><th>Run</th><th>Mode</th><th>Split</th><th>Completed</th><th>Precision</th><th>Recall</th></tr></thead>
          <tbody>{value.history.map(run => <tr key={run.run}><td>{run.run_started_local}</td><td>{run.mode}</td><td>{run.split}</td><td>{run.completed}/{run.attempts}</td><td>{percent(run.precision)}</td><td>{percent(run.recall)}</td></tr>)}</tbody></table>
      </details>
    </>}
  </section>;
}
