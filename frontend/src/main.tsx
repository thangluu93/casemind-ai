import '@fontsource-variable/inter';
import {useEffect, useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {
  api,
  ApiError,
  type CaseData,
  type CaseSummary,
  type Evidence,
  type RecordData,
  type Report,
  type Review,
  type Run,
} from './api';
import {CaseHeader, Sidebar} from './case-navigation';
import {EvidenceColumn} from './evidence-review';
import {FlowGraph} from './flow-graph';
import {InvestigationTimeline, ReportPanel} from './investigation-report';
import {SourceExplorer} from './source-explorer';
import {WatchlistScreening} from './watchlist-screening';
import {FindingCards} from './finding-cards';
import {TransactionReasons} from './transaction-reasons';
import {InvestigationExplorer} from './investigation-explorers';
import {FollowUpWorkspace} from './follow-up-workspace';
import {CaseHistory} from './case-history';
import {CaseQA, type QuestionSourceRef} from './case-qa';
import {ChallengeWorkspace, EvaluationScorecard, FourEyesPanel, GraphQueryPanel, RfiDrafts, TransferReplay, TriageQueue, TypologyMap, WhatIfSimulator} from './insight-panels';
import {DEMO_STEPS, GuidedDemo} from './guided-demo';
import './styles.css';
const destinations = ['Overview','Triage','Watchlist','Sources','Findings','Transaction reasons','Money trail','Replay','Ownership','Documents','Typologies','Challenge','What-if','Graph query','RFI drafts','Follow-up','Case Q&A','History','Evaluation'] as const;
type Destination = typeof destinations[number];

function App() {
  const [tab,setTab] = useState<Destination>('Overview');
  const [tour, setTour] = useState<number>();
  const [sourceInventory, setSourceInventory] = useState<QuestionSourceRef>();
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [data, setData] = useState<CaseData>();
  const [run, setRun] = useState<Run>();
  const [report, setReport] = useState<Report>();
  const [review, setReview] = useState<Review>();
  const [evidence, setEvidence] = useState<Evidence>();
  const [source, setSource] = useState<RecordData>();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [reason, setReason] = useState('');
  const [action, setAction] = useState('needs_follow_up');
  const [reviewBusy, setReviewBusy] = useState(false);
  const selected = useRef('');
  const selectionVersion = useRef(0);
  const detailVersion = useRef(0);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const activePolling = useRef('');

  function resetCaseState() {
    detailVersion.current += 1;
    setSourceInventory(undefined);
    setData(undefined);
    setRun(undefined);
    setReport(undefined);
    setReview(undefined);
    setSource(undefined);
    setEvidence(undefined);
    setReason('');
    setError('');
  }

  async function loadCase(id: string) {
    if (busy) return;

    selected.current = id;
    const version = ++selectionVersion.current;
    resetCaseState();
    try {
      const next = await api<CaseData>(`/cases/${id}`);
      if (selectionVersion.current !== version) return;

      setData(next);
      const key = localStorage.getItem(`casemind:${id}`);
      if (!key) return;

      const previous = await api<Run>(`/cases/${id}/runs/${key}`).catch(() => undefined);
      if (!previous || selectionVersion.current !== version) return;

      setRun(previous);
      if (previous.status === 'running') {
        setBusy(true);
        activePolling.current = `${id}:${key}`;
        void poll(id, key);
      } else {
        await loadReport(previous, version);
      }
    } catch (caught) {
      if (selectionVersion.current === version) setError((caught as Error).message);
    }
  }

  async function loadReport(next: Run, version = selectionVersion.current) {
    if (!['awaiting_review', 'completed_with_gaps'].includes(next.status)) return;

    const [nextReport, nextReview, pinnedCase] = await Promise.all([
      api<Report>(`/runs/${next.run_id}/report`),
      api<Review>(`/runs/${next.run_id}/review`),
      api<CaseData>(`/runs/${next.run_id}/case`),
    ]);
    if (selectionVersion.current === version && selected.current === next.case_id) {
      setReport(nextReport);
      setReview(nextReview);
      setData(pinnedCase);
    }
  }

  async function poll(id: string, key: string) {
    if (selected.current !== id || activePolling.current !== `${id}:${key}`) return;

    const version = selectionVersion.current;
    try {
      const next = await api<Run>(`/cases/${id}/runs/${key}`);
      if (activePolling.current !== `${id}:${key}`) return;
      setRun(next);
      if (next.status !== 'running') {
        activePolling.current = '';
        setBusy(false);
        await loadReport(next, version);
        return;
      }
      if (next.error) setError(next.error);
    } catch {
      // The initial request may not yet have created its manifest.
    }
    if (activePolling.current === `${id}:${key}`) timer.current = setTimeout(() => poll(id, key), 1800);
  }

  useEffect(() => {
    api<CaseSummary[]>('/cases')
      .then(list => {
        setCases(list);
        if (list[0]) void loadCase(list[0].id);
      })
      .catch(caught => setError(caught.message));

    return () => {
      activePolling.current = '';
      if (timer.current) clearTimeout(timer.current);
    };
  }, []);

  async function start() {
    if (!data || busy) return;

    const previous = {data, run, report, review, evidence, source};
    const previousKey = localStorage.getItem(`casemind:${data.id}`);
    setBusy(true);
    setError('');
    setReport(undefined);
    setReview(undefined);
    setEvidence(undefined);
    setRun(undefined);
    setSource(undefined);
    const id = data.id;
    const version = ++selectionVersion.current;
    const key = crypto.randomUUID();
    let accepted = false;
    localStorage.setItem(`casemind:${id}`, key);
    activePolling.current = `${id}:${key}`;
    void poll(id, key);

    try {
      setData(await api<CaseData>(`/cases/${id}`));
      const next = await api<Run>(`/cases/${id}/runs`, {idempotency_key: key});
      accepted = true;
      if (timer.current) clearTimeout(timer.current);
      setRun(next);
      await loadReport(next, version);
      if (next.error) setError(next.error);
    } catch (caught) {
      if (!accepted && caught instanceof ApiError && (caught.status < 500 || caught.status === 503)) {
        setData(previous.data);
        setRun(previous.run);
        setReport(previous.report);
        setReview(previous.review);
        setEvidence(previous.evidence);
        setSource(previous.source);
        if (previousKey) localStorage.setItem(`casemind:${id}`, previousKey);
        else localStorage.removeItem(`casemind:${id}`);
      }
      setError((caught as Error).message);
      if (timer.current) clearTimeout(timer.current);
    } finally {
      activePolling.current = '';
      setBusy(false);
    }
  }

  async function inspect(id: string) {
    if (!data) return;
    const version = selectionVersion.current;
    const detail = ++detailVersion.current;

    try {
      const next = await api<RecordData>(run ? `/runs/${run.run_id}/sources/${encodeURIComponent(id)}` : `/cases/${data.id}/sources/${encodeURIComponent(id)}`);
      if (selectionVersion.current === version && detailVersion.current === detail) setSource(next);
    } catch (caught) {
      if (selectionVersion.current === version && detailVersion.current === detail) setError((caught as Error).message);
    }
  }

  async function saveReview() {
    if (!run || !report) return;

    const version = selectionVersion.current;
    setReviewBusy(true);
    setError('');
    try {
      const next = await api<Review>(`/runs/${run.run_id}/review`, {
        report_hash: report.hash,
        expected_version: report.version,
        action,
        reason,
      });
      if (selectionVersion.current === version) setReview(next);
    } catch (caught) {
      if (selectionVersion.current === version) setError((caught as Error).message);
    } finally {
      setReviewBusy(false);
    }
  }

  async function openHistory(caseId: string, runId?: string) {
    if (busy) return;
    selected.current = caseId;
    const version = ++selectionVersion.current;
    resetCaseState();
    setTab('Overview');
    try {
      if (runId) {
        const next = await api<Run>(`/runs/${runId}`);
        const current = await api<CaseData>(`/runs/${runId}/case`);
        if (selectionVersion.current !== version) return;
        setRun(next); setData(current);
        await loadReport(next, version);
      } else {await loadCase(caseId);}
    } catch (caught) {if (selectionVersion.current === version) setError((caught as Error).message);}
  }

  function goToStep(step: number) {
    const target = DEMO_STEPS[step];
    setTour(step);
    const caseId = target.caseIndex === undefined ? undefined : cases[target.caseIndex]?.id;
    if (caseId && caseId !== data?.id) void loadCase(caseId);
    setTab(target.tab as Destination);
  }

  function selectEvidence(next?: Evidence) {
    detailVersion.current += 1;
    setEvidence(next);
    setSource(undefined);
  }

  function closeDetail() {
    detailVersion.current += 1;
    setEvidence(undefined);
    setSource(undefined);
  }

  return (
    <div className="app-shell">
      <Sidebar cases={cases} currentCaseId={data?.id} busy={busy} onSelect={id => void loadCase(id)} />
      <main>
        <header className="topbar">
          <span>Financial crime investigation</span>
          <span className="topbar-actions"><button onClick={() => goToStep(0)} disabled={busy}>Guided demo</button><span className="synthetic-label">Synthetic data only</span></span>
        </header>
        <div className="workspace">
          <CaseHeader
            cases={cases}
            data={data}
            run={run}
            review={review}
            reportReady={Boolean(report)}
            busy={busy}
            onStart={() => void start()}
          />
          {error && (
            <div className="error-banner" role="alert">
              {error}<button onClick={() => setError('')} aria-label="Dismiss error">Dismiss</button>
            </div>
          )}
          <nav className="workspace-tabs" aria-label="Investigator features">{destinations.map(d=><button key={d} aria-current={tab===d?'page':undefined} onClick={()=>setTab(d)}>{d}</button>)}</nav>
          {data&&tab!=='Overview'&&<div className="scope-banner">Synthetic · {run ? `Pinned run ${run.run_id}` : `Selected case ${data.id}`} · {run?'Completed evidence is bound to this run.':'Source preview; no completed investigation implied.'}</div>}
          <div className="work-grid">
            <div className="analysis-column">
              {data&&tab==='Sources'&&<SourceExplorer key={`${data.id}:${run?.run_id}:${sourceInventory?.collection_hash}`} data={data} inventory={sourceInventory} inspect={id=>void inspect(id)}/>}
              {data&&tab==='Watchlist'&&<WatchlistScreening key={`${data.id}:${run?.run_id}`} scope={{caseId:data.id,runId:run?.run_id}} report={report} inspect={id=>void inspect(id)}/>}
              {tab==='Findings'&&<FindingCards report={report} select={selectEvidence}/>}
              {data&&tab==='Transaction reasons'&&<TransactionReasons key={`${data.id}:${run?.run_id}`} data={data} scope={{caseId:data.id,runId:run?.run_id}} inspect={id=>void inspect(id)}/>}
              {data&&['Money trail','Ownership','Documents'].includes(tab)&&<InvestigationExplorer key={`${data.id}:${run?.run_id}:${tab}`} kind={tab==='Money trail'?'money-trail':tab==='Ownership'?'ownership':'documents'} scope={{caseId:data.id,runId:run?.run_id}} data={data} inspect={id=>void inspect(id)}/>}
              {tab==='Follow-up'&&<FollowUpWorkspace key={run?.run_id} runId={run?.run_id} report={report} onChild={(id,rid)=>void openHistory(id,rid)}/>}
              {tab==='Case Q&A'&&<CaseQA key={run?.run_id} runId={run?.run_id} report={report} inspectSource={id=>void inspect(id)} inspectInventory={ref=>{setSourceInventory(ref);setTab('Sources');}} inspectEvidence={id=>selectEvidence(report?.evidence.find(e=>e.id===id))}/>}
              {tab==='History'&&<CaseHistory onSelect={(id,rid)=>void openHistory(id,rid)}/>}
              {tab==='Triage'&&<TriageQueue openRun={(id,rid)=>void openHistory(id,rid)} openCase={id=>{setTab('Overview');void loadCase(id);}}/>}
              {tab==='Typologies'&&<TypologyMap key={run?.run_id} runId={report?run?.run_id:undefined} inspectEvidence={id=>selectEvidence(report?.evidence.find(e=>e.id===id))}/>}
              {tab==='Challenge'&&<ChallengeWorkspace key={run?.run_id} runId={report?run?.run_id:undefined} report={report} inspect={id=>void inspect(id)} inspectEvidence={id=>selectEvidence(report?.evidence.find(e=>e.id===id))}/>}
              {tab==='What-if'&&<WhatIfSimulator key={run?.run_id} runId={report?run?.run_id:undefined} inspect={id=>void inspect(id)}/>}
              {data&&tab==='Graph query'&&<GraphQueryPanel key={`${data.id}:${run?.run_id}`} runId={report?run?.run_id:undefined} report={report} data={data} inspect={id=>void inspect(id)}/>}
              {tab==='RFI drafts'&&<RfiDrafts key={run?.run_id} runId={report?run?.run_id:undefined} report={report} inspectEvidence={id=>selectEvidence(report?.evidence.find(e=>e.id===id))}/>}
              {data&&tab==='Replay'&&<TransferReplay key={`${data.id}:${run?.run_id}`} data={data} inspect={id=>void inspect(id)}/>}
              {tab==='Evaluation'&&<EvaluationScorecard/>}
              {data && tab==='Overview' && (
                <FlowGraph
                  data={data}
                  select={setSource}
                  highlighted={evidence?.refs || (source ? [source.id] : [])}
                />
              )}
              {tab==='Overview'&&<InvestigationTimeline run={run} busy={busy} />}
              {report && tab==='Overview' && <ReportPanel report={report} runId={run?.run_id} onSelectEvidence={selectEvidence} />}
              {report && tab==='Overview' && <FourEyesPanel runId={run?.run_id} reviewed={Boolean(review && review.action !== 'pending')} />}
            </div>
            <EvidenceColumn
              data={data}
              report={report}
              review={review}
              evidence={evidence}
              source={source}
              action={action}
              reason={reason}
              reviewBusy={reviewBusy}
              onActionChange={setAction}
              onReasonChange={setReason}
              onSelectEvidence={selectEvidence}
              onInspectSource={id => void inspect(id)}
              onCloseDetail={closeDetail}
              onSaveReview={() => void saveReview()}
            />
          </div>
          {tour !== undefined && <GuidedDemo step={tour} onGo={goToStep} onClose={() => setTour(undefined)} />}
          <footer>CaseMind AI · Evidence before inference · AI Builder Cup prototype</footer>
        </div>
      </main>
    </div>
  );
}

createRoot(document.getElementById('root')!).render(<App />);
