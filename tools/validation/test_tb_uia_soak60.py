"""Offline negative and regression checks for TB-UIA-02; no Windows APIs called."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('tb_soak', ROOT/'tools/tb_default/soak60.py')
soak = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(soak)


class SoakNegativeTests(unittest.TestCase):
    def setUp(self):
        soak.REPORTS.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix='soak-unit-', dir=soak.REPORTS)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.nodes = [dict(pid=3856, hwnd=100, id='1.2.3', name='Import terrain...',
                           type='ControlType.Button', enabled=True,
                           patterns=['InvokePatternIdentifiers.Pattern']),
                      dict(pid=3856, hwnd=100, id='1.2.4', name='Ready',
                           type='ControlType.Text', enabled=True, patterns=[])]

    def test_01_single_import_candidate(self):
        self.assertEqual(soak.validate_inventory(self.nodes, 3856, 100)['nodes'], 2)

    def test_02_zero_import_candidates(self):
        self.nodes.pop(0)
        with self.assertRaises(soak.Blocked): soak.validate_inventory(self.nodes, 3856)

    def test_03_ambiguous_import_candidates(self):
        self.nodes.append(dict(self.nodes[0]))
        with self.assertRaises(soak.Blocked): soak.validate_inventory(self.nodes, 3856)

    def test_04_disabled_import(self):
        self.nodes[0]['enabled'] = False
        with self.assertRaises(soak.Blocked): soak.validate_inventory(self.nodes, 3856)

    def test_05_missing_invoke(self):
        self.nodes[0]['patterns'] = []
        with self.assertRaises(soak.Blocked): soak.validate_inventory(self.nodes, 3856)

    def test_06_wrong_control_type(self):
        self.nodes[0]['type'] = 'ControlType.Text'
        with self.assertRaises(soak.Blocked): soak.validate_inventory(self.nodes, 3856)

    def test_07_wrong_owner_pid(self):
        self.nodes[0]['pid'] = 9999
        with self.assertRaises(soak.Blocked): soak.validate_inventory(self.nodes, 3856)

    def test_08_zero_hwnd(self):
        self.nodes[0]['hwnd'] = 0
        with self.assertRaises(soak.Blocked): soak.validate_inventory(self.nodes, 3856)

    def test_09_other_hwnd(self):
        self.nodes[0]['hwnd'] = 999
        with self.assertRaises(soak.Blocked): soak.validate_inventory(self.nodes, 3856, 100)

    def test_10_ready_absent(self):
        self.nodes.pop()
        with self.assertRaises(soak.Blocked): soak.validate_inventory(self.nodes, 3856)

    def test_11_error_dialog(self):
        self.nodes.append(dict(pid=3856, hwnd=100, id='1.2.5',name='TerrainBuilder Error',
                               type='ControlType.Window', enabled=True, patterns=[]))
        with self.assertRaises(soak.Blocked): soak.validate_inventory(self.nodes, 3856)

    def test_12_empty_tree(self):
        with self.assertRaises(soak.Blocked): soak.validate_inventory([], 3856)

    def test_13_bad_json(self):
        with self.assertRaises(soak.Blocked): soak.parse_inventory('{broken}')

    def test_14_noncanonical_runtime_id(self):
        sample=dict(self.nodes[0],id='malformed')
        with self.assertRaises(soak.Blocked): soak.parse_inventory(json.dumps(sample))

    def test_15_inventory_jsonl_roundtrip(self):
        text='\n'.join(json.dumps(n) for n in self.nodes)
        self.assertEqual(soak.parse_inventory(text), self.nodes)

    def test_16_status_missing_verified_pid(self):
        with self.assertRaises(soak.Blocked): soak.validate_status('editorWindow=True; dialogObserved=False; uia=True; responding=True',3856)

    def test_17_status_dialog_present(self):
        s='verified pid=3856; editorWindow=True; dialogObserved=True; uia=True; responding=True; name=Ready; Application initialization finished.'
        with self.assertRaises(soak.Blocked): soak.validate_status(s,3856)

    def test_18_status_ready_missing(self):
        s='verified pid=3856; editorWindow=True; dialogObserved=False; uia=True; responding=True'
        with self.assertRaises(soak.Blocked): soak.validate_status(s,3856)

    def test_19_status_success(self):
        s='verified pid=3856;\neditorWindow=True; dialogObserved=False; uia=True; responding=True\nname=Ready\nApplication initialization finished.'
        self.assertIsNone(soak.validate_status(s,3856))

    def test_20_unsafe_output_path(self):
        with self.assertRaises(soak.Blocked): soak.under_reports(self.root/'../../outside')

    def test_21_unique_run_names(self):
        a=soak.unique_dir(self.root);b=soak.unique_dir(self.root)
        self.assertNotEqual(a,b)

    def fixture(self):
        p=self.root/'fixture'
        result=soak.make_fixture(p)
        self.assertEqual(result['columns'],64)
        return p

    def test_22_fixture_positive(self):
        self.fixture()

    def test_23_fixture_bad_header(self):
        p=self.fixture();f=p/'W.asc'
        f.write_text(f.read_text().replace('cellsize 8','cellsize 4'))
        with self.assertRaises(soak.Blocked): soak.verify_fixture(p)

    def test_24_fixture_wrong_row_count(self):
        p=self.fixture();f=p/'merged.asc';a=f.read_text().splitlines()
        f.write_text('\n'.join(a[:-1])+'\n')
        with self.assertRaises(soak.Blocked): soak.verify_fixture(p)

    def test_25_fixture_wrong_seam(self):
        p=self.fixture();f=p/'E.asc';a=f.read_text().splitlines()
        row=a[6].split();row[0]='888';a[6]=' '.join(row)
        f.write_text('\n'.join(a)+'\n')
        with self.assertRaises(soak.Blocked): soak.verify_fixture(p)

    def test_26_fixture_wrong_nodata(self):
        p=self.fixture();f=p/'W.asc';a=f.read_text().splitlines()
        row=a[10].split();row[31]='0';a[10]=' '.join(row)
        f.write_text('\n'.join(a)+'\n')
        with self.assertRaises(soak.Blocked): soak.verify_fixture(p)

    def test_27_fixture_duplicate_source_id(self):
        p=self.fixture();f=p/'objects.json';obj=json.loads(f.read_text())
        obj[1]['id']=obj[0]['id'];f.write_text(json.dumps(obj))
        with self.assertRaises(soak.Blocked): soak.verify_fixture(p)

    def test_28_fixture_wrong_boundary_owner_coord(self):
        p=self.fixture();f=p/'objects.json';obj=json.loads(f.read_text())
        obj[2]['x']=255;f.write_text(json.dumps(obj))
        with self.assertRaises(soak.Blocked): soak.verify_fixture(p)

    def test_29_fixture_nonfinite_value(self):
        p=self.fixture();f=p/'merged.asc';a=f.read_text().splitlines()
        row=a[6].split();row[0]='nan';a[6]=' '.join(row)
        f.write_text('\n'.join(a)+'\n')
        with self.assertRaises(soak.Blocked): soak.verify_fixture(p)

    def test_30_no_windows_job_on_linux(self):
        if soak.os.name != 'nt':
            with self.assertRaises(soak.Blocked): soak.run_in_job(Path('fake.exe'),[],100)

    def test_31_invalid_cli_args_never_start_tb(self):
        self.assertEqual(soak.main(['soak','--out',str(self.root)]), 2)

    def test_32_schedule_120_12(self):
        plan=soak.sample_plan()
        self.assertEqual(len(plan),120)
        self.assertEqual(sum(flag for _,flag in plan),12)
        self.assertEqual(plan[9],(10,True))

    def test_33_schedule_misconfigured(self):
        with self.assertRaises(ValueError): soak.sample_plan(121,10)

    def test_34_ambiguous_main_hwnd(self):
        with self.assertRaises(soak.Blocked): soak.status_hwnd('HWND=0xAA; class=wxWindowClassNR;\nHWND=0xBB; class=wxWindowClassNR;')

    def test_35_status_memory_metrics(self):
        got=soak.status_metrics('WS=62963712; private=76972032; responding=True')
        self.assertEqual(got['privateBytes'],76972032)

    def test_36_status_memory_unresponsive(self):
        with self.assertRaises(soak.Blocked): soak.status_metrics('WS=10; private=10; responding=False')

    def test_37_canonical_import_never_invokes(self):
        source=(ROOT/'tools/tb_default/soak60.py').read_text()
        for symbol in ('InvokePattern.Invoke(', 'SendKeys', 'SendInput', 'WM_COMMAND', 'SwitchDesktop'):
            self.assertNotIn(symbol,source)


if __name__ == '__main__': unittest.main()
