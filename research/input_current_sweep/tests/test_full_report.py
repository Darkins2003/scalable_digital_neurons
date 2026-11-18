import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import make_full_report as report


class FullReportTests(unittest.TestCase):
    def test_format_groups_preserve_binary_points_and_exclude_invalid_runs(self):
        values = [dict(kind='state', baseline_width=32, fractional_bits=24, integer_bits_observed=5, value='n0.vmem'), dict(kind='state', baseline_width=32, fractional_bits=16, integer_bits_observed=9, value='n0.te')]
        valid = dict(current_pa=1, numeric=dict(numerically_valid=True), values=values)
        invalid = dict(current_pa=2, numeric=dict(numerically_valid=False), values=[dict(values[0], integer_bits_observed=20)])
        rows, maxima = report.make_bit_data([valid, invalid])
        self.assertEqual(len(rows), 2)
        self.assertEqual(maxima['state', 32, 24]['required_integer_bits'], 5)
        self.assertEqual(maxima['state', 32, 24]['spare_integer_bits'], 3)
        self.assertEqual(maxima['state', 32, 16]['available_integer_bits'], 16)

    def test_primary_overflow_is_separate_from_same_step_cascades(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = root / 'runs/current_8000'
            run.mkdir(parents=True)
            fields = ['neuron','signal','group','width','fractional','overflow_count','first_overflow_step']
            rows = [dict(neuron=0,signal='exponential',group='current',width=32,fractional=8,overflow_count=1,first_overflow_step=60035),dict(neuron=0,signal='update',group='state',width=32,fractional=24,overflow_count=4,first_overflow_step=60035)]
            with (run / 'calculation_sites.csv').open('w', newline='') as stream:
                writer = csv.DictWriter(stream,fields)
                writer.writeheader()
                writer.writerows(rows)
            case = dict(current_pa=8000,_source_directory=root,directory_name='current_8000',numeric=dict(overflow_count=5,first_overflow_neuron=0,first_overflow_signal='exponential',first_overflow_group='current'))
            primary, flagged = report.collect_overflows([case], .001)
            self.assertEqual(len(primary),1)
            self.assertEqual(len(flagged),2)
            self.assertEqual(primary[0]['signal'],'exponential')
            self.assertAlmostEqual(primary[0]['first_flagged_time_ms'],60.036)
            self.assertFalse(flagged[1]['primary_trigger'])


if __name__ == '__main__':
    unittest.main()
