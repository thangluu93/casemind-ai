export type RecordData = {id: string; source_kind: string; [key: string]: unknown};
export type Entity = RecordData & {name: string; kind: string};
export type Account = RecordData & {entity_id: string};
export type Transaction = RecordData & {sender: string; receiver: string; amount: string; currency: string; timestamp: string};
export type Relationship = RecordData & {owner: string; owned: string; percentage: string | null};
export type CaseSummary = {id: string; title: string; description: string; transaction_count: number; document_count: number};
export type CaseData = Omit<CaseSummary, 'transaction_count' | 'document_count'> & {entities: Entity[]; accounts: Account[]; transactions: Transaction[]; relationships: Relationship[]; documents: RecordData[]; watchlist: RecordData[]};
export type Evidence = {id: string; tool: string; tool_version: number; source_kind: string; verification_status: string; refs: string[]; claim_kind: string; payload: Record<string, unknown>; limitations: string[]; parameters: Record<string, unknown>};
export type Run = {run_id: string; case_id: string; status: string; error?: string; events: {index: number; role: string; status: string; at: string; payload: Record<string, unknown>}[]};
export type Priority = {score: number; level: string; interpretation: string; contributors: {tool: string; weight: number; evidence_ids: string[]}[]};
export type Report = {run_id: string; hash: string; version: number; status: string; model: string; evidence: Evidence[]; gaps: unknown[]; priority?: Priority; usage: {input_tokens: number; output_tokens: number; elapsed_seconds: number; tool_calls: number}; synthesis: {summary: string; hypotheses: {text: string; evidence_ids: string[]}[]; alternatives: string[]; unresolved: string[]}};
export type Review = {action: string; reason?: string; at?: string};
export class ApiError extends Error {
  constructor(message: string, public status: number) {super(message); this.name = "ApiError";}
}
export async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, body === undefined ? {} : {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
  if (!response.ok) {
    const error = await response.json().catch(() => ({detail: 'Connection failed. Please retry.'}));
    throw new ApiError(typeof error.detail === 'string' ? error.detail : `Request failed (${response.status})`, response.status);
  }
  return response.json();
}
