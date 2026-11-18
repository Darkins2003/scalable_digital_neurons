import sys
import ast
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import run_fixed_integer_study as fixed


class FixedIntegerStudyTests(unittest.TestCase):
    def test_removed_source_provenance_uses_exact_recorded_hashes(self):
        compatibility=json.loads((fixed.DIRECTORY/'profile_source_compatibility.json').read_text())
        for relative,entry in compatibility['source_aliases'].items():
            self.assertTrue(fixed.study.profile_source_matches(relative,entry['previous_sha256']))
            self.assertFalse(fixed.study.profile_source_matches(relative,'0'*64))

    def test_shared_numerical_functions_are_unchanged(self):
        compatibility=json.loads((fixed.DIRECTORY/'profile_source_compatibility.json').read_text())
        functions={node.name:node for node in ast.parse(Path(fixed.study.__file__).read_text()).body if isinstance(node,ast.FunctionDef)}
        for name,expected in compatibility['shared_function_ast_sha256'].items():
            actual=hashlib.sha256(ast.dump(functions[name],include_attributes=False).encode()).hexdigest()
            self.assertEqual(actual,expected,name)

    def test_agreed_current_grid(self):
        self.assertEqual(len(fixed.DEFAULT_CURRENTS),57)
        self.assertEqual(len(set(fixed.DEFAULT_CURRENTS)),57)
        self.assertEqual(fixed.DEFAULT_CURRENTS[:21],tuple(range(0,101,5)))
        self.assertEqual(fixed.DEFAULT_CURRENTS[21:],tuple(range(125,1001,25)))
        self.assertIn(80,fixed.DEFAULT_CURRENTS)

    def test_every_width_and_zero_fractional_endpoint(self):
        integers=dict(state=9,matrix=10,current=18,triangle=11,constant=9,timestep=9)
        candidates=fixed.make_configurations(integers)
        self.assertEqual([row['width'] for row in candidates],list(range(32,17,-1)))
        self.assertEqual(len(candidates)*len(fixed.DEFAULT_CURRENTS),855)
        self.assertEqual(candidates[-1]['formats']['current'],(18,0))
        for candidate in candidates:
            for group,(width,fractional) in candidate['formats'].items():
                self.assertEqual(width-fractional,integers[group])
            self.assertEqual(candidate['formats']['state'],candidate['formats']['constant'])
            self.assertEqual(candidate['formats']['state'],candidate['formats']['timestep'])
        with self.assertRaises(ValueError):
            fixed.make_configurations(integers,[17])

    def test_exact_signed_endpoints(self):
        self.assertEqual(fixed.integer_bits(-32768*256,32768*256-1,8),16)
        self.assertEqual(fixed.integer_bits(0,32768*256,8),17)
        self.assertEqual(fixed.integer_bits(-32768*256-1,0,8),17)

    def test_display_preserves_last_sample_and_error_extrema(self):
        reference=np.zeros((4001,20))
        reference[:,0]=np.arange(4001)
        actual=reference.copy()
        actual[-1,2]=17
        actual[12,2]=-9
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'display.npz'
            fixed.save_display(path,actual,reference)
            with np.load(path) as display:
                self.assertEqual(display['candidate_maximum'][:,0].max(),17)
                self.assertEqual(display['candidate_minimum'][:,0].min(),-9)
                self.assertEqual(display['error_maximum'][:,0].max(),17)


if __name__=='__main__':
    unittest.main()
