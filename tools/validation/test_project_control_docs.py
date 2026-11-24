"""Guard against stale agent entrypoints and unverifiable cross-stage PASS claims.

Offline, stdlib-only; does not read user files, query GitHub or execute GIS.
Update deliberately when the owner changes a project decision.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class ProjectControlDocumentsTests(unittest.TestCase):
    def test_all_authority_documents_exist(self):
        paths = [
            "docs/PROJECT_CONTROL.md",
            "docs/PROJECT_STATE.yaml",
            "docs/REQUIREMENTS_MATRIX.md",
            "docs/VERIFICATION_LEDGER.md",
            "docs/audits/PROJECT_AUDIT_20261124.md",
            "docs/DECISIONS/ADR-0002-owner-pivot-map-and-gm-only.md",
            "docs/map/MAP_003_GM26_TILES.md",
            "docs/HANDOFF.md",
            "docs/AGENT_REPORT_TEMPLATE.md",
        ]
        for name in paths:
            with self.subTest(name=name):
                self.assertTrue((ROOT / name).is_file())

    def test_one_active_issue_shared_across_entrypoints(self):
        state = read("docs/PROJECT_STATE.yaml")
        match = re.search(r'^  active_issue: "https://github.com/[^"]+/issues/(\d+)"$', state, re.M)
        self.assertIsNotNone(match)
        active = "Issue #" + match.group(1)
        for path in ["AGENT_START.md", "docs/PROJECT_CONTROL.md",
                     "docs/HANDOFF.md", "docs/REQUIREMENTS_MATRIX.md"]:
            with self.subTest(path=path):
                self.assertIn(active, read(path))

    def test_stage_is_partial_not_game_ready(self):
        state = read("docs/PROJECT_STATE.yaml")
        self.assertIn('stage: "001-foundation"', state)
        self.assertIn('status: "PARTIAL"', state)
        self.assertIn('game_engine_load_test: false', state)
        self.assertIn('terrain_builder_import_pass: false', state)
        self.assertIn('main_contains_map_work: false', state)

    def test_heightmap_method_is_owner_approved_local_gm(self):
        state = read("docs/PROJECT_STATE.yaml")
        self.assertIn("heights_acquired_and_exported_by:", state)
        self.assertIn("Local Global Mapper 26.2 Pro 64-bit only", state)
        self.assertIn("python_gdal_or_github_actions_new_heightmap_generation_authorized: false", state)
        self.assertIn("docs/map/MAP_003_GM26_TILES.md", read("docs/PROJECT_CONTROL.md"))
        self.assertIn("Copernicus_DSM_COG_10_N51_00_E030_00_DEM", read("docs/map/MAP_003_GM26_TILES.md"))

    def test_pilot_and_world_grids_never_conflated(self):
        state = read("docs/PROJECT_STATE.yaml")
        self.assertRegex(state, r"(?m)^  grid_cells: 4096$")
        self.assertRegex(state, r"(?m)^  cell_size_m: 20$")
        self.assertRegex(state, r"(?m)^  ncols: 64$")
        self.assertRegex(state, r"(?m)^  nrows: 64$")
        self.assertRegex(state, r"(?m)^  xllcorner_m: 294373\.084$")
        self.assertRegex(state, r"(?m)^  no_data_required_for_tb: 0$")
        self.assertIn("PILOT ONLY", state)

    def test_evidence_ledger_has_independent_gates(self):
        ledger = read("docs/VERIFICATION_LEDGER.md")
        for code in ["E-006", "E-007", "E-010", "E-013", "E-014", "E-015", "E-016"]:
            with self.subTest(code=code):
                self.assertIn(code, ledger)
        for label in ["T0 docs/CI", "T2 GIS local", "T4 TB sandbox", "T5 Arma runtime"]:
            self.assertIn(label, ledger)

    def test_agent_handoff_has_all_gates_and_real_log_requirement(self):
        template = read("docs/AGENT_REPORT_TEMPLATE.md")
        for t in ("T0 GitHub", "T1 Source", "T2 Actual local", "T3 Grid", "T4 Isolated TB", "T5 Game"):
            self.assertIn(t, template)
        self.assertIn("Фактическое доказательство", template)

    def test_no_literal_escaped_newlines_in_entrypoints(self):
        for path in ["AGENTS.md", "README.md"]:
            self.assertNotIn(r"\n\n", read(path), path)

    def test_history_not_silently_rewritten(self):
        # Old FAIL and later PASS must both remain visible.
        progress = read("docs/map/MAP_001_PROGRESS.md")
        self.assertIn("операция была отменена", progress.lower())
        self.assertIn("exit 0", progress)
        self.assertIn("253 NoData", progress)
        self.assertIn("Issue #42", progress)


if __name__ == "__main__":
    unittest.main()
