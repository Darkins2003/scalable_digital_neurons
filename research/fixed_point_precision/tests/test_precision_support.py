import unittest
import hashlib
import json
import os
import tempfile
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import precision_support as study


class PrecisionSupportTests(unittest.TestCase):
    def test_json_write_retries_temporary_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / 'checkpoint.json'
            original_replace = Path.replace
            attempts = []

            def replace(source, target):
                attempts.append(source)
                if len(attempts) < 3:
                    raise PermissionError('Temporary Windows lock')
                return original_replace(source, target)

            with patch.object(Path, 'replace', replace), patch.object(study.time, 'sleep'):
                self.assertTrue(study.save_json(destination, {'saved': True}))
            self.assertEqual(json.loads(destination.read_text()), {'saved': True})
            self.assertEqual(len(attempts), 3)
            self.assertEqual(list(Path(directory).glob('*.tmp')), [])

    def test_locked_progress_does_not_abort_or_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / 'progress.json'
            study.save_json(destination, {'completed': 10})
            with patch.object(Path, 'replace', side_effect=PermissionError('Locked')), patch.object(study.time, 'sleep'):
                self.assertFalse(study.save_json(destination, {'completed': 11}, best_effort=True))
            self.assertEqual(json.loads(destination.read_text()), {'completed': 10})
            self.assertFalse(study.save_json(destination, {'completed': 12}, best_effort=True))
            self.assertEqual(list(Path(directory).glob('*.tmp')), [])
            study.DISABLED_PROGRESS_PATHS.discard(destination)

    def test_checkpoint_write_failure_is_not_hidden(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / 'completed.json'
            with patch.object(Path, 'replace', side_effect=PermissionError('Locked')), patch.object(study.time, 'sleep'):
                with self.assertRaises(PermissionError):
                    study.save_json(destination, {'completed': True})

    @unittest.skipUnless(os.name == 'nt', 'Windows sharing semantics')
    def test_real_windows_reader_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / 'progress.json'
            study.save_json(destination, {'completed': 10})
            with destination.open('r') as reader, patch.object(study.time, 'sleep'):
                self.assertFalse(study.save_json(destination, {'completed': 11}, best_effort=True))
                self.assertEqual(json.load(reader), {'completed': 10})
            study.DISABLED_PROGRESS_PATHS.discard(destination)
            self.assertTrue(study.save_json(destination, {'completed': 12}, best_effort=True))
            self.assertEqual(json.loads(destination.read_text()), {'completed': 12})



    def test_integer_range_boundaries(self):
        self.assertEqual(study.required_integer_bits(-8, 7.99), 4)
        self.assertEqual(study.required_integer_bits(-8, 8), 5)
        self.assertEqual(study.required_integer_bits(0, .001), 1)

    def test_metrics_preserve_timing_error(self):
        reference = np.zeros((10, 20))
        reference[:, 0] = np.arange(10)
        actual = reference.copy()
        reference[3:5, 2] = 3
        actual[4:6, 2] = 3
        states, spikes, matches = study.accuracy(actual, reference, 'test', 80, 'shifted')
        self.assertGreater(states[0]['rmse'], 0)
        self.assertEqual(spikes[0]['reference_spikes'], 1)
        self.assertEqual(spikes[0]['candidate_spikes'], 1)
        self.assertAlmostEqual(spikes[0]['mean_signed_error_ms'], .001)
        self.assertEqual(len(matches), 2)

    def test_input_mismatch_rejected(self):
        reference = np.zeros((2, 20))
        reference[:, 0] = np.arange(2)
        actual = reference.copy()
        actual[1, 1] = 80
        with self.assertRaises(ValueError):
            study.accuracy(actual, reference, 'test', 80, 'mismatch')


if __name__ == '__main__':
    unittest.main()
