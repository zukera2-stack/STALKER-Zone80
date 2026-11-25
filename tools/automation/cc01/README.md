# Zone80 Worker CC-01 — Linux synthetic prototype

Run `python -m unittest -v test_worker.py` with Python 3.13 (stdlib only). The tests create isolated temporary `zone80-synthetic-*` directories and launch the fixed synthetic child, not GIS software.

To make a demo manifest, use the **test** helper only: `python -c 'import json; from test_worker import manifest; print(json.dumps(manifest(),indent=2))' > demo.json`. The helper expires after ten minutes and pins the actual Python/worker file hashes. `reviewed_code_sha` identifies the source baseline, not an independently attested build. Local approval is a descriptive label, not an authentication mechanism. No native kinds are accepted. The older disabled MAP-003 queue template is intentionally incompatible with this narrower prototype.

Run `python worker.py init ./zone80-synthetic-demo` once, then `python worker.py run ./zone80-synthetic-demo --manifest demo.json` twice. The second run skips validated outputs. State JSON, logs and unique attempt directories stay within this explicit new sandbox. Create `stop.request` inside the sandbox to stop **between jobs**. Do not use it for live GIS or real asset folders.

Limitations: Linux only; Windows fails closed. Fixed child does not spawn descendants. Uses Linux flock, /proc/meminfo host available RAM, disk free, RLIMIT_AS (virtual address cap, not RSS/tree memory), wall timeout. No hard cgroup/resource tree claims. Stop during active job, real crash/recovery and descendants remain CC-02. Interrupted state is conservatively blocked until reviewed; no automatic retry of uncertain running processes. Trusted local sandbox, not a security boundary against adversarial filesystem races or tampered state. No scheduler, native tools, network, new real elevations or P: access.
