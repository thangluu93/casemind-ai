import {useState} from 'react';
import type {CaseData, RecordData} from './api';
import {text} from './workspace-api';
import type {QuestionSourceRef} from './case-qa';
const groups = ['entities','accounts','transactions','relationships','documents','watchlist'] as const;
export function SourceExplorer({data, inspect, inventory}: {data: CaseData; inspect: (id:string)=>void; inventory?: QuestionSourceRef}) {
  const [group,setGroup]=useState<typeof groups[number]>(groups.find(group=>group===inventory?.group)||'transactions');
  const [query,setQuery]=useState('');
  const rows = (data[group] as RecordData[]).filter(row=> {
    if (inventory?.group !== group || !inventory.scope) return true;
    const {account_ids=[],entity_ids=[],direction,currency}=inventory.scope;
    if (group==='transactions') return (!currency||row.currency===currency)&&(!account_ids.length||
      ((direction!=='incoming'&&account_ids.includes(String(row.sender)))||
       (direction!=='outgoing'&&account_ids.includes(String(row.receiver)))));
    if (!entity_ids.length) return true;
    if (group==='accounts'||group==='documents') return entity_ids.includes(String(row.entity_id));
    if (group==='relationships') return entity_ids.includes(String(row.owner))||entity_ids.includes(String(row.owned));
    return true;
  });
  const filtered=rows.filter(row=>JSON.stringify(row).toLowerCase().includes(query.toLowerCase()));
  const fields= group==='transactions'?['id','sender','receiver','amount','currency','timestamp']:group==='entities'?['id','name','kind','identifiers']:group==='accounts'?['id','entity_id','bank_id']:group==='relationships'?['id','owner','owned','percentage']:group==='watchlist'?['id','name','category','identifiers']:['id','entity_id','kind','fields'];
  return <section className="panel"><span className="eyebrow">SOURCE INVENTORY · SYNTHETIC</span><h2>Source explorer</h2><div className="filter-row"><label>Record type<select value={group} onChange={e=>setGroup(e.target.value as typeof group)}>{groups.map(g=><option key={g}>{g}</option>)}</select></label><label>Search sources<input value={query} onChange={e=>setQuery(e.target.value)} placeholder="ID, name or value" /></label></div><p className="muted">Showing {Math.min(filtered.length,200)} of {rows.length} supplied records. Search filters the selected snapshot; it does not change findings.</p><div className="table-scroll"><table><thead><tr>{fields.map(f=><th key={f}>{f.replaceAll('_',' ')}</th>)}<th>Source</th></tr></thead><tbody>{filtered.slice(0,200).map(row=><tr key={row.id}>{fields.map(f=><td key={f}>{text(row[f])}</td>)}<td><button onClick={()=>inspect(row.id)}>Inspect</button></td></tr>)}</tbody></table></div>{!filtered.length&&<p className="empty">No supplied records match this filter. This is not clearance.</p>}</section>;
}
