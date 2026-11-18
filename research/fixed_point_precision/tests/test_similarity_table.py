import sys
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import make_similarity_table as similarity
from signal_type_sweep import make_configurations


class SimilarityTableTests(unittest.TestCase):
    def test_separate_sweeps_exclude_previous_combined_option(self):
        integers=dict(state=9,constant=9,timestep=9,matrix=10,current=18,triangle=11)
        with tempfile.TemporaryDirectory() as temporary:
            output=Path(temporary)
            (output/'tables').mkdir()
            parent=dict(fingerprint='parent',currents=[80],configurations=[dict(name='existing',width=32,formats={})],budgets=dict(group_integer_bits=integers))
            (output/'manifest.json').write_text(json.dumps(parent))
            for folder,configurations in [('signal_type_sweep',[dict(signal_type=name) for name in ('baseline','shared','matrix','current','triangle')]),('individual_signal_type_sweep',make_configurations(integers))]:
                destination=output/folder
                destination.mkdir()
                configurations=[dict(name=f'candidate_{index}',formats={},width=32,**row) if 'name' not in row else row for index,row in enumerate(configurations)]
                (destination/'manifest.json').write_text(json.dumps(dict(parent_fingerprint='parent',fingerprint=folder,configurations=configurations)))
            similarity.generate(output)
            page=(output/'comparison_table.html').read_text(encoding='utf-8')
            payload=json.loads(page.split('const data=',1)[1].split(';\n',1)[0])
            self.assertEqual(set(payload['sweeps']),{'all','matrix','current','triangle','state','constant','timestep'})
            for group in ('state','constant','timestep'):
                self.assertEqual(payload['sweeps'][group]['widths'],list(range(32,8,-1)))

    def test_identical_signals_have_unit_correlation_and_zero_shift(self):
        reference=np.random.default_rng(4).normal(size=400)
        lags,scores=similarity.normalised_correlation(reference,reference,.1)
        score,lag=similarity.best_alignment(lags,scores)
        self.assertAlmostEqual(score,1)
        self.assertEqual(lag,0)

    def test_positive_shift_delays_an_early_candidate(self):
        reference=np.random.default_rng(5).normal(size=400)
        candidate=np.concatenate((reference[6:],np.zeros(6)))
        lags,scores=similarity.normalised_correlation(reference,candidate,.1)
        score,lag=similarity.best_alignment(lags,scores)
        self.assertAlmostEqual(score,1)
        self.assertAlmostEqual(lag,.6)

    def test_correlation_does_not_measure_amplitude_or_offset_agreement(self):
        reference=np.random.default_rng(6).normal(size=400)
        lags,scores=similarity.normalised_correlation(reference,reference*3+8,.1)
        score,lag=similarity.best_alignment(lags,scores)
        self.assertAlmostEqual(score,1)
        self.assertEqual(lag,0)

    def test_constant_signals_have_undefined_correlation(self):
        lags,scores=similarity.normalised_correlation(np.ones(400),np.ones(400),.1)
        converted=[None if not np.isfinite(value) else value for value in scores]
        self.assertEqual(similarity.best_alignment(lags,converted),(None,None))

    def test_local_peaks_can_exist_without_threshold_recrossing(self):
        voltage=np.full((100,3),2.)
        voltage[20,:]=5
        voltage[60,:]=5
        voltage[80,:]=2.2
        self.assertEqual(similarity.peak_counts(voltage,.1),[2,2,2])


if __name__=='__main__':
    unittest.main()
