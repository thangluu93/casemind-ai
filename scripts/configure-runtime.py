"""Grant prototype runtime access only to its dedicated dataset and bucket."""

import subprocess

from google.cloud import bigquery

from casemind.cloud import BUCKET, DATASET, PROJECT, Cloud

account = f"casemind-runtime@{PROJECT}.iam.gserviceaccount.com"
prefix = ["gcloud", "--configuration=casemind-ai"]
existing = subprocess.check_output(
    prefix
    + [
        "iam",
        "service-accounts",
        "list",
        "--project=" + PROJECT,
        "--filter=email:" + account,
        "--format=value(email)",
    ],
    text=True,
).strip()
if not existing:
    subprocess.run(
        prefix
        + [
            "iam",
            "service-accounts",
            "create",
            "casemind-runtime",
            "--project=" + PROJECT,
            "--display-name=CaseMind prototype runtime",
            "--quiet",
        ],
        check=True,
    )
for role in ("roles/aiplatform.user", "roles/documentai.apiUser", "roles/bigquery.jobUser"):
    subprocess.run(
        prefix
        + [
            "projects",
            "add-iam-policy-binding",
            PROJECT,
            "--member=serviceAccount:" + account,
            "--role=" + role,
            "--condition=None",
            "--quiet",
            "--format=none",
        ],
        check=True,
    )
cloud = Cloud()
dataset = cloud.bigquery.get_dataset(f"{PROJECT}.{DATASET}")
entry = bigquery.AccessEntry("READER", "userByEmail", account)
if entry not in dataset.access_entries:
    dataset.access_entries = list(dataset.access_entries) + [entry]
    cloud.bigquery.update_dataset(dataset, ["access_entries"])
bucket = cloud.storage.bucket(BUCKET)
policy = bucket.get_iam_policy(requested_policy_version=3)
member = "serviceAccount:" + account
role = "roles/storage.objectUser"
binding = next((b for b in policy.bindings if b["role"] == role), None)
if binding:
    binding["members"].add(member)
else:
    policy.bindings.append({"role": role, "members": {member}})
bucket.set_iam_policy(policy)
print("Prototype runtime IAM configured")
