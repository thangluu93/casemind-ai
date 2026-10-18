import {ApiError} from './api';

export type Scope = {caseId: string; runId?: string; snapshotId?: string};
export type SourceRef = {id: string; [key: string]: unknown};
export type Snapshot = {case_id?: string; snapshot_id?: string; source_kind?: string; origin?: string; [key: string]: unknown};
export function scopePath(scope: Scope) {return scope.runId ? `/runs/${encodeURIComponent(scope.runId)}` : `/cases/${encodeURIComponent(scope.caseId)}`;}
export async function upload(path: string, file: File, metadata: Record<string, string>): Promise<unknown> {
  // A raw bounded stream avoids multipart buffering before server-side limits.
  const query = new URLSearchParams({...metadata, filename: file.name});
  const response = await fetch(`/api${path}?${query}`, {method: 'POST', headers: {'Content-Type': file.type || 'application/octet-stream'}, body: file});
  const value = await response.json();
  if (!response.ok) throw new ApiError(value.detail || 'Upload failed', response.status);
  return value;
}
export function text(value: unknown): string {
  if (value === null || value === undefined) return 'Not supplied';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}
