"""Bounded, cited model advisories over a pinned run: challenge, RFI drafts, graph-query plans.

Models interpret deterministic outputs; they never compute facts, send messages or decide.
"""
import asyncio
import json
import re
import time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .analytics import redact_untrusted
from .insights import GraphQuery, _accounts_for, alternative_checks, change_drivers
from .models import digest
from .store import Conflict, mutate

KINDS = ("challenge", "rfi", "graph_query_plan")


class ChallengePoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_ids: list[str] = Field(min_length=1, max_length=10)
    legitimate_explanation: str = Field(max_length=800)
    what_would_falsify: str = Field(max_length=800)


class ChallengeAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    points: list[ChallengePoint] = Field(max_length=12)
    overall_caution: str = Field(max_length=1200)
    abstained: bool


class RfiDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recipient_role: Literal["customer", "relationship_manager", "counterparty_bank", "registry"]
    subject: str = Field(max_length=200)
    body: str = Field(max_length=2500)
    requested_items: list[str] = Field(max_length=10)
    evidence_ids: list[str] = Field(min_length=1, max_length=20)
    driver_ids: list[str] = Field(max_length=10)


class RfiAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    drafts: list[RfiDraft] = Field(max_length=6)
    abstained: bool


class GraphQueryPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start_id: str = Field(max_length=200)
    end_id: str | None = Field(default=None, max_length=200)
    max_hops: int = Field(ge=1, le=4)
    currency: str | None = Field(default=None, max_length=8)
    min_amount: str | None = Field(default=None, max_length=32)
    window_hours: int | None = Field(default=None, ge=1, le=720)
    rationale: str = Field(max_length=600)
    abstained: bool


SCHEMAS = {"challenge": ChallengeAnswer, "rfi": RfiAnswer, "graph_query_plan": GraphQueryPlan}
INSTRUCTIONS = {
    "challenge": "Act as a devil's advocate reviewer. For each indicator, give the strongest "
                 "legitimate explanation and the specific evidence that would falsify the "
                 "suspicious hypothesis. Use the supplied deterministic alternative checks; do not "
                 "contradict them. Cite only supplied evidence IDs. Abstain if evidence is absent.",
    "rfi": "Draft requests for information that an investigator may edit and send. Drafts are "
           "never sent automatically. Be neutral; do not allege wrongdoing or reveal internal "
           "suspicion to the customer. Base each request on supplied change drivers and cite "
           "evidence IDs. Refer to records by description, not by numbers.",
    "graph_query_plan": "Translate the investigator question into the GraphQueryPlan schema. Use "
                        "only supplied account or entity IDs. Do not answer the question; the "
                        "plan is shown to the investigator before deterministic execution. "
                        "Abstain if the question cannot be expressed as a bounded path query.",
}


def _digit_free(*texts):
    if any(re.search(r"\d", text or "") for text in texts):
        raise ValueError("Model prose must be digit-free; numeric facts stay in tool output")


def compact_evidence(report):
    return redact_untrusted([{"id": e["id"], "tool": e["tool"], "claim_kind": e["claim_kind"],
                              "payload": {k: v for k, v in e.get("payload", {}).items()
                                          if k not in ("text", "fields")},
                              "limitations": e.get("limitations", [])}
                             for e in report.get("evidence", [])])


def context_for(kind, snapshot, report, question):
    case = snapshot.case
    if kind == "graph_query_plan":
        return {"question": question,
                "accounts": [{"id": a.id, "holder": a.entity_id} for a in case.accounts],
                "entities": [{"id": e.id, "name": e.name, "kind": e.kind} for e in case.entities],
                "currencies": sorted({t.currency for t in case.transactions})}
    value = {"evidence": compact_evidence(report),
             "synthesis": redact_untrusted(report.get("synthesis")),
             "alternative_checks": alternative_checks(case, report)["checks"]}
    if kind == "rfi":
        value["change_drivers"] = change_drivers(case, report)["drivers"]
    return value


