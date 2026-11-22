# Repository workflow

main is the stable reviewed foundation. Work in feat/*, fix/* or audit/* branches, make pull requests and keep verifiable commits. No force push, no unreviewed upstream GRM vendoring and no automatic merge for high-impact generation changes. Never commit addon binaries, large GIS data, credentials, cache or game builds.

Review checks: Python standard-library validation, source/asset allowlist, traceable configuration, no claims of in-game performance without evidence. Keep overrides small and reviewed; raw input remains local and immutable.

A local Cursor clone of the project must stay separate from an upstream ArmaRealMap clone. If experimentation needs upstream changes, preserve the original commit hash and do it in a dedicated patch branch; check the upstream license before publishing code.
