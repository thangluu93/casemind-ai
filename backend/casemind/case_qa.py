"""Pinned, bounded case questions with deterministic exact facts and cited synthesis."""
import asyncio
import json
import re
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from .models import digest


class ModelAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str = Field(max_length=3000)
    evidence_ids: list[str] = Field(max_length=20)
    abstained: bool
    limitations: list[str] = Field(max_length=10)


def normalized_question(question):
    if not isinstance(question, str):
        raise ValueError("Question must be text")
    question = " ".join(question.split())
    if not 5 <= len(question) <= 2000:
        raise ValueError("Question must contain between five and two thousand characters")
    return question


def retrieval(report, snapshot):
    evidence = report.get("evidence", [])
    if len(evidence) > 100:
        raise ValueError("Pinned evidence retrieval count limit exceeded")
    from .analytics import redact_untrusted
    context = {"evidence": redact_untrusted(evidence), "synthesis": report.get("synthesis"),
               "limitations": report.get("limitations", []),
               "case_id": snapshot.case.id, "snapshot_hash": snapshot.snapshot_id}
    if len(json.dumps(context, default=str).encode()) > 64000:
        raise ValueError("Pinned retrieval byte limit exceeded")
    if any(item.get("case_id", snapshot.case.id) != snapshot.case.id for item in evidence):
        raise ValueError("Evidence belongs to another case")
    return context


def classify(question):
    lower = question.lower()
    if any(term in lower for term in ("http://", "https://", "execute sql", "select *",
                                     "other case", "another case", "approve", "disposition",
                                     "ignore instructions", "ignore previous", "system prompt",
                                     "is guilty", "criminality", "search the web")):
        return "unsupported"
    if re.search(r"\b(?:transactions?|amounts?|totals?|how many|counts?|percentages?|balance|sum)\b", lower):
        return "deterministic"
    if any(term in lower for term in ("finding", "evidence", "uncertain", "contradict", "explain",
                                     "summary", "summarize", "follow up", "follow-up", "limitation",
                                     "hypothes", "risk", "alternative", "document", "ownership",
                                     "screening", "watchlist")):
        return "synthesis"
    return "unsupported"


def _source_refs(snapshot, group, records, scope=None):
    records = sorted(records, key=lambda record: record.id)
    refs = [{"kind": "record", "snapshot_hash": snapshot.snapshot_id,
             "record_id": record.id, "group": group} for record in records[:200]]
    if not records or len(records) > 200:
        refs.append({"kind": "inventory", "snapshot_hash": snapshot.snapshot_id,
                     "record_id": None, "group": group, "record_count": len(records),
                     "collection_hash": digest([record.model_dump(mode="json") for record in records]),
                     "scope": scope or {}, "truncated": len(records) > 200})
    return refs


