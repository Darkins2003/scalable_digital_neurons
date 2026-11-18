import sys
import unittest
import json
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sweep_analysis as analysis


class CurrentSweepTests(unittest.TestCase):
    def test_current_grid_and_q8_resolution(self):
        self.assertEqual(len(analysis.current_grid('0', '300', '1')), 301)
        self.assertEqual(analysis.current_grid('-1', '1', '.5'), [-256, -128, 0, 128, 256])
        with self.assertRaises(ValueError):
            analysis.current_grid('0', '1', '.1')
        with self.assertRaises(ValueError):
            analysis.current_grid('0', '5', '2')

    def test_signed_integer_boundary_counts(self):
        self.assertEqual(analysis.integer_bits(-8 * 256, 8 * 256 - 1, 8), 4)
        self.assertEqual(analysis.integer_bits(-8 * 256, 8 * 256, 8), 5)
        self.assertEqual(analysis.integer_bits(-8 * 256 - 1, 0, 8), 5)
        self.assertEqual(analysis.integer_bits(-256, 0, 8), 1)
        self.assertEqual(analysis.integer_bits(0, 0, 24), 1)
        self.assertEqual(analysis.integer_bits(-(1 << 62), (1 << 62) - 1, 31), 32)

    def test_initial_to_first_sample_crossing_is_counted(self):
        raw = np.zeros((4, 20), dtype=np.int64)
        for column in (2, 6, 10):
            raw[:, column] = np.array([2, 0, 2, 0]) * (2 ** 24)
        profiles = [dict(value=f'n{neuron}.vmem', first_raw=0, fractional_bits=24, kind='state') for neuron in range(3)]
        metrics, crossings, display = analysis.analyse_voltage(raw, profiles, 80, .001, 0, 3, 1.4542)
        self.assertEqual([row['crossings_total'] for row in metrics], [2, 2, 2])
        self.assertEqual([row['crossings_during_pulse'] for row in metrics], [2, 2, 2])
        self.assertEqual(len(crossings), 6)
        self.assertLess(crossings[0]['crossing_time_ms'], .001)
        self.assertEqual(metrics[0]['minimum_vmem'], 0)
        self.assertEqual(float(display['maximum_voltage'].max()), 2)

    def test_invalid_current_does_not_expand_recommended_range(self):
        common = dict(value='n0.vmem', kind='state', phase='after_update', baseline_width=32, fractional_bits=8, minimum_time_ms=0, maximum_time_ms=1, minimum_at_initialisation=True, maximum_at_initialisation=False)
        valid = dict(common, current_pa=80, numerically_valid=True, minimum_raw=-256, maximum_raw=512, minimum=-1, maximum=2)
        invalid = dict(common, current_pa=300, numerically_valid=False, minimum_raw=-99999, maximum_raw=99999, minimum=-390, maximum=390)
        result = analysis.aggregate_profiles([valid, invalid], 1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['maximum'], 2)
        self.assertEqual(result[0]['integer_bits_observed'], 3)
        self.assertEqual(result[0]['integer_bits_with_headroom'], 4)

    def test_profiled_state_extrema_match_saved_full_baseline(self):
        study_directory = Path(__file__).resolve().parents[1]
        checkpoint = study_directory / 'results/runs/current_000/completed.json'
        references = [study_directory.parent / relative for relative in ('fixed_point_precision/results_fixed_integer/runs/reference32/current_0000/reference_trace.npz','fixed_point_precision/build/fixed_integer_smoke/runs/reference32/current_0000/reference_trace.npz')]
        reference = next((path for path in references if path.is_file()),references[0])
        if not checkpoint.is_file() or not reference.is_file():
            self.skipTest('Full baseline and current-zero profiling checkpoint are required')
        case = json.loads(checkpoint.read_text())
        with np.load(reference) as saved:
            raw = saved['raw'][:,2:20]
        lookup = {row['value']: row for row in case['values'] if row['kind'] == 'state'}
        for column, name in enumerate(analysis.STATE_NAMES):
            row = lookup[name]
            self.assertEqual(row['minimum_raw'], min(int(raw[:,column].min()),row['first_raw']))
            self.assertEqual(row['maximum_raw'], max(int(raw[:,column].max()),row['first_raw']))
            self.assertEqual(row['observations'], 190001)


if __name__ == '__main__':
    unittest.main()
