"""Create only dedicated prototype resources; never alter existing source tables."""

import json
from pathlib import Path

from google.cloud import bigquery, documentai

from casemind.case_resolver import demo_snapshot, CaseResolver
from casemind.cloud import BUCKET, DATASET, PROJECT, REGION, Cloud
from casemind.generator import demo_cases

cloud = Cloud()
bucket = cloud.storage.bucket(BUCKET)
if not bucket.exists():
    bucket.iam_configuration.uniform_bucket_level_access_enabled = True
    bucket.add_lifecycle_delete_rule(age=30)
    cloud.storage.create_bucket(bucket, location=REGION)
dataset = bigquery.Dataset(f"{PROJECT}.{DATASET}")
dataset.location = REGION
dataset.default_table_expiration_ms = 30 * 86400000
cloud.bigquery.create_dataset(dataset, exists_ok=True)
parent = f"projects/{PROJECT}/locations/{REGION}"
processors = list(cloud.documents.list_processors(request={"parent": parent}))
processor = next(
    (p for p in processors if p.display_name == "casemind-synthetic-form-parser"), None
)
if processor is None:
    processor = cloud.documents.create_processor(
        request={
            "parent": parent,
            "processor": documentai.Processor(
                type_="FORM_PARSER_PROCESSOR", display_name="casemind-synthetic-form-parser"
            ),
        }
    )
cloud.processor = processor.name
cases = demo_cases()
for case in cases.values():
    cloud.load_case(demo_snapshot(case), {d.id: CaseResolver(cloud.store, {}).document_bytes(demo_snapshot(case), d.id) for d in case.documents})
    assert len(cloud.query_transactions(demo_snapshot(case)).transactions) == len(case.transactions)
    for doc in case.documents:
        result = cloud.extract(demo_snapshot(case), doc, CaseResolver(cloud.store, {}).document_bytes(demo_snapshot(case), doc.id))
        print(json.dumps({"document": doc.id, "fields": result["fields"]}))
config = {
    "project": PROJECT,
    "region": REGION,
    "bucket": BUCKET,
    "dataset": DATASET,
    "processor": processor.name,
    "model": "gemini-3.1-flash-lite",
}
Path("artifacts").mkdir(exist_ok=True)
Path("artifacts/cloud-config.json").write_text(json.dumps(config, indent=2))
print(json.dumps(config, indent=2))
