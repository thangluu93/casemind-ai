import asyncio
import time

import pytest

from casemind.auth import Sessions
from casemind.case_resolver import demo_snapshot
from casemind.continuity import FollowUps, Operations, semantic_diff
from casemind.generator import demo_cases
from casemind.intake import IntakeBatch, IntakeRecord, commit_child, stage_stream, validate_batch
from casemind.models import digest
from casemind.store import Conflict, FileStore, UsageLedger
from casemind.source_catalog import SourceCatalog


@pytest.fixture
def store(tmp_path):
    return FileStore(tmp_path)


def test_google_csrf_audience_and_revocation(store):
    claims = {"sub": "allowed", "aud": "client", "iss": "accounts.google.com", "exp": time.time()+60}
    sessions = Sessions(store, "s"*32, "client", ["allowed"], lambda *args: claims)
    with pytest.raises(PermissionError):
        sessions.verify_google("jwt", "token", "different")
    assert sessions.verify_google("jwt", "token", "token") == "allowed"
    first = sessions.issue("allowed", "anonymous")
    second = sessions.issue("allowed", previous=first)
    with pytest.raises(PermissionError):
        sessions.resolve(first)
    assert sessions.resolve(second) == "allowed"
    sessions.revoke(second)
    with pytest.raises(PermissionError):
        Sessions(store, "s"*32, "client", ["allowed"]).resolve(second)
    claims["aud"] = "foreign"
    with pytest.raises(PermissionError):
        sessions.verify_google("jwt", "token", "token")


def test_operations_conflict_before_quota_and_no_restart_replay(store):
    ledger = UsageLedger(store)
    operations = Operations(store, ledger)
    operation = operations.reserve("owner", "question", "same-key", "snapshot", "report", [], {"q":"x"})
    usage, _ = store.get("usage/prototype-v1")
    with pytest.raises(Conflict):
        operations.reserve("owner", "question", "same-key", "snapshot", "report", [], {"q":"y"})
    assert store.get("usage/prototype-v1")[0] == usage
    context = operations.begin("owner", operation["id"])
    key = operations.prefix("owner", operation["id"]) + "/manifest"
    record, version = store.get(key)
    store.put(key, record | {"deadline": time.time()-1}, version)
    recovered, _ = operations.recover("owner")
    assert recovered[0]["error"] == "interrupted"
    with pytest.raises(Conflict):
        context.check()
    with pytest.raises(Conflict):
        operations.begin("owner", operation["id"])


def test_followup_command_replay_and_cas(store):
    followups = FollowUps(store)
    command = {"notes": "Review supplied synthetic data", "parent_run": "parent"}
    first = followups.command("owner", "followup", "key", 0, command)
    assert followups.command("owner", "followup", "key", 0, command) == first
    with pytest.raises(Conflict):
        followups.command("owner", "followup", "key", 0, {"notes":"changed"})
    with pytest.raises(Conflict):
        followups.command("owner", "followup", "new", 0, command)


def test_forward_references_quarantine_and_permutation(store):
    case = next(iter(demo_cases().values()))
    source = SourceCatalog(store).put(b"{}", "application/json").model_dump(mode="json")
    records = [IntakeRecord(group="accounts", record={"id":"new-account","entity_id":"new-entity"}, source_object=source, locator="row/2"),
               IntakeRecord(group="entities", record={"id":"new-entity","name":"Synthetic New","kind":"company"}, source_object=source, locator="row/1"),
               IntakeRecord(group="accounts", record={"id":"bad-account","entity_id":"missing"}, source_object=source, locator="row/3")]
    batch = IntakeBatch(classification="synthetic", records=records)
    child, accepted, quarantine = validate_batch(case, batch)
    assert "new-account" in child.sources and "bad-account" not in child.sources
    assert len(accepted) == 2 and len(quarantine) == 1
    reversed_child, _, _ = validate_batch(case, batch.model_copy(update={"records":list(reversed(records))}))
    assert digest(child) == digest(reversed_child)
    snapshot, quarantine = commit_child(store,"owner",demo_snapshot(case),batch)
    assert snapshot.manifest_version == 2 and len(quarantine) == 1
    assert semantic_diff(case,snapshot.case)["added"] == ["new-account","new-entity"]


def test_stream_caps_without_content_length(store):
    async def chunks():
        for _ in range(3):
            yield b"x" * (1024**2)
    with pytest.raises(ValueError, match="size limit"):
        asyncio.run(stage_stream(chunks(),store,"owner","followup","application/json"))
    assert not list(store.root.rglob("*.blob"))


def test_supersede_revision_is_required():
    case = next(iter(demo_cases().values()))
    entity = case.entities[0]
    item = IntakeRecord(group="entities",action="supersede",record=entity.model_dump(mode="json") | {"name":"Revised synthetic"}, source_object={},locator="row/1",target_revision="wrong")
    child, accepted, quarantine = validate_batch(case,IntakeBatch(classification="synthetic",records=[item]))
    assert not accepted and quarantine and child.sources[entity.id].name == entity.name


