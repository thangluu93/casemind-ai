"""Read-only project budget/usage verification; never print credentials or session IDs."""

import json
import urllib.request
from pathlib import Path

from google.auth.transport.requests import Request

from casemind.cloud import Cloud, credentials

cloud = Cloud()
usage, _ = cloud.store.get("usage/prototype-v1")
usage = usage or {"runs": {}, "pages": []}
counts = {
    "reserved_runs": len(usage["runs"]),
    "attempted_pages": len(usage["pages"]),
    "remaining_runs": cloud.ledger.max_runs - len(usage["runs"]),
}
creds = credentials()
creds.refresh(Request())
request = urllib.request.Request(
    "https://billingbudgets.googleapis.com/v1/billingAccounts/0129DA-6F9D06-6B750E/budgets",
    headers={"Authorization": "Bearer " + creds.token, "x-goog-user-project": "casemind-ai"},
)
with urllib.request.urlopen(request, timeout=20) as response:
    budgets = json.load(response)["budgets"]
safe = [
    {k: v.get(k) for k in ("displayName", "budgetFilter", "amount", "thresholdRules")}
    for v in budgets
    if "projects/251896792352" in v.get("budgetFilter", {}).get("projects", [])
]
result = {"usage": counts, "budgets": safe}
Path("artifacts").mkdir(exist_ok=True)
Path("artifacts/budget-verification.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
