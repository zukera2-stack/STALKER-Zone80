"""Offline-only checks of MAP-001 Global Mapper GMS templates.

These do NOT prove Global Mapper 26.2 runtime behavior or GIS validity.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "tools" / "gm26" / "scripts"
WRAPPER = ROOT / "tools" / "gm26" / "Invoke-GlobalMapper.ps1"
TEMPLATES = {
    "export_elevation_asc.gms": "EXPORT_ELEVATION FILENAME=\"%output%\" TYPE=ARCASCIIGRID",
    "export_elevation_geotiff.gms": "EXPORT_ELEVATION FILENAME=\"%output%\" TYPE=GEOTIFF",
    "export_roads_geojson.gms": "EXPORT_VECTOR FILENAME=\"%output%\" TYPE=GEOJSON SHAPE_TYPE=LINES",
    "export_buildings_geojson.gms": "EXPORT_VECTOR FILENAME=\"%output%\" TYPE=GEOJSON SHAPE_TYPE=AREAS",
}


class TestGm26Templates(unittest.TestCase):
    def test_expected_exports(self):
        for path, signature in TEMPLATES.items():
            with self.subTest(path=path):
                text = (SCRIPTS / path).read_text(encoding="utf-8")
                self.assertIn(signature, text)
                self.assertTrue(text.startswith("GLOBAL_MAPPER_SCRIPT VERSION=1.00"))
                self.assertIn('IMPORT FILENAME="%input%" TYPE=AUTO', text)
                self.assertIn('SET_LOG_FILE FILENAME="%logfile%"', text)
                self.assertIn("ZONE80_FINISHED", text)

    def test_scripts_do_not_launch_external_commands_or_insert_models(self):
        forbidden = {"RUN_COMMAND", "GENERATE_ELEV_GRID", "EDIT_VECTOR", "FORCE_EXIT",
                     "EXPORT_3D", "IMPORT_ONLINE", "IMPORT_WMS"}
        for path in TEMPLATES:
            lines = (SCRIPTS / path).read_text(encoding="utf-8").splitlines()
            commands = {line.split(" ", 1)[0] for line in lines if line.strip()}
            self.assertTrue(forbidden.isdisjoint(commands), path)

    def test_buildings_only_go_to_separate_geojson(self):
        template = (SCRIPTS / "export_buildings_geojson.gms").read_text(encoding="utf-8")
        self.assertIn("SHAPE_TYPE=AREAS", template)
        self.assertNotIn("EXPORT_ELEVATION", template)
        self.assertNotIn("SHAPE_TYPE=LINES", template)

    def test_wrapper_limits_scope_and_never_kills_gm(self):
        text = WRAPPER.read_text(encoding="utf-8")
        for expected in ("GlobalMapperExe", "26\\.2", "reports\\MAP-001",
                         "MANIFEST.json", "EXPORTED_NEEDS_GIS_QC",
                         "Get-FileHash", "WaitForExit", "DryRun"):
            self.assertIn(expected, text)
        for forbidden in ("Stop-Process", "TerminateProcess", "SendKeys",
                          "InvokePattern", "Set-ExecutionPolicy", "P:\\"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
