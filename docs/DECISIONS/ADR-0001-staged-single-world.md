# ADR-0001: One world, sectorized preparation

Status: proposed for experiment (2026-11-22).

Decision: target one 81,920 m Arma 3 world using 4096² × 20 m heightmap. Preprocess 64 distinct 10,240 m sectors and retain stable source IDs and deterministic boundary ownership, then investigate one streaming/disk-backed WRP assembly. **Do not binary-join separate WRP files.**

Rationale: the previously attempted GRM monolithic build exceeded reported 32 GB workstation RAM. The cause is not yet measured. Smaller computational units and an external spool are testable hypotheses, not proven fixes.

Alternatives: all-at-once GRM is the observed risk; 64 separate Arma maps is incompatible with the single-world goal; 8192² terrain grid is a high-risk unproven alternative.

Review trigger: two adjacent sectors and successful engine acceptance of the single WRP path. If false, revisit project scope rather than claim success.
