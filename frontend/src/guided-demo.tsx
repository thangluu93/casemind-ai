export type DemoStep = {title: string; body: string; tab: string; caseIndex?: number};

export const DEMO_STEPS: DemoStep[] = [
  {title: 'Fragmented evidence, one workspace', tab: 'Overview', caseIndex: 0,
    body: 'Select the main synthetic case. Source counts are visible before anything runs. Press Run investigation to execute the live specialists; the tour never starts billed work for you.'},
  {title: 'Watch the specialists work', tab: 'Overview', caseIndex: 0,
    body: 'The timeline records each specialist and tool call. Select a hypothesis citation to highlight only the edges it cites in the graph.'},
  {title: 'Follow the money', tab: 'Money trail', caseIndex: 0,
    body: 'Directed, chronological transfers with exact decimal amounts. A connected path does not prove the same funds moved.'},
  {title: 'Replay the flow over time', tab: 'Replay', caseIndex: 0,
    body: 'Play the transfers in recorded order to see the layering sequence unfold.'},
  {title: 'Who owns whom', tab: 'Ownership', caseIndex: 0,
    body: 'Per-step percentages, the exact path product and every unknown are shown. No legal beneficial-owner conclusion is drawn.'},
  {title: 'Map indicators to typologies', tab: 'Typologies', caseIndex: 0,
    body: 'Recorded indicators are mapped to typology categories, with observed, not observed and not evaluated kept distinct.'},
  {title: 'Argue the other side', tab: 'Challenge', caseIndex: 0,
    body: 'Deterministic checks test legitimate explanations, and a ranked list shows which missing information would change the picture most.'},
  {title: 'Test the thresholds', tab: 'What-if', caseIndex: 0,
    body: 'Change a demonstration rule and see which transactions would enter or leave each indicator. The report stays unchanged.'},
  {title: 'Similar names are not matches', tab: 'Watchlist', caseIndex: 2,
    body: 'The screening control compares identifiers field by field. Conflicting and missing identifiers stay visible.'},
  {title: 'Documents that try to give orders', tab: 'Findings', caseIndex: 5,
    body: 'This safety control contains text telling the reviewer to approve the case. It is detected, withheld from model context and never clears anyone.'},
  {title: 'A human decides, a second human checks', tab: 'Overview', caseIndex: 0,
    body: 'Record an immutable review bound to the report hash, then request a maker-checker second review.'},
  {title: 'Measured, not claimed', tab: 'Evaluation', caseIndex: 0,
    body: 'Aggregate results from recorded benchmark runs, with live and offline runs separated and failures retained.'},
];

type Props = {step: number; onGo: (step: number) => void; onClose: () => void};

export function GuidedDemo({step, onGo, onClose}: Props) {
  const current = DEMO_STEPS[step];
  return <aside className="guided-demo" role="dialog" aria-label="Guided demo">
    <span className="eyebrow">GUIDED DEMO · STEP {step + 1} OF {DEMO_STEPS.length}</span>
    <h3>{current.title}</h3>
    <p>{current.body}</p>
    <div className="citation-row">
      <button disabled={step === 0} onClick={() => onGo(step - 1)}>Back</button>
      {step < DEMO_STEPS.length - 1 ? <button className="primary" onClick={() => onGo(step + 1)}>Next</button> : <button className="primary" onClick={onClose}>Finish</button>}
      <button onClick={onClose}>Close</button>
    </div>
  </aside>;
}
