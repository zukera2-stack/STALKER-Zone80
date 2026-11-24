# ADR-0001: One world, sectorized preparation

Status: proposed for experiment (2026-11-22).

Decision: target one 81,920 m Arma 3 world using 4096² × 20 m heightmap. Preprocess 64 distinct 10,240 m sectors and retain stable source IDs and deterministic boundary ownership, then investigate one streaming/disk-backed WRP assembly. **Do not binary-join separate WRP files.**

Rationale: the previously attempted GRM monolithic build exceeded reported 32 GB workstation RAM. The cause is not yet measured. Smaller computational units and an external spool are testable hypotheses, not proven fixes.

Alternatives: all-at-once GRM is the observed risk; 64 separate Arma maps is incompatible with the single-world goal; 8192² terrain grid is a high-risk unproven alternative.

Review trigger: two adjacent sectors and successful engine acceptance of the single WRP path. If false, revisit project scope rather than claim success.

## Evidence clarification (2026-11-24 audit; proposal still unproven)

The original rationale's phrase `exceeded reported 32 GB workstation RAM` is **not itself measured proof of OOM**. Historical GRM evidence mentions a Task disposal exception during `RawSatelliteImage` and a reported 8.3–8.7 GB memory figure whose metric was not fully identified. The project has **not** proven actual out-of-memory or a working streaming WRP assembler. The single-world target and 8×8 preprocessing remain design hypotheses pending measured engine acceptance; do not present them as completed code. See `docs/BASELINE_FROM_PRIOR_REPORTS.md` and [audit](../audits/PROJECT_AUDIT_20261124.md).
