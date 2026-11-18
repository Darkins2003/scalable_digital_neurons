import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import make_sv_bit_report as report


class SignalMappingTests(unittest.TestCase):
    def test_state_names_include_correct_state_and_neuron_indices(self):
        module,signal,note=report.rtl_mapping('n2.vna','state')
        self.assertEqual((module,signal),('single_neuron','neuron_state_variables[3][2]'))
        self.assertEqual(report.rtl_mapping('n1.te','state')[1],'excitatory_triangular_state_reg[1]')

    def test_matrix_products_and_c_prefix_sums_are_distinguished(self):
        self.assertEqual(report.rtl_mapping('n0.matrix_product[2;7]','matrix_product_rescaled')[1],'products[2][7]')
        self.assertIn('no one-to-one',report.rtl_mapping('n0.matrix_partial_sum[2;7]','matrix_partial_sum')[2])

    def test_triangle_derivative_is_not_claimed_as_a_stored_rtl_derivative(self):
        self.assertIn('precomputed',report.rtl_mapping('n0.derivative_te','derivative')[2])
        self.assertEqual(report.rtl_mapping('n0.update_te','euler_update')[1],'mul_excitatory_dt_slope')


if __name__=='__main__':
    unittest.main()
