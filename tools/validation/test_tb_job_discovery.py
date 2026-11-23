"""Include the standalone Job lifecycle suite in Foundation discovery."""
import importlib.util
import sys
import unittest
from pathlib import Path


def load_tests(loader, tests, pattern):
    directory = Path(__file__).resolve().parents[1] / 'tb_default'
    spec = importlib.util.spec_from_file_location('tb_job_lifecycle', directory / 'test_job_lifecycle.py')
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(directory))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    tests.addTests(loader.loadTestsFromModule(module))
    return tests

class RuntimeIdTests(unittest.TestCase):
    def test_signed_native_component(self):
        directory = Path(__file__).resolve().parents[1] / 'tb_default'
        spec = importlib.util.spec_from_file_location('tb_soak_runtime_id', directory / 'soak60.py')
        soak = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(soak)
        template = '{"pid":1,"hwnd":2,"id":"%s","patterns":[],"type":"ControlType.Custom"}'
        self.assertEqual(soak.parse_inventory(template % '42.136598.4.-1')[0]['id'], '42.136598.4.-1')
        for invalid in ('42..1', '42.--1', '42.x'):
            with self.subTest(invalid=invalid), self.assertRaises(soak.Blocked):
                soak.parse_inventory(template % invalid)
