# Stage gates: evidence rather than optimism

## Status vocabulary
- **PASS / GO:** measured criteria satisfied by reproducible evidence.
- **PARTIAL:** preparatory work exists but required tests or dependencies are missing.
- **FAIL / NO-GO:** criterion contradicted or safety bound breached.
- **NOT TESTED:** no evidence. This is never PASS.

## Stage 001 foundation acceptance
- Actual Windows build, CPU/cores, physical RAM, pagefile, storage and tool paths/versions recorded.
- Existing local .grma3m/.grma3a, GRM tag/SHA and addon roots located *if they exist*, without mutation.
- Unchanged upstream GRM builds; small memory profile recorded with stage-by-stage peak. If not possible, PARTIAL with reason.
- Asset inventory with hashes and UNKNOWN license handling; no copyrighted binaries committed.
- Candidate CRS roundtrip and distortion measured on boundary control points; no guessed map origin.
- Git diff clean of third-party assets, credentials and source datasets; manifest tooling deterministic.
- Reports include exact commands, SHA, logs, file inventory and unresolved issues.

## Promotion
The director audits the evidence; the owner authorizes Stage 002. Do not begin 10.24 km pilot or full world on Stage 001 authorization. For Stage 003 and Stage 007, a successful serializer is not a PASS: **the actual Arma map must load** with RPT/screenshots and package dependency checks.
