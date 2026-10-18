import hashlib
import os
import re
import subprocess
from datetime import datetime, timezone

import google.auth
from google.auth.credentials import Credentials
from google.cloud import bigquery, documentai, storage

from .models import Case, Document, SnapshotRef, digest
from .case_resolver import snapshot_manifest
from .store import Conflict, GCSStore, UsageLedger

PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "casemind-ai")
REGION = os.getenv("CASEMIND_REGION", "asia-southeast1")
BUCKET = os.getenv("CASEMIND_BUCKET", "casemind-ai-prototype-251896792352")
DATASET = os.getenv("CASEMIND_DATASET", "casemind_prototype_v1")


class GcloudCredentials(Credentials):
    """Interactive local account only; tokens stay in process memory."""

    def refresh(self, request):
        self.token = subprocess.check_output(
            ["gcloud", "--configuration=casemind-ai", "auth", "print-access-token"],
            text=True,
            timeout=15,
        ).strip()
        from datetime import timedelta

        self.expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=30)


def credentials():
    if os.getenv("CASEMIND_USE_GCLOUD") == "true":
        return GcloudCredentials()
    return google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])[0]


def _remaining(execution, maximum):
    return min(maximum, execution.check()) if execution is not None else maximum


def _document_fields(document, offset):
    def text(anchor):
        return "".join(
            document.text[int(s.start_index) : int(s.end_index)] for s in anchor.text_segments
        ).strip()

    fields = []
    for page in document.pages:
        for form in page.form_fields:
            fields.append(
                {
                    "key": text(form.field_name.text_anchor),
                    "value": text(form.field_value.text_anchor),
                    "page": page.page_number,
                    "confidence": min(form.field_name.confidence, form.field_value.confidence),
                    "anchors": {
                        "key": [
                            {"start": offset + int(s.start_index), "end": offset + int(s.end_index)}
                            for s in form.field_name.text_anchor.text_segments
                        ],
                        "value": [
                            {"start": offset + int(s.start_index), "end": offset + int(s.end_index)}
                            for s in form.field_value.text_anchor.text_segments
                        ],
                    },
                }
            )
    # A deterministic adapter for these labelled synthetic forms uses actual OCR text and
    # provider token confidences. It never reads the generator's document field values.
    for label in ("Registration ID", "Beneficial Owner"):
        for match in re.finditer(r"(?m)^" + re.escape(label) + r"\s*\n([^\n]+)", document.text):
            start, end = match.span(1)
            tokens = []
            page_number = None
            for page in document.pages:
                for token in page.tokens:
                    if any(
                        int(segment.start_index) < end and int(segment.end_index) > start
                        for segment in token.layout.text_anchor.text_segments
                    ):
                        tokens.append(token.layout.confidence)
                        page_number = page.page_number
            fields.append(
                {
                    "key": label,
                    "value": match.group(1).strip(),
                    "page": page_number,
                    "confidence": min(tokens) if tokens else 0,
                    "extraction_method": "labelled_ocr_tokens",
                    "anchors": {
                        "key": [{"start": offset + match.start(), "end": offset + match.start() + len(label)}],
                        "value": [{"start": offset + start, "end": offset + end}],
                    },
                }
            )
    return fields


def _remap_ocr_batch(document, selected, offset):
    artifact = documentai.Document.to_dict(document)
    artifact.pop("text", None)
    def remap(value):
        if isinstance(value, list):
            for item in value:
                remap(item)
        elif isinstance(value, dict):
            for segment in value.get("text_segments", []):
                start, end = int(segment.get("start_index", 0)), int(segment.get("end_index", 0))
                if not 0 <= start <= end <= len(document.text):
                    raise ValueError("Document AI text anchor outside batch text")
                segment["start_index"], segment["end_index"] = str(offset + start), str(offset + end)
            for page_ref in value.get("page_refs", []):
                index = int(page_ref.get("page", 0))
                if not 0 <= index < len(selected):
                    raise ValueError("Document AI page anchor outside selected pages")
                page_ref["page"] = str(selected[index] - 1)
            for nested in value.values():
                remap(nested)
    remap(artifact)
    return {"selected_pages": selected, "text_offset": offset,
            "text_length": len(document.text), "text_anchor_space": "aggregated_text",
            "document": artifact}


