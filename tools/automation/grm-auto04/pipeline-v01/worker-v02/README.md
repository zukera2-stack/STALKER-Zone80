# AUTONOMY-WIN-02 — existing Windows Worker recovery candidate

**PASS: fixed native synthetic GRM recovery + handoff. Overall Stage001 PARTIAL.**
Base b5ba9a467d0c955dead523744d4a4e1a3345732a. This is a versioned candidate of pipeline_gate.py, not a second scheduler or a deployment replacing v01. Tested only in isolated D:/Zone80/PipelineV01_02; v01 accepted snapshot and current pointer unchanged.

## Implementation and reproduction

Copy the unchanged, pinned CC01/CC03/CC05Q helpers and original handoff_gate.py from the existing setup. Copy job_probe.py from the parent pipeline-v01 directory unchanged (only shared Win32 definitions are imported, not the probe main). Place the three tested v02 files beside them. Fresh dedicated exact root only: installed Python 3.15 x64 with -B, pipeline_gate.py init (123 snapshot files); never initialize an existing accepted sandbox. Normal invocation: resume_gate.py, which calls the existing GRM worker and unchanged handoff gate. The optional fixed fault modes below are test-only, never an owner production launch instruction.

Worker retains original deterministic input/host/code checks, staging, CC03 ownership, independent native baseline comparison and current pointer. New job_owner.py creates a uniquely named Global Job Object, KILL_ON_JOB_CLOSE, no breakaway, suspended child with JOB_LIST and explicit HANDLE_LIST for stdin/stdout/stderr, checks actual membership and active count before resume, persists ownership with PID and creation FILETIME, requires active count zero before successful publication. No arbitrary command input. On recovery: same identity, complete journal, previous worker and child PIDs non-live, job name absent (not access-denied), exact staged inputs, durable successful execution and independent report checked before publication. Live/reused PID is conservatively refused. Interrupted job without durable success may be retried only once; at most two attempt directories in this fixed fixture. Incomplete journal before child identity recorded deliberately blocks, no blind cleanup. No forced external PID termination. Source pins and previously accepted pointer are preserved; journal archived rather than deleted.

Actual ordered Windows test (separate fresh root, one finite suite):
1. pipeline_gate.py run during-child: exit73 after observed live native GRM child. No current.
2. pipeline_gate.py run before-publish: previous journal recovered, one bounded retry. Real native GRM exit0, full validation then abrupt exit73 before pointer. No current.
3. pipeline_gate.py run after-publish: previous fully checked output recovered and current atomically published; abrupt exit73 before journal archive.
4. pipeline_gate.py run: recovered same pointer, archived journal, verified SKIP. Suite exit0, two attempts, exactly one accepted output. 11/11 exported files identical to historic baseline, all 4562 unique object anchors and CC03 checks pass; report hash identical to v01.
5. resume_gate.py: verified SKIP GRM, fresh handoff PASS 15 files (13 equal, 2 path/manifest changes). Stop marker before launch refused exit2, removed only explicit test marker; normal resume exit0, both stages SKIP, current pointer byte-identical.
6. Rechecked v01 current, source tv4p/archive, common read-only cfg hashes unchanged. No candidate child remained observed.

| artifact | SHA256 |
|---|---|
| pipeline_gate.py | 3ae6a7cdde23fbb88386d68ed91e07cbad080dcdac013c458b994325843b0c96 |
| job_owner.py | 21252163536bf440ab5f84d7ede26459df1dca8f48a0f3cf235f3d175f40c0bf |
| resume_gate.py | 6173a4fd994fa918b2a22248265c298be015247077aa524f4050e8e3a5dc17ed |
| candidate current.json | d678687abb531f76da445d55b5c12ebe512b97df432ce394d429e5d2076a797f |
| candidate report.json | a31b357202888a71b6735e543d2c43a6401e0a142aa64bb28edfe95bcd19543e |
| candidate handoff ZIP | aee9a7f42d3adcfccaa0321cc01bde024aaa0c9916f951841dde63e7ccd1fdf0 |
| original current.json | 599cb1921dbafaa7e8d02b51838189e2031bb941e1666f2c30dd239e2dc48e68 |

All three source files Git blob verified exact. No raw snapshots published.

## Limits / next gate

Faults deliberately induced in the real Worker using os._exit, not a crash of GRM itself. No actual PID reuse, failure inside CreateProcessW, reboot, power-loss, native timeout/live stop or GRM descendant fault tested here; previous synthetic probe tested timeout/descendant containment only. The stop check tested here is before launch. The complete journal is required; job-name absence depends on OS job lifetime and noninherited handle/namespace assumptions; no general hostile-process or privilege isolation claim. No automatic repair of arbitrary changed code/inputs, no general DAG migration, partial handoff recovery or new Terrain Builder run. Two attempts is a fixed fixture budget, not a generalized retry policy. Original deployed v01 unchanged, no autostart/service/agent installed. Do not apply a v02 snapshot to v01 or promote the stage. Next: connect the validated native project open/save/reopen/export and a changed object layer to existing finite runner in a separate owned project, with per-stage durable checkpoints; then test handoff interruption, full native stop/restart and dependency invalidation. Stable TB 1.32 only. No P writes, real data, WRP/PBO, merge or promotion.
