---
title: Investigator workspace plan validation
date: 2026-10-10
status: reviewed
---

# Investigator workspace plan validation

## Result

The [plan](../plan.md) retains all ten feature groups and the user's three
confirmed choices. Six phases describe dependencies, file ownership, execution
steps, test gates, risks and rollback. All implementation checkboxes remain
pending; planning verification does not establish application readiness.

## Validation questions and confirmed answers

1. **Schedule:** “Kế hoạch nên đặt mục tiêu hoàn thành cả 10 nhóm trước ngày
   freeze 17/10, hay chia thành các đợt nhưng vẫn giữ đủ phạm vi?”
   Options: “Chia đợt, giữ đủ 10 nhóm” | “Cả 10 nhóm trước 17/10”.
   Answer: **“Cả 10 nhóm trước 17/10”**.
   Impact: all ten groups remain targeted before October 17; October 11–16
   integration checkpoints and a capacity shortfall are documented.
2. **Export:** “Báo cáo dễ đọc nên hỗ trợ định dạng nào ngay trong phạm vi
   triển khai?”
   Options: “HTML để in và PDF, giữ JSON” | “HTML để in và JSON”.
   Answer: **“HTML để in và PDF, giữ JSON”**.
   Impact: phase 5 includes all three formats, exact-value parity, safe escaping
   and preserved existing JSON behavior.
3. **Follow-up:** “Follow-up nên chạy lại các kiểm tra có sẵn và lưu ghi chú,
   hay cần cả thu thập dữ liệu mới?”
   Options: “Kiểm tra có sẵn và ghi chú” | “Thêm thu thập dữ liệu mới”.
   Answer: **“Thêm thu thập dữ liệu mới”**.
   Impact: phase 4 includes restricted CSV/PDF/structured intake, validation,
   quarantine, provenance, immutable child snapshots and linked analysis.

These answers supersede the corresponding recommended defaults in the earlier
[brainstorm report](../../reports/brainstorm-261010-2204-investigator-workspace-features.md).

## Source checks and corrections

- Analytics sorts/deduplicates evidence references. Path order must be emitted
  explicitly; reference order cannot establish traversal order.
- Activity evidence includes baseline transactions and identifies a target
  transaction separately. Only explicit attribution can drive flagged reasons.
- Existing reports/reviews are immutable and run sources are pinned. Proposed
  adapters must not rewrite old artifacts or hashes.
- Current session ownership is an opaque bearer cookie, not authenticated user
  identity. Restricted intake adds verified allowlisted identity while preserving
  existing synthetic investigation and review access.
- Current run reservations do not account for all proposed Q&A/follow-up usage.
  Phase 4 extends conservative operation accounting and retains compatibility.
- The evaluator currently constructs cloud clients even without `--live`.
  Phase 6 makes the default evaluation genuinely offline before using it as an
  offline gate. Existing browser investigation tests invoke billed providers.
- Existing report JSON and proposed canonical export JSON are distinct routes;
  adding exports cannot silently change the original report contract.
- This workspace has no Git checkout. Rollback uses pre-change backups instead
  of assuming a commit history exists.

## Whole-plan verification

- The dependency graph is acyclic: 1 precedes 2 and 4; 2 precedes 3; 2 and 4
  precede 5; 3 and 5 precede 6. Shared integration files have serialized ownership.
- Feature mapping: groups 1–4 use phases 1–2; groups 5–7 use phase 3;
  follow-up and history use phase 4; Q&A and exports use phase 5; phase 6 verifies
  the complete scope across all five scenarios.
- Phase effort ranges sum to **180–248 human builder-hours**. Documented team
  capacity for October 11–16 is approximately **48 hours**. The **132–200 hour**
  gap is a planning risk, not permission to reduce scope or change the deadline.
- `ak plan validate plans/261010-2210-investigator-workspace --json` passed.
- Runtime task tracking is represented by durable phase checkboxes; no external
  project tasks were created. No application tests or provider calls were run
  to claim feature completion during planning.

## Tool limitations

The automatic journal command failed with `project "casemind-ai" not found`:
AgentKit's project registry is empty. No registry change or journal was created.
The plan itself was scaffolded through the installed CLI and validated normally.

## Remaining prerequisites

- Capacity and availability for the full deadline target remain unverified.
- Hosted restricted intake needs an OAuth client, allowlist and signing-secret
  configuration; none was created in this planning turn.
- Live model/auth/browser evaluation and deployment remain unperformed. Reuse
  applicable explicit authorization when executing; this planning request does
  not itself initiate those actions.