def validate(kind, raw, snapshot, report, context):
    answer = SCHEMAS[kind].model_validate(raw)
    allowed = {e["id"] for e in report.get("evidence", [])}
    if kind == "challenge":
        _digit_free(answer.overall_caution, *(p.legitimate_explanation for p in answer.points),
                    *(p.what_would_falsify for p in answer.points))
        if any(not set(p.evidence_ids) <= allowed for p in answer.points):
            raise ValueError("Challenge cited evidence outside the pinned run")
        if not answer.abstained and not answer.points:
            raise ValueError("A challenge requires cited points or an abstention")
        return answer.model_dump() | {"status": "advisory_requires_review"}
    if kind == "rfi":
        drivers = {d["id"] for d in context["change_drivers"]}
        for draft in answer.drafts:
            _digit_free(draft.subject, draft.body, *draft.requested_items)
            if not set(draft.evidence_ids) <= allowed:
                raise ValueError("Draft cited evidence outside the pinned run")
            if not set(draft.driver_ids) <= drivers:
                raise ValueError("Draft referenced an unknown change driver")
        if not answer.abstained and not answer.drafts:
            raise ValueError("RFI output requires drafts or an abstention")
        return answer.model_dump() | {"status": "draft_not_sent"}
    _digit_free(answer.rationale)
    if answer.abstained:
        return answer.model_dump() | {"status": "abstained", "query": None}
    query = GraphQuery(**answer.model_dump(exclude={"rationale", "abstained"}))
    _accounts_for(snapshot.case, query.start_id)
    _accounts_for(snapshot.case, query.end_id)
    return answer.model_dump() | {"status": "plan_requires_confirmation",
                                  "query": query.model_dump()}


def verify_pinned(report, snapshot, run_id, expected_report_hash):
    report_hash = report.get("hash") or digest(report)
    if report.get("hash") and digest({k: v for k, v in report.items() if k != "hash"}) != report_hash:
        raise ValueError("Pinned report integrity mismatch")
    if report.get("input_hash", snapshot.snapshot_id) != snapshot.snapshot_id:
        raise ValueError("Report belongs to another snapshot")
    if report.get("run_id", run_id) != run_id:
        raise ValueError("Report belongs to another run")
    if report_hash != expected_report_hash:
        raise Conflict("Pinned report hash changed")
    return report_hash


async def run_advisory(operations, owner, run_id, snapshot, report, kind, key,
                       expected_report_hash, generate, question=""):
    """`generate` is the real bounded Google adapter; there is no simulated fallback."""
    if kind not in KINDS:
        raise ValueError("Unknown advisory kind")
    question = " ".join(str(question or "").split())
    if kind == "graph_query_plan" and not 5 <= len(question) <= 1000:
        raise ValueError("A graph question between five and one thousand characters is required")
    report_hash = verify_pinned(report, snapshot, run_id, expected_report_hash)
    context = context_for(kind, snapshot, report, question)
    sources = [digest(item) for item in report.get("evidence", [])]
    operation = operations.reserve(owner, "advisory:" + kind, key, snapshot.snapshot_id,
                                   report_hash, sources,
                                   {"run_id": run_id, "kind": kind, "question": question})
    if operation["state"] == "terminal":
        return operation
    execution = operations.begin(owner, operation["id"])
    try:
        if generate is None:
            raise ValueError("Google synthesis is unavailable")
        raw = await asyncio.wait_for(generate(kind, context, execution), timeout=execution.check())
        result = validate(kind, raw, snapshot, report, context)
        execution.check()
        return operations.finish(execution, result=result)
    except Exception:
        try:
            operations.finish(execution, error="Advisory processing failed; explicit new request required")
        except Exception:
            pass
        raise


async def bounded_generate(store, execution, payload, instruction, schema, usage_key):
    """One throttled, deadline-fenced, schema-constrained Gemini call with recorded usage."""
    from google import genai
    from google.genai import types

    from .cloud import PROJECT, credentials
    from .investigation import MODEL

    execution.check()
    now = time.time()

    def reserve_slot(old):
        start = max(now, (old or {}).get("next_at", now))
        if start - now > 30:
            raise ValueError("Model traffic is busy")
        return {"next_at": start + 1.5, "start_at": start}

    slot = mutate(store, "usage/model-rate-v1", reserve_slot)
    await asyncio.sleep(max(0, slot["start_at"] - time.time()))
    remaining = execution.check()
    text = json.dumps(payload)
    if len((text + instruction).encode()) > 48000:
        raise ValueError("Model input allowance exceeded")
    client = genai.Client(vertexai=True, project=PROJECT, location="global",
                          credentials=credentials(),
                          http_options=types.HttpOptions(timeout=int(min(remaining, 40) * 1000),
                                                         retry_options=types.HttpRetryOptions(attempts=1)))
    try:
        result = await client.aio.models.generate_content(
            model=MODEL, contents=text,
            config=types.GenerateContentConfig(system_instruction=instruction,
                                               max_output_tokens=1600, temperature=0,
                                               response_mime_type="application/json",
                                               response_schema=schema))
        execution.check()
        value = json.loads(result.text)
        usage = result.usage_metadata
        store.put(usage_key, {
            "input_tokens": usage.prompt_token_count if usage else None,
            "output_tokens": (usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0)
            if usage else None,
            "input_bytes": len((text + instruction).encode()), "model": MODEL,
        })
        return value
    finally:
        await client.aio.aclose()
