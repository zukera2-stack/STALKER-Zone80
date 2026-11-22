# Synthetic tile pipeline

Run the offline checks with Python 3:

```text
python -m unittest discover -s tools/gis/tile_pipeline -v
```

Run the Windows integration from the checkout:

```powershell
pwsh -NoProfile -File tools/gis/tile_pipeline/run.ps1
```

Use Windows, PowerShell 7+, 64-bit Python 3.8+ and an existing licensed Global Mapper Pro 26.2 installation with the matching GDAL DLL. The runner checks the standard Program Files installation or an explicit `-MapperHome` argument. It never searches PATH for Global Mapper or downloads software. Missing dependencies print `SKIP / NOT TESTED` and exit 0. A runtime failure exits nonzero. Require the explicit PASS marker for integration acceptance. Leave Global Mapper closed before running the test. The runner leaves existing sessions alone.

The runner generates synthetic inputs and relative-path GMS scripts under a fresh ignored `reports/gis04-*` directory. It invokes W → E → W, records file sizes, timestamps and SHA-256 in `run-*.json`, records observed peak working sets by process and checks the E snapshot before and after the repeat. See `verification.json` for the raster and vector results. All coordinates and elevations are synthetic. EPSG:32636 is the test CRS. ASC outputs require the CRS to be supplied by the consumer. The projected GeoJSON is a local interchange fixture with an explicit CRS field.

The offline ownership tests simulate the same points arriving through overlapping buffers, including the internal seam and outer edges. Empty and collapsed fixture geometries are rejected before assignment. This utility assumes line and polygon parts have already been clipped by the exporter and supports the simple geometries in this fixture.

For Cursor acceptance run the integration command inside Cursor's integrated PowerShell terminal and record the terminal provenance separately.
