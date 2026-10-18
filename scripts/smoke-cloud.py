import asyncio
import json
import os
from pathlib import Path
from uuid import uuid4

from casemind.cloud import Cloud
from casemind.generator import demo_cases
from casemind.investigation import investigate

config = json.loads(Path("artifacts/cloud-config.json").read_text())
os.environ["CASEMIND_PROCESSOR"] = config["processor"]
cloud = Cloud()


async def main():
    reports = []
    for case in demo_cases().values():
        run_id = "smoke-" + uuid4().hex[:20]
        cloud.ledger.reserve_run("developer-smoke-" + case.id, run_id)

        async def emit(role, status, payload=None):
            print(role, status, flush=True)

        report = await investigate(case, run_id, cloud.store, cloud, emit)
        reports.append(report)
        print(
            json.dumps(
                {
                    "case": case.title,
                    "status": report["status"],
                    "gaps": report["gaps"],
                    "usage": report["usage"],
                }
            ),
            flush=True,
        )
    Path("artifacts/smoke-reports.json").write_text(json.dumps(reports, indent=2))


asyncio.run(main())
