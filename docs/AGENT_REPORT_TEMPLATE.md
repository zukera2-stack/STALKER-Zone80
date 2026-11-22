# Stage 001 — Agent evidence handoff

**Engineer:**  
**Date/time + timezone:**  
**Git branch / HEAD SHA:**  
**Issue:**  
**Gate:** PASS / PARTIAL / FAIL / NOT TESTED  

## 1. What was actually observed

State each observation with source log, screenshot, command or original artifact checksum. List report-only facts separately from newly measured facts.

## 2. Exact commands and versions

```text
# actual commands executed, not a suggested command list
```

Tools (Global Mapper, GRM, Arma Tools, Python, .NET, OS) and exact versions:

## 3. Prior GRM incident: task exception vs RAM

- Studio version:
- Previous log match:
- Did the small v0.11.1 test run?:
- Relevant `RawSatelliteImage` output:
- Private Bytes peak:
- Working Set peak:
- Available RAM:
- Temporary disk usage:
- Error/exit code:

## 4. GIS and assets

- Candidate CRS and horizontal control-point residuals:
- Input DEM/source date/hash/license:
- Source addon directories **checked read-only**:
- Number of PBO/P3D files scanned:
- Unverified model dimensions/classes/licenses:
- Source ID and coordinate mismatches:

## 5. Files, diffs and safety

- Paths of created files (redact sensitive user paths in public GitHub):
- Files and SHA-256:
- Git changed files / commit:
- Did any protected original change? If yes, STOP and explain:

## 6. Acceptance checklist

| Criterion | Status | Evidence |
|---|---|---|
| Environment verification | NOT TESTED | |
| GRM baseline on small sample | NOT TESTED | |
| Original addon inventory | NOT TESTED | |
| Candidate CRS checked | NOT TESTED | |
| 64 synthetic sector manifests | NOT TESTED | |
| WRP/PBO + Arma loaded | NOT TESTED | Not required in Stage 001 |

## 7. Decision request

- Recommended GO / PARTIAL / NO-GO:
- Blockers:
- What action needs owner approval:
- Recommended narrow follow-up (no unauthorized new stage):
