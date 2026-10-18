import {useState} from 'react';
import type {CaseData, RecordData} from './api';

export function FlowGraph({data, select, highlighted}: {data: CaseData; select: (r: RecordData) => void; highlighted: string[]}) {
  const [mode, setMode] = useState<'transfers' | 'ownership'>('transfers');
  const nodes = mode === 'transfers' ? data.accounts : data.entities;
  const edges = mode === 'transfers' ? data.transactions : data.relationships;
  const positions = nodes.map((_, i) => ({x: 320 + Math.cos(i * Math.PI * 2 / nodes.length - Math.PI / 2) * 210, y: 210 + Math.sin(i * Math.PI * 2 / nodes.length - Math.PI / 2) * 135}));
  const entityName = (id: string) => data.entities.find(e => e.id === id)?.name.replace('Demo ', '') || id;
  return <section className="panel graph-panel" aria-labelledby="graph-title">
    <div className="panel-heading"><div><span className="eyebrow">CONNECTED RECORDS</span><h2 id="graph-title">Follow the evidence</h2></div>
      <div className="segmented" aria-label="Graph view"><button aria-pressed={mode === 'transfers'} onClick={() => setMode('transfers')}>Transfers</button><button aria-pressed={mode === 'ownership'} onClick={() => setMode('ownership')}>Ownership</button></div></div>
    <p className="muted graph-help">Select an account, entity or arrow to inspect its source. Arrows show direction.</p>
    {edges.length === 0 ? <div className="empty">No ownership relationships supplied for this case.</div> : <svg className="flow-graph" viewBox="0 0 640 430" role="group" aria-label="Directed source graph">
      <defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" /></marker></defs>
      {edges.map((edge, index) => {
        const fromId = mode === 'transfers' ? edge.sender : edge.owner;
        const toId = mode === 'transfers' ? edge.receiver : edge.owned;
        const a = positions[nodes.findIndex(n => n.id === fromId)], b = positions[nodes.findIndex(n => n.id === toId)];
        if (!a || !b) return null;
        const length = Math.hypot(b.x - a.x, b.y - a.y) || 1;
        const start = {x: a.x + (b.x - a.x) * 34 / length, y: a.y + (b.y - a.y) * 34 / length};
        const end = {x: b.x - (b.x - a.x) * 34 / length, y: b.y - (b.y - a.y) * 34 / length};
        const offset = ((index % 5) - 2) * 10;
        const cx = (a.x + b.x) / 2 + offset * (a.y - b.y) / length;
        const cy = (a.y + b.y) / 2 + offset * (b.x - a.x) / length;
        const label = mode === 'transfers' ? `${edge.currency} ${String(edge.amount)}` : `${edge.percentage ?? '?'}% shareholding`;
        return <g key={edge.id} className={`graph-edge ${highlighted.includes(edge.id) ? 'selected' : ''}`} role="button" tabIndex={0} aria-label={label} onClick={() => select(edge)} onKeyDown={e => {if (e.key === 'Enter' || e.key === ' ') {e.preventDefault(); select(edge);}}}>
          <title>{label} · {edge.id}</title><path className="edge-hit" d={`M${start.x},${start.y} Q${cx},${cy} ${end.x},${end.y}`} /><path className="edge-line" markerEnd="url(#arrow)" d={`M${start.x},${start.y} Q${cx},${cy} ${end.x},${end.y}`} />
        </g>;
      })}
      {nodes.map((node, i) => <g key={node.id} className={`graph-node ${highlighted.includes(node.id) ? 'selected' : ''}`} role="button" tabIndex={0} aria-label={entityName(mode === 'transfers' ? String(node.entity_id) : node.id)} onClick={() => select(node)} onKeyDown={e => {if (e.key === 'Enter' || e.key === ' ') {e.preventDefault(); select(node);}}}>
        <circle className="node-hit" cx={positions[i].x} cy={positions[i].y} r="52" />
        <circle cx={positions[i].x} cy={positions[i].y} r="30" /><text x={positions[i].x} y={positions[i].y + 5} textAnchor="middle">{mode === 'transfers' ? 'A' : node.kind === 'person' ? 'P' : 'E'}{i + 1}</text>
        <text className="node-label" x={positions[i].x} y={positions[i].y + 52} textAnchor="middle">{entityName(mode === 'transfers' ? String(node.entity_id) : node.id)}</text>
      </g>)}
    </svg>}
    <details><summary>Accessible source list · {edges.length} links</summary><div className="source-list">{edges.map(edge => <button key={edge.id} onClick={() => select(edge)}>{edge.id.split(':').at(-1)} · {mode === 'transfers' ? `${edge.currency} ${edge.amount}` : `${edge.percentage ?? 'Unknown'}% ownership`}</button>)}</div></details>
  </section>;
}
