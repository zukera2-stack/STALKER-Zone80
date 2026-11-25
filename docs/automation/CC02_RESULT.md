# CC-02 — Linux synthetic fault injection and recovery
25.11.2026, Issue #42, Draft PR #47, base f585327a32849c7c83601a275c4d23a178b54cf0. Linux/Python 3.13.5 stdlib, new isolated synthetic roots only. No real geographic height generation or native GIS/GRM/TB, no P: writes, no scheduler or stage promotion. Source in tools/automation/cc02. CC-01 remains intact.

## Changes and decisions
CC-02 uses an exact hash-pinned CC-01 helper copy, new synthetic-only root marker and strict manifest fields (fixed fault modes, bounded delay, sampled group RSS guard). No custom command, shell or native kind. Linux fcntl flock shared via inherited FD with fixed child and controlled descendants: a crashed runner cannot release the lock while the owned child still has it. New explicit --recover only for matching trusted CC-02 interrupted protocol after lock acquisition. Fixed child/descendant alarms bound lifetime if runner is killed; no automatic relaunch of uncertain process. Unique attempt directories and old artifacts preserved. Active stop and timeout use SIGTERM then SIGKILL of child session group while leader PID is unreaped; no process-name kill; verify no live group members. Unexpected cleanup interruption stops queue. Completed validated PASS preserved when stop requested; output exact hash still required. No automatic CC-01 state migration.

## Actual execution
`python -m py_compile worker.py test_worker.py cc01_base.py` PASS. First exploratory suite 11 PASS. Final `python -m unittest -v test_worker.py` twice: 13 methods PASS each, 14.418s and 14.198s, nine invalid-manifest subcases rejected. Logs tests.log/tests_repeat.log included. Actual test subprocesses, not only mocks:
- nonzero exit, exit 0 missing/wrong artifact, timeout, disk block, sampled RSS limit, dependent block, invalidation and corrupted cached artifact rejection;
- active cancellation of fixed child and descendant, no remaining live group members, unrelated sentinel unaffected; leader exiting before descendant rejected;
- two concurrent runners: second blocked, no duplicate attempt;
- SIGKILL runner after A PASS while B child alive, new runner blocked by inherited lock; after child exits, no implicit recovery; explicit --recover starts new B attempt, keeps A exactly unchanged and old B attempt;
- checkpoint test subprocess exits 77 before or after os.replace through injected hook, readable previous/new JSON respectively (NOT power-loss/disk failure proof);
- CLI demo, two jobs PASS then both verified SKIP; both CLI exit 0, both child exit 0. A elapsed 0.146s / sampled group RSS peak 11141120 B; B 0.1476s / 10878976 B. Both payload hashes equal (same payload), artifact SHA256 b5eb232761afe68b4b2c536556a760480d6ea92e81cd7f05ccdf19cd5c143369. Actual aggregate in demo_result.json.

## File integrity
worker.py SHA256 72c0fb893cf202c954f36e9568e7dd2a9386183587d7bcdb71c772fa944f5824, Git blob 961ed20027aabc017b0a1788dd2c2ec082791683.
cc01_base.py SHA256 7ee6a93a45e61b3ee53776709e2df85effb2d002a1cc2fe232da32ad35a7b547, Git blob 388e7e36fe4a4d3b62bbfc31c9b1d2aa4c10c5be (identical to CC-01 worker).
test_worker.py SHA256 96f01f47fd0237c1910a16fc43430eb2ffbb739a72728d7a3f4d0c95e93d8dd1, Git blob 3da54765fc51196f93f586187485aa55f332ab2b.
tests.log SHA256 56f3b5d08260dc09ca748d86cccccb311037c49a690ff4b5c9da79b78fa28c9d.
tests_repeat.log SHA256 9c8b15b39913dc6e10ecb7e6ca43247058bb179dda09d4a023b8535999015906.
Owner ZIP Zone80_Worker_CC02.zip 13079 bytes, SHA256 81242c2461a62fd6ea0e042726d20cb1d39a07b532a7319f86145645b97c73f3, CRC PASS. Source transfer text delivered separately; all seven repo blobs matched measured Git blob IDs before publication.

## Limits and assessment
PASS bounded Linux synthetic CC-02, full WORKER_CONTRACT still PARTIAL. RSS is sampled sum of member RSS (may double count shared pages and miss transient peaks); RLIMIT_AS is per process, not whole tree. Host MemAvailable/free disk preflight not cgroup-aware. No verified arbitrary/escaping descendants, adversarial filesystem/security boundary, Windows Job Objects, real native tool/scheduler, locked desktop, detached survival, actual power loss or strict private/commit tree caps. Trusted synthetic state and descriptive approval only. Windows unsupported. Next CC-03 logical sector manifests, stable ownership, two-neighbor synthetic test. Reuse existing tools/validation/build_sector_manifests.py first, do not duplicate or generate real heights. Stage 001 PARTIAL, MAP-003 GM 629 NoData and TB BLOCKED unchanged.
