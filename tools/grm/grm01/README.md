# GRM-01 offline contract test

Python 3.10+ and its standard library suffice for the fixture and tests. From the repository root:

```powershell
python -m unittest discover -s tools/grm/grm01 -p "test_*.py" -v
python tools/grm/grm01/export.py grm01-example W
python tools/grm/grm01/export.py grm01-example E
python tools/grm/grm01/export.py grm01-example merge
```

Choose a fresh run name. The optional default action `all` runs the three operations together. Outputs are local under `reports/`. Absolute and relative object files retain their respective height modes. The sidecars carry synthetic IDs and simple clipped parts separately from Terrain Builder object rows. The assembled grid is a rectangular intermediate for offline comparison.

The optional .NET probe requires the pinned GRM framework-dependent build. It compares the CSV files directly to the upstream serializer and generates one test TML with a fictional model path. See the [audit](../../../docs/audits/GRM_01_MODULAR_EXPORT.md) for exact commands. The offline CI step requires neither .NET nor licensed apps.