def deterministic_answer(question, snapshot, report):
    case = snapshot.case
    def mentioned(identity):
        return bool(re.search(r"(?<![\w:-])" + re.escape(identity) + r"(?![\w:-])", question))
    relevant = [t for t in case.transactions if mentioned(t.id)]
    selected_accounts = {account.id for account in case.accounts if mentioned(account.id)}
    selected_entities = {entity.id for entity in case.entities if mentioned(entity.id)}
    selected_accounts |= {account.id for account in case.accounts
                          if account.entity_id in selected_entities}
    lower = question.lower()
    sender_only = any(term in lower for term in ("sent by", "sent from", "outgoing", "sender"))
    receiver_only = any(term in lower for term in ("received by", "received into", "incoming", "receiver"))
    selected_transactions = [transaction for transaction in case.transactions
        if not selected_accounts or
        ((not receiver_only and transaction.sender in selected_accounts) or
         (not sender_only and transaction.receiver in selected_accounts))]
    cited_ids = set()
    scope = {"account_ids": sorted(selected_accounts), "entity_ids": sorted(selected_entities),
             "direction": "outgoing" if sender_only else "incoming" if receiver_only else "all"}
    lower = question.lower()
    facts = []
    if relevant:
        facts = [{"transaction_id": t.id, "amount": str(t.amount), "currency": t.currency,
                  "sender": t.sender, "receiver": t.receiver,
                  "timestamp": t.timestamp.isoformat(),
                  "source_refs": _source_refs(snapshot, "transactions", [t])} for t in relevant]
        cited_ids.update(t.id for t in relevant)
        if "why" in lower or "reason" in lower:
            from .explanations import build_transaction_reasons
            from .models import Evidence
            evidence = [Evidence.model_validate(e) for e in report.get("evidence", [])]
            for fact in facts:
                fact["reasons"] = build_transaction_reasons(snapshot, evidence,
                                                            fact["transaction_id"])
    elif "how many" in lower or re.search(r"\bcounts?\b", lower):
        unsupported_filter = any(term in lower for term in ("suspicious", "flagged", "greater", "less than",
            "over ", "under ", "before ", "after ", "between ", "at least", "at most"))
        if not unsupported_filter:
            if "transaction" in lower:
                facts = [{"transaction_count": len(selected_transactions),
                          "scope_account_ids": sorted(selected_accounts),
                          "source_refs": _source_refs(snapshot, "transactions", selected_transactions, scope)}]
                cited_ids.update(record.id for record in selected_transactions)
            else:
                groups = (("account", "accounts"), ("entit", "entities"), ("document", "documents"),
                          ("relationship", "relationships"), ("watchlist", "watchlist"))
                selected_group = next((group for term, group in groups if term in lower), None)
                if selected_group:
                    selected_records = getattr(case, selected_group)
                    if selected_entities:
                        if selected_group in ("accounts", "documents"):
                            selected_records = [record for record in selected_records
                                                if record.entity_id in selected_entities]
                        elif selected_group == "relationships":
                            selected_records = [record for record in selected_records
                                                if record.owner in selected_entities or record.owned in selected_entities]
                    facts = [{selected_group + "_count": len(selected_records),
                              "source_refs": _source_refs(snapshot, selected_group, selected_records, scope)}]
                    cited_ids.update(record.id for record in selected_records)
    elif ("total" in lower or "sum" in lower) and ("amount" in lower or "transaction" in lower):
        if any(term in lower for term in ("greater", "less than", "over ", "under ", "before ", "after ", "between ")):
            return {"answer": "This numeric filter is not supported by the pinned deterministic query.",
                    "facts": [], "evidence_ids": [], "source_refs": [], "abstained": True, "limitations": [],
                    "method": "deterministic", "snapshot_hash": snapshot.snapshot_id}
        totals = {}
        for transaction in selected_transactions:
            totals[transaction.currency] = totals.get(transaction.currency, Decimal(0)) + transaction.amount
        facts = [{"currency": currency, "total_amount": str(amount),
                  "source_refs": _source_refs(snapshot, "transactions",
                     [record for record in selected_transactions if record.currency == currency],
                     scope | {"currency": currency})}
                 for currency, amount in sorted(totals.items())]
        cited_ids.update(record.id for record in selected_transactions)
    elif "percentage" in lower:
        facts = [{"relationship_id": item.id, "owner": item.owner, "owned": item.owned,
                  "percentage": str(item.percentage) if item.percentage is not None else None,
                  "source_refs": _source_refs(snapshot, "relationships", [item])}
                 for item in case.relationships if mentioned(item.id) or mentioned(item.owner)
                 or mentioned(item.owned)]
        cited_ids.update(fact["relationship_id"] for fact in facts)
    evidence_ids = sorted({item["id"] for item in report.get("evidence", [])
                           if set(item.get("refs", [])) & cited_ids})
    unique_refs = {digest(ref): ref for fact in facts for ref in fact.get("source_refs", [])}
    source_refs = sorted(unique_refs.values(), key=lambda ref: (ref["group"], ref["kind"], ref["record_id"] or ""))
    if sum(ref["kind"] == "record" for ref in source_refs) > 200:
        inventories = []
        for group in sorted({ref["group"] for ref in source_refs}):
            records = [record for record in getattr(case, group) if record.id in cited_ids]
            inventories.append({"kind": "inventory", "snapshot_hash": snapshot.snapshot_id,
                "record_id": None, "group": group, "record_count": len(records),
                "collection_hash": digest([record.model_dump(mode="json")
                                           for record in sorted(records, key=lambda record: record.id)]),
                "scope": scope, "truncated": True})
        source_refs = [ref for ref in source_refs if ref["kind"] == "record"][:200] + inventories
    limitations = ["Indicators do not establish criminality; human review is required."]
    if any(ref.get("truncated") for ref in source_refs):
        limitations.append("Source links show a bounded subset; the pinned inventory hash and count cover the complete selected collection.")
    return {"answer": "Exact facts from the pinned synthetic snapshot." if facts else
            "Specify a transaction or relationship in this pinned case.",
            "facts": facts, "evidence_ids": evidence_ids, "source_refs": source_refs,
            "abstained": not bool(facts), "limitations": limitations,
            "method": "deterministic", "snapshot_hash": snapshot.snapshot_id}


