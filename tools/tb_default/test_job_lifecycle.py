import unittest
from unittest.mock import Mock
from soak60 import Blocked, job_lifecycle, status_hwnd

class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.o = {name: Mock() for name in ('new_job','setup','create','identity',
            'assign','resume','wait','exit_code','close_job','terminate_suspended','close_child','emit')}
        self.o['wait'].return_value = 0
        self.o['exit_code'].return_value = 0

    def run_job(self):
        return job_lifecycle(timeout_ms=10, **self.o)

    def test_assignment_failure(self):
        self.o['assign'].side_effect = Blocked('access denied')
        with self.assertRaisesRegex(Blocked, 'access denied'):
            self.run_job()
        self.o['terminate_suspended'].assert_called_once()
        self.o['wait'].assert_called_once_with(3000)
        self.o['exit_code'].assert_called_once()
        self.o['resume'].assert_not_called()
        self.o['close_child'].assert_called_once()

    def test_assigned_failures(self):
        for fault in ('resume', 'timeout', 'wait', 'exit_code'):
            with self.subTest(fault=fault):
                self.setUp()
                if fault == 'timeout':
                    self.o['wait'].side_effect = [258, 0]
                elif fault in ('wait','exit_code'):
                    self.o[fault].side_effect = [Blocked(fault), 0]
                else:
                    self.o[fault].side_effect = Blocked(fault)
                with self.assertRaises(Blocked):
                    self.run_job()
                self.o['terminate_suspended'].assert_not_called()
                self.o['close_job'].assert_called_once()
                self.o['wait'].assert_called_with(3000)

    def test_setup_failures(self):
        for fault in ('new_job','setup','create'):
            with self.subTest(fault=fault):
                self.setUp()
                self.o[fault].side_effect = Blocked(fault)
                with self.assertRaises(Blocked):
                    self.run_job()
                self.o['close_child'].assert_not_called()
                self.o['close_job'].assert_called() if fault != 'new_job' else self.o['close_job'].assert_not_called()

    def test_failed_logging_cleans_owned_child(self):
        self.o['emit'].side_effect = [OSError('log'), None]
        with self.assertRaises(OSError):
            self.run_job()
        self.o['terminate_suspended'].assert_called_once()
        self.o['close_child'].assert_called_once()

    def test_unconfirmed_cleanup_blocks(self):
        self.o['assign'].side_effect = Blocked('assignment')
        self.o['wait'].return_value = 258
        with self.assertRaisesRegex(Blocked, 'UNCONFIRMED CLEANUP'):
            self.run_job()

    def test_repeated_calls_create_separate_jobs(self):
        self.o['new_job'].side_effect = [1, 2]
        self.assertEqual(self.run_job(), 0)
        self.assertEqual(self.run_job(), 0)
        self.assertEqual([c.args for c in self.o['close_job'].call_args_list], [(1,), (2,)])

class WindowTests(unittest.TestCase):
    def test_hidden_peer_does_not_shadow_minimized_editor(self):
        hidden = 'HWND=0x2E0C46; class=wxWindowClassNR; visible=False; enabled=True; minimized=False; title='
        editor = 'HWND=0x30F36; class=wxWindowClassNR; visible=True; enabled=True; minimized=True; title=Terrain Builder - unamedProject'
        self.assertEqual(status_hwnd(hidden + '\n' + editor), 0x30F36)
        with self.assertRaises(Blocked):
            status_hwnd(hidden)
        with self.assertRaises(Blocked):
            status_hwnd(editor + '\n' + editor.replace('30F36', '30F37'))

if __name__ == '__main__':
    unittest.main()
