import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from signal_type_sweep import SIGNAL_TYPES, make_configurations


class SignalTypeSweepTests(unittest.TestCase):
    def test_full_sweep_changes_only_selected_type_and_reaches_zero_fraction(self):
        integers = dict(state=9,constant=9,timestep=9,matrix=10,current=18,triangle=11)
        configurations = make_configurations(integers)
        self.assertEqual(len(configurations),127)
        self.assertEqual(len({tuple(row['formats'].values()) for row in configurations}),127)
        self.assertEqual(set(SIGNAL_TYPES),set(integers))
        for signal_type, groups in SIGNAL_TYPES.items():
            selected = [row for row in configurations if row['signal_type']==signal_type]
            self.assertEqual([row['width'] for row in selected],list(range(31,integers[groups[0]]-1,-1)))
            for row in selected:
                for group, (width,fractional) in row['formats'].items():
                    self.assertEqual(width,row['width'] if group in groups else 32)
                    self.assertEqual(width-fractional,integers[group])
            self.assertTrue(all(selected[-1]['formats'][group][1]==0 for group in groups))

    def test_separate_groups_keep_their_own_integer_allocation(self):
        integers = dict(state=8,constant=9,timestep=10,matrix=10,current=18,triangle=11)
        configurations = make_configurations(integers)
        for signal_type in ('state','constant','timestep'):
            selected = [row for row in configurations if row['signal_type']==signal_type]
            self.assertEqual(selected[-1]['width'],integers[signal_type])
            self.assertEqual(selected[-1]['formats'][signal_type][1],0)
            for row in selected:
                for group in integers:
                    if group!=signal_type:
                        self.assertEqual(row['formats'][group],(32,32-integers[group]))


if __name__=='__main__':
    unittest.main()