def test_claim_bootstrap_preserves_run_bytes_and_excludes_foreign(store):
    sessions = Sessions(store,"s"*32,"client",["owner"])
    store.put("runs/one",{"session":"anonymous","case_id":"case","status":"completed"})
    store.put("runs/two",{"session":"foreign","case_id":"case","status":"completed"})
    original = store.get("runs/one")
    sessions.issue("owner","anonymous")
    sessions.bootstrap("owner","anonymous",limit=100)
    assert store.get("runs/one") == original
    history = Operations(store,UsageLedger(store)).history("owner")
    assert [item["run_id"] for item in history["items"]] == ["one"]
    with pytest.raises(PermissionError):
        sessions.bootstrap("owner","foreign")


def test_crash_after_command_envelope_recovers_same_command(store):
    followups = FollowUps(store)
    command = {"notes":"Investigate supplied evidence"}
    canonical = digest({"command":command,"expected_version":0})
    store.put("follow-ups/"+digest("owner")+"/followup/commands/"+digest("key"),
              {"hash":canonical,"command":command,"expected_version":0})
    result = followups.command("owner","followup","key",0,command)
    assert result["version"] == 1
    assert followups.command("owner","followup","key",0,command) == result
    with pytest.raises(Conflict):
        followups.command("owner","followup","key",1,command)


def test_duplicate_stable_ids_quarantine_every_conflicting_record():
    case = next(iter(demo_cases().values()))
    items = [IntakeRecord(group="entities",record={"id":"duplicate","name":name,"kind":"company"},
                          source_object={},locator="record") for name in ("Synthetic A","Synthetic B")]
    child, accepted, quarantine = validate_batch(case,IntakeBatch(classification="synthetic",records=items))
    assert not accepted and len(quarantine) == 2 and "duplicate" not in child.sources


def test_staged_original_promotion_and_ttl_cleanup(store):
    from casemind.intake import promote_staged, sweep_staging
    async def chunks():
        yield b'{"classification":"synthetic","records":[]}'
    staged = asyncio.run(stage_stream(chunks(),store,"owner","followup","application/json"))
    ref = promote_staged(store,"owner","followup",staged)
    assert SourceCatalog(store).read(ref).startswith(b"{")
    second = asyncio.run(stage_stream(chunks(),store,"owner","followup","application/json"))
    assert sweep_staging(store,"owner",now=second["created"]+3601)["removed"] == 1


def test_stream_upload_key_replays_and_changed_bytes_conflict(store):
    async def stream(data):
        yield data
    async def stage(data):
        return await stage_stream(stream(data),store,"owner","followup","application/json",
                                  idempotency_key="upload-key",expected_version=1,filename="a.json")
    first = asyncio.run(stage(b"{}"))
    assert asyncio.run(stage(b"{}")) == first
    before = store.get("staged/"+digest("owner")+"/"+digest("followup"))[0]
    with pytest.raises(Conflict):
        asyncio.run(stage(b'{"different":true}'))
    assert store.get("staged/"+digest("owner")+"/"+digest("followup"))[0] == before


def test_followup_replay_checks_request_before_result_work(store):
    followups = FollowUps(store)
    request = {"batch":{"classification":"synthetic","records":[]}}
    assert followups.replay("owner","followup","key",0,request) is None
    applied = followups.command("owner","followup","key",0,{"status":"committed"})
    assert followups.replay("owner","followup","key",0,request) == applied
    with pytest.raises(Conflict):
        followups.replay("owner","followup","key",0,{"batch":"changed"})


def test_claim_scope_lookup_and_owner_indexed_history(store):
    from casemind.continuity import index_run, run_history
    sessions = Sessions(store,"s"*32,"client",["owner"])
    followups = FollowUps(store)
    followups.command("anonymous","task","key",0,{"run_id":"one"})
    store.put("runs/one",{"case_id":"case","session":"anonymous","status":"complete"})
    sessions.issue("owner","anonymous")
    scopes, _ = sessions.owner_scopes("owner")
    assert followups.find(scopes,"task")[0]["owner"] == "anonymous"
    assert "foreign" not in scopes
    index_run(store,"owner","one")
    assert run_history(store,"owner")["items"][0]["run_id"] == "one"


def test_prepare_serializes_commands_without_advancing_revision(store):
    followups = FollowUps(store)
    followups.command("owner","task","create",0,{"run_id":"parent","report_hash":"report","parent_snapshot":"snapshot"})
    first = followups.prepare("owner","task","commit",1,{"batch":"synthetic"})
    assert first["version"] == 1 and first["pending_command"]["key"] == "commit"
    assert followups.prepare("owner","task","commit",1,{"batch":"synthetic"})["version"] == 1
    with pytest.raises(Conflict):
        followups.prepare("owner","task","different",1,{"batch":"synthetic"})
    with pytest.raises(Conflict):
        followups.command("owner","task","commit",1,{"run_id":"child"})
    result = followups.command("owner","task","commit",1,{"linked_run_id":"child"})
    assert result["version"] == 2 and result["pending_command"] is None
    assert result["run_id"] == "parent" and result["linked_run_id"] == "child"