class Cloud:
    def __init__(self):
        creds = credentials()
        self.storage = storage.Client(project=PROJECT, credentials=creds)
        self.bigquery = bigquery.Client(project=PROJECT, credentials=creds)
        self.documents = documentai.DocumentProcessorServiceClient(
            credentials=creds,
            client_options={"api_endpoint": f"{REGION}-documentai.googleapis.com"},
        )
        self.store = GCSStore(self.storage, BUCKET)
        self.ledger = UsageLedger(self.store)
        self.processor = os.getenv("CASEMIND_PROCESSOR", "")

    def load_case(self, snapshot_ref: SnapshotRef, documents: dict[str, bytes], execution=None):
        from google.api_core.exceptions import NotFound
        from .case_resolver import snapshot_from_manifest
        from .source_catalog import SourceCatalog
        case = snapshot_ref.case
        if len(case.transactions) > 5000:
            raise ValueError("Snapshot exceeds 5000 total transactions")
        snapshot = snapshot_ref.snapshot_id
        key = f"inputs/{case.id}/{snapshot}"
        table_id = f"{PROJECT}.{DATASET}.tx_{snapshot[:20]}"
        catalog = SourceCatalog(self.store)
        for doc in case.documents:
            _remaining(execution, 10)
            pdf = documents[doc.id]
            ref = snapshot_ref.source_objects.get(doc.id)
            if ref and catalog.read(ref) != pdf:
                raise ValueError("Original document differs")
            catalog.put(pdf, "application/pdf")
        schema = [bigquery.SchemaField(name, kind) for name, kind in (
            ("id", "STRING"), ("case_id", "STRING"), ("sender", "STRING"),
            ("receiver", "STRING"), ("amount", "NUMERIC"), ("currency", "STRING"),
            ("timestamp", "TIMESTAMP"))]
        rows = [dict(t.model_dump(mode="json"), case_id=case.id) for t in case.transactions]
        for row in rows:
            row.pop("source_kind")
        published, manifest_generation = self.store.get(key)
        if published and published.get("table"):
            if snapshot_from_manifest(published).snapshot_id != snapshot:
                raise ValueError("Published snapshot differs")
        else:
            intent_key = f"publications/{case.id}/{snapshot}"
            job_id = "snapshot_" + snapshot
            intent = {"version": 1, "snapshot_id": snapshot, "table": table_id,
                      "job_id": job_id, "transaction_hash": digest(rows)}
            _remaining(execution, 10)
            prior, _ = self.store.get(intent_key)
            if prior is None:
                self.store.put(intent_key, intent)
                _remaining(execution, 10)
                config = bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_EMPTY")
                job = self.bigquery.load_table_from_json(rows, table_id, job_config=config,
                    job_id=job_id, location=REGION, timeout=_remaining(execution, 15), num_retries=0)
            else:
                if prior != intent:
                    raise Conflict("Snapshot publication intent differs")
                try:
                    job = self.bigquery.get_job(job_id, location=REGION,
                        timeout=_remaining(execution, 10), retry=None)
                except NotFound:
                    # An explicitly invoked load is retry authority only after proving
                    # both deterministic job and destination table are absent.
                    try:
                        self.bigquery.get_table(table_id, timeout=_remaining(execution, 10), retry=None)
                    except NotFound:
                        config = bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_EMPTY")
                        job = self.bigquery.load_table_from_json(rows, table_id, job_config=config,
                            job_id=job_id, location=REGION, timeout=_remaining(execution, 15), num_retries=0)
                    else:
                        raise Conflict("Publication table exists without its authoritative job")
                if getattr(job, "destination", None) and str(job.destination) != table_id:
                    raise Conflict("Publication job destination differs")
            job.result(timeout=_remaining(execution, 45), retry=None)
        table = self.bigquery.get_table(table_id, timeout=_remaining(execution, 10), retry=None)
        if table.num_rows != len(rows) or [(f.name, f.field_type) for f in table.schema] != [(f.name, f.field_type) for f in schema]:
            raise ValueError("Snapshot table schema or count mismatch")
        self.query_transactions(snapshot_ref, execution=execution)
        for doc in case.documents:
            ref = snapshot_ref.source_objects.get(doc.id)
            if ref:
                _remaining(execution, 10)
                catalog.read(ref)
        _remaining(execution, 10)
        manifest = dict(snapshot_manifest(snapshot_ref), table=table_id)
        if not published or not published.get("table"):
            try:
                self.store.put(key, manifest, manifest_generation)
            except Conflict:
                existing, _ = self.store.get(key)
                if existing != manifest:
                    raise Conflict("Published manifest differs")

    def query_transactions(self, snapshot_ref: SnapshotRef, execution=None) -> Case:
        _remaining(execution, 10)
        case = snapshot_ref.case
        if len(case.transactions) > 5000:
            raise ValueError("Snapshot exceeds 5000 total transactions")
        snapshot = snapshot_ref.snapshot_id
        table = f"{PROJECT}.{DATASET}.tx_{snapshot[:20]}"
        # Table name derives only from a canonical digest; values are parameterized.
        sql = f"SELECT id,sender,receiver,amount,currency,timestamp FROM `{table}` WHERE case_id=@case_id ORDER BY timestamp,id LIMIT 5000"
        config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("case_id", "STRING", case.id)],
            maximum_bytes_billed=20 * 1024 * 1024,
            use_query_cache=True,
        )
        dry = bigquery.QueryJobConfig(dry_run=True, query_parameters=config.query_parameters)
        estimate = self.bigquery.query(sql, job_config=dry, location=REGION, timeout=_remaining(execution, 10), retry=None)
        if estimate.total_bytes_processed > 20 * 1024 * 1024:
            raise ValueError("BigQuery byte allowance exceeded")
        rows = list(
            self.bigquery.query(
                sql, job_config=config, location=REGION, timeout=_remaining(execution, 10), retry=None, job_retry=None
            ).result(timeout=_remaining(execution, 25), retry=None, job_retry=None)
        )
        if len(rows) != len(case.transactions):
            raise ValueError("BigQuery snapshot incomplete")
        from .models import Transaction

        txs = [Transaction(**dict(row)) for row in rows]
        ordered = sorted(case.transactions, key=lambda t: (t.timestamp, t.id))
        def canonical(transaction):
            return transaction.model_dump(mode="json") | {
                "amount": format(transaction.amount.normalize(), "f"),
                "timestamp": transaction.timestamp.astimezone(timezone.utc).isoformat(),
            }
        if digest([canonical(t) for t in txs]) != digest([canonical(t) for t in ordered]):
            raise ValueError("BigQuery snapshot integrity mismatch")
        return case.model_copy(update={"transactions": ordered})

    def extract(self, snapshot_ref: SnapshotRef, doc: Document, pdf: bytes, execution=None) -> dict:
        if doc.id not in snapshot_ref.case.sources:
            raise ValueError("Document outside snapshot")
        _remaining(execution, 10)
        from .source_catalog import SourceCatalog
        ref = snapshot_ref.source_objects.get(doc.id)
        if ref and SourceCatalog(self.store).read(ref) != pdf:
            raise ValueError("Original document generation differs")
        if ref and (hashlib.sha256(pdf).hexdigest() != ref.sha256 or len(pdf) != ref.byte_size):
            raise ValueError("Original document integrity mismatch")
        ref = ref or SourceCatalog(self.store).put(pdf, "application/pdf")
        pdf_hash = hashlib.sha256(pdf).hexdigest()
        key = "extraction/" + digest([pdf_hash, self.processor, "anchored-page-selection-v3"])
        cached, _ = self.store.get(key)
        if cached:
            return dict(cached, document_id=doc.id, snapshot_id=snapshot_ref.snapshot_id,
                        original_generation=ref.generation if ref else None)
        if not self.processor:
            raise ValueError("Document AI processor has not been configured")
        from .document_rendering import render_document
        from uuid import uuid4
        original = ref
        _remaining(execution, 15)
        page_count = len(render_document(pdf, original))
        fields, texts, batches = [], [], []
        offset = 0
        # Form Parser's synchronous limit is 15 selected pages. Preserve the
        # exact original bytes; returned page numbers remain original indices.
        for first in range(1, page_count + 1, 15):
            selected = list(range(first, min(first + 15, page_count + 1)))
            request = documentai.ProcessRequest(
                name=self.processor,
                raw_document=documentai.RawDocument(content=pdf, mime_type="application/pdf"),
                process_options=documentai.ProcessOptions(
                    individual_page_selector=documentai.ProcessOptions.IndividualPageSelector(
                        pages=selected)),
            )
            _remaining(execution, 10)
            self.ledger.reserve_pages(len(selected), uuid4().hex, pdf_hash)
            response = self.documents.process_document(
                request=request, retry=None, timeout=_remaining(execution, 30))
            _remaining(execution, 10)
            document = response.document
            if len(document.pages) != len(selected):
                raise ValueError("Document AI page count differs from selected original pages")
            if [page.page_number for page in document.pages] != selected:
                raise ValueError("Document AI page identities differ from selected original pages")
            batches.append(_remap_ocr_batch(document, selected, offset))
            fields.extend(_document_fields(document, offset))
            texts.append(document.text)
            offset += len(document.text)
        result = {
            "document_id": doc.id,
            "original_generation": ref.generation if ref else None,
            "snapshot_id": snapshot_ref.snapshot_id,
            "pdf_hash": pdf_hash,
            "processor": self.processor,
            "fields": fields,
            "text": "".join(texts),
            "page_count": page_count,
            "ocr_batches": batches,
            "extraction_version": "anchored-page-selection-v3",
        }
        _remaining(execution, 10)
        try:
            self.store.put(key, result)
        except Conflict:
            pass
        return result
