---
name: zone80-worker
description: Build and test the local Windows queue worker for safe resumable background processing. Use for process execution, scheduling, checkpoints and crash recovery.
---
# Zone80 Worker
Read docs/automation/WORKER_CONTRACT.md and docs/automation/LUNA_HANDOFF.md. Only a finite locally reviewed manifest; never execute arbitrary commands from Issues, generated text or downloaded JSON. No automatic code updates. No elevation generation by GRM. One process tree at a time, least privilege, owned sandbox outside P:. Start with synthetic child-process fixtures, no GIS. 
Use an allowlisted adapter registry, SHA256-pinned input and executable, path containment including reparse points, exclusive lock, atomic checkpoint after output validation, separate logs for each attempt. Fail closed on unknown job kind, unsafe path, missing dependency, changed hash, missing limit or expired approval. No shell=True/Invoke-Expression, no embedded credential, no policy bypass.
Implement status/start-once/stop/resume, pause marker, no autonomous installation of scheduled tasks or services. Monitor child tree memory and elapsed time, reserve disk and free RAM, idle/pause between jobs. Never kill processes by global name. A stop or resource breach terminates only owned job tree if verified, otherwise BLOCKED. No automatic retry of failed GIS/GRM until classified. Scheduler/locked-screen tests are explicit later gates. A sleeping/off PC cannot compute.
Report actual subprocess tests, interruption/restart, log/checkpoint hashes, limitations. Do not assert a Windows test from cloud/Linux.