def validate_answer(raw, allowed):
    answer = ModelAnswer.model_validate(raw)
    if any(re.search(r"\d", text) for text in [answer.answer, *answer.limitations]):
        raise ValueError("Model prose must be digit-free")
    if not set(answer.evidence_ids) <= allowed:
        raise ValueError("Answer cited evidence outside the pinned run")
    if not answer.abstained and not answer.evidence_ids:
        raise ValueError("An answer requires pinned evidence citations")
    return answer


async def ask_question(operations, owner, run_id, snapshot, report, question, key,
                       expected_report_hash, synthesis=None):
    """Synthesis is an injected real bounded Google adapter; no runtime mock fallback."""
    question = normalized_question(question)
    report_hash = report.get("hash") or digest(report)
    if report.get("hash") and digest({k: v for k, v in report.items() if k != "hash"}) != report_hash:
        raise ValueError("Pinned report integrity mismatch")
    if report.get("input_hash", snapshot.snapshot_id) != snapshot.snapshot_id:
        raise ValueError("Report belongs to another snapshot")
    if report.get("run_id", run_id) != run_id:
        raise ValueError("Report belongs to another run")
    if report_hash != expected_report_hash:
        from .store import Conflict
        raise Conflict("Pinned report hash changed")
    context = retrieval(report, snapshot)
    family = classify(question)
    refs = {ref for evidence in context["evidence"] for ref in evidence.get("refs", [])}
    source_hashes = [digest(snapshot.case.sources[ref]) for ref in refs
                     if ref in snapshot.case.sources]
    source_hashes += [ref.sha256 for key, ref in snapshot.source_objects.items() if key in refs]
    source_hashes += [digest(item) for item in context["evidence"]]
    operation = operations.reserve(owner, "question", key, snapshot.snapshot_id, report_hash,
                                   source_hashes,
                                   {"question": question, "run_id": run_id}, bill=family == "synthesis")
    if operation["state"] == "terminal":
        return operation
    execution = operations.begin(owner, operation["id"])
    try:
        if family == "unsupported":
            answer = {"answer": "This question is outside the supported pinned case scope.",
                      "facts": [], "evidence_ids": [], "abstained": True,
                      "limitations": ["No external searches, decisions or cross-case retrieval."],
                      "method": "abstention"}
        elif family == "deterministic":
            answer = deterministic_answer(question, snapshot, report)
        else:
            if synthesis is None:
                raise ValueError("Google synthesis is unavailable")
            execution.check()
            raw = await asyncio.wait_for(synthesis(question, context, execution),
                                         timeout=execution.check())
            answer = validate_answer(raw, {e["id"] for e in context["evidence"]}).model_dump()
            answer.update({"method": "hypothesis", "facts": []})
        execution.check()
        return operations.finish(execution, result=answer)
    except Exception:
        # Retain a sanitized failure and quota; never replay uncertain provider work.
        try:
            operations.finish(execution, error="Question processing failed; explicit new request required")
        except Exception:
            pass
        raise
