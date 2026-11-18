import unittest
import math
from decimal import Decimal, localcontext

import numpy

import compare_base_two_exponential as comparison


def scalar_signed(value, width):
    value &= (1 << width) - 1
    return value - (1 << width) if value & (1 << (width - 1)) else value


def scalar_shift(value, integer_exponent):
    shifted = value << integer_exponent if integer_exponent >= 0 else value >> -integer_exponent
    return scalar_signed(scalar_signed(shifted, 64) >> 16, 32)


def scalar_linear(encoded_input):
    integer_exponent, fractional_part = divmod(int(encoded_input), 1 << 24)
    if integer_exponent < -6:
        return 0
    shift_amount = integer_exponent % 64 if integer_exponent >= 0 else integer_exponent
    return scalar_shift((1 << 24) + fractional_part, shift_amount)


def scalar_cubic(encoded_input):
    integer_exponent, fractional_part = divmod(int(encoded_input), 1 << 24)
    if integer_exponent < -6 or integer_exponent >= 64:
        return 0
    square = fractional_part * fractional_part // (1 << 24)
    correction = (1 << 24) + (square - fractional_part) // 4
    return scalar_signed(scalar_linear(encoded_input) * correction // (1 << 24), 32)


class ExponentialComparisonTests(unittest.TestCase):
    def test_q24_fractional_models_match_scalar_integer_arithmetic(self):
        encoded_inputs = numpy.array([0, 1, 255, 256, (1 << 23), (1 << 24) - 1], dtype=numpy.int64)
        numpy.testing.assert_array_equal(comparison.fractional_fixed_point("linear", encoded_inputs), (1 << 24) + encoded_inputs)
        expected_cubic = []
        for value in encoded_inputs:
            square = int(value) * int(value) // (1 << 24)
            correction = (1 << 24) + (square - int(value)) // 4
            expected_cubic.append(correction * ((1 << 24) + int(value)) // (1 << 24))
        numpy.testing.assert_array_equal(comparison.fractional_fixed_point("cubic", encoded_inputs), expected_cubic)
        self.assertEqual(int(comparison.fractional_fixed_point("linear", numpy.array([1]))[0]), (1 << 24) + 1)
        for size in (16, 1024, 65536):
            table = comparison.make_table(size)
            expected = [int(table[int(value) * size // (1 << 24)]) for value in encoded_inputs]
            numpy.testing.assert_array_equal(comparison.fractional_fixed_point(f"bram_{size}", encoded_inputs, table), expected)
        with localcontext() as context:
            context.prec = 80
            for family in ("maclaurin", "sollya"):
                for degree in range(5):
                    coefficients = comparison.SOLLYA_COEFFICIENTS[degree] if family == "sollya" else [int(((Decimal(2).ln() ** power / Decimal(math.factorial(power))) * (1 << 24)).to_integral_value()) for power in range(degree + 1)]
                    expected = []
                    for value in encoded_inputs:
                        result = coefficients[-1]
                        for coefficient in reversed(coefficients[:-1]):
                            result = result * int(value) // (1 << 24) + coefficient
                        expected.append(result)
                    numpy.testing.assert_array_equal(comparison.fractional_fixed_point(f"{family}_{degree}", encoded_inputs), expected)

    def test_q24_range_preserves_overestimation_and_rejects_overflow(self):
        values = numpy.array([(2 << 24) + 1, -(1 << 24)], dtype=numpy.int64)
        numpy.testing.assert_array_equal(comparison.checked_signed_32(values), values)
        for value in (-(1 << 31) - 1, 1 << 31):
            with self.assertRaises(OverflowError):
                comparison.checked_signed_32(numpy.array([value], dtype=numpy.int64))
        for value in (-1, 1 << 24):
            with self.assertRaises(ValueError):
                comparison.fractional_fixed_point("linear", numpy.array([value], dtype=numpy.int64))

    def test_sollya_coefficients_match_supplied_exact_decimals(self):
        decimal_coefficients = {
            0: ("1.5",),
            1: ("0.956964313983917236328125", "1"),
            2: ("1.002476036548614501953125", "0.651046812534332275390625", "0.344001114368438720703125"),
            3: ("0.9998929500579833984375", "0.696457445621490478515625", "0.224338352680206298828125", "0.07920420169830322265625"),
            4: ("1.00000369548797607421875", "0.6929662227630615234375", "0.24163818359375", "0.051690578460693359375", "0.01369762420654296875"),
        }
        with localcontext() as context:
            context.prec = 80
            for degree, values in decimal_coefficients.items():
                for value, integer in zip(values, comparison.SOLLYA_COEFFICIENTS[degree]):
                    self.assertEqual(Decimal(value) * comparison.INPUT_SCALE, integer)
                    self.assertTrue(-(1 << 31) <= integer < (1 << 31))

    def test_q8_polynomials_match_scalar_integer_evaluation(self):
        generator = numpy.random.default_rng(8128)
        encoded_inputs = numpy.unique(numpy.concatenate(([0, 1, (1 << 24) - 1], generator.integers(0, 1 << 24, 1000))))
        for degree, coefficients in comparison.SOLLYA_COEFFICIENTS.items():
            expected = []
            for value in encoded_inputs:
                result = coefficients[-1]
                for coefficient in reversed(coefficients[:-1]):
                    result = scalar_signed((result * int(value) // (1 << 24)) + coefficient, 32)
                expected.append(result >> 16)
            numpy.testing.assert_array_equal(comparison.polynomial_fixed_point(f"sollya_{degree}", encoded_inputs), expected)
        inputs = encoded_inputs / comparison.INPUT_SCALE
        numpy.testing.assert_array_equal(comparison.polynomial_fixed_point("linear", encoded_inputs), comparison.linear_hardware(encoded_inputs))
        numpy.testing.assert_array_equal(comparison.polynomial_fixed_point("cubic", encoded_inputs), comparison.cubic_hardware(encoded_inputs))
        for family in ("maclaurin", "sollya"):
            for degree in range(5):
                output_integers = comparison.polynomial_fixed_point(f"{family}_{degree}", encoded_inputs)
                self.assertTrue(numpy.issubdtype(output_integers.dtype, numpy.integer))
                self.assertTrue(numpy.all((output_integers >= 0) & (output_integers <= 512)))
        predictions = comparison.polynomial_fixed_point("sollya_3", encoded_inputs) / comparison.OUTPUT_SCALE
        expected = comparison.accuracy_statistics("sollya_3", "hardware_fractional", "uniform", inputs, numpy.exp2(inputs), predictions, True, comparison.OUTPUT_SCALE)
        actual, unused_profile = comparison.batched_accuracy_statistics("sollya_3", "hardware_fractional", "uniform", encoded_inputs, lambda values: comparison.polynomial_fixed_point("sollya_3", values), 127)
        for key, value in expected.items():
            if isinstance(value, (float, int)):
                self.assertAlmostEqual(actual[key], value, places=9, msg=key)
            else:
                self.assertEqual(actual[key], value)

    def test_maclaurin_polynomials_against_high_precision_coefficients(self):
        inputs = numpy.array([0.0, 0.125, 0.5, 0.875, 1 - 1 / comparison.INPUT_SCALE])
        with localcontext() as context:
            context.prec = 60
            logarithm = Decimal(2).ln()
            for degree in range(5):
                expected = []
                for value in inputs:
                    argument = Decimal.from_float(float(value)) * logarithm
                    term = Decimal(1)
                    result = Decimal(1)
                    for power in range(1, degree + 1):
                        term = term * argument / power
                        result += term
                    expected.append(float(result))
                numpy.testing.assert_allclose(comparison.maclaurin_approximation(inputs, degree), expected, rtol=2e-16, atol=4e-16)
        numpy.testing.assert_array_equal(comparison.maclaurin_approximation(inputs, 0), numpy.ones_like(inputs))
        models = comparison.mathematical_models(inputs, {})
        numpy.testing.assert_array_equal(models["linear"], 1 + inputs)
        numpy.testing.assert_array_equal(models["cubic"], (1 + inputs) * (1 + (inputs**2 - inputs) / 4))

    def test_explicit_step_sizes(self):
        self.assertEqual(comparison.parse_step_size("8"), 8)
        self.assertEqual(comparison.parse_step_size("0b1000"), 8)
        for step_size in (3, 8, 128):
            sample_count = (comparison.INPUT_SCALE - 1) // step_size + 1
            inputs, unused_boundaries = comparison.input_vectors(sample_count, 64, step_size)
            self.assertEqual(len(inputs), sample_count)
            self.assertEqual(int(inputs[0]), 0)
            self.assertLess(int(inputs[-1]), comparison.INPUT_SCALE)
            self.assertTrue(numpy.all(numpy.diff(inputs) == step_size))

    def test_vectorised_models_against_scalar_integer_arithmetic(self):
        random_generator = numpy.random.default_rng(271828)
        random_inputs = random_generator.integers(-(1 << 31), 1 << 31, size=5000, dtype=numpy.int64)
        boundaries = numpy.array([integer * (1 << 24) + offset for integer in range(-127, 128) for offset in (-1, 0, 1)], dtype=numpy.int64)
        encoded_inputs = numpy.concatenate((random_inputs, boundaries, [-(1 << 31), (1 << 31) - 1]))
        numpy.testing.assert_array_equal(comparison.linear_hardware(encoded_inputs), [scalar_linear(value) for value in encoded_inputs])
        numpy.testing.assert_array_equal(comparison.cubic_hardware(encoded_inputs), [scalar_cubic(value) for value in encoded_inputs])
        for size in (16, 1024, 65536):
            table = comparison.make_table(size)
            expected = [scalar_shift(int(table[(int(value) % (1 << 24)) * size // (1 << 24)]), int(value) // (1 << 24)) for value in encoded_inputs]
            numpy.testing.assert_array_equal(comparison.bram_hardware(encoded_inputs, table), expected)

    def test_existing_table_matches_high_precision_generation(self):
        table = comparison.make_table(1024)
        with localcontext() as context:
            context.prec = 60
            expected = [int((Decimal(2) ** (Decimal(address) / 1024) * (1 << 24)).to_integral_value()) for address in range(1024)]
        numpy.testing.assert_array_equal(table, expected)

    def test_generated_table_values_against_high_precision(self):
        with localcontext() as context:
            context.prec = 60
            for size in comparison.DEFAULT_BRAM_SIZES:
                table = comparison.make_table(size)
                for address in sorted(set((0, 1, size // 3, size // 2, size - 2, size - 1))):
                    expected = int((Decimal(2) ** (Decimal(address) / size) * (1 << 24)).to_integral_value())
                    self.assertEqual(int(table[address]), expected)

    def test_known_outputs_and_cutoffs(self):
        encoded_inputs = numpy.array([-7, -6, -1, 0, 1, 2, 22, 23, 64]) * (1 << 24)
        numpy.testing.assert_array_equal(comparison.linear_hardware(encoded_inputs), [0, 4, 128, 256, 512, 1024, 1 << 30, -(1 << 31), 256])
        numpy.testing.assert_array_equal(comparison.cubic_hardware(encoded_inputs), [0, 4, 128, 256, 512, 1024, 1 << 30, -(1 << 31), 0])
        table = comparison.make_table(1024)
        self.assertEqual(int(comparison.bram_hardware(numpy.array([-7 * (1 << 24)]), table)[0]), 2)
        self.assertEqual(int(comparison.cubic_hardware(numpy.array([(1 << 23)]))[0]), 360)

    def test_all_table_boundaries_have_adjacent_inputs(self):
        uniform_inputs, directed_inputs = comparison.input_vectors(200, 1024)
        for boundary in numpy.arange(1, 1024) * ((1 << 24) // 1024):
            self.assertTrue(all(value in directed_inputs for value in (boundary - 1, boundary, boundary + 1)))
        self.assertTrue(numpy.all(numpy.diff(uniform_inputs) > 0))

    def test_comparison_inputs_only_vary_the_fractional_bits(self):
        for sample_count in (2, 200, 262144):
            uniform_inputs, directed_inputs = comparison.input_vectors(sample_count, 65536)
            self.assertEqual(len(uniform_inputs), sample_count)
            self.assertEqual(int(uniform_inputs[0]), 0)
            self.assertEqual(int(directed_inputs[0]), 0)
            self.assertEqual(int(directed_inputs[-1]), (1 << 24) - 1)
            self.assertIn(1, directed_inputs)
            self.assertTrue(numpy.all(numpy.diff(uniform_inputs) > 0))
            for inputs in (uniform_inputs, directed_inputs):
                self.assertTrue(numpy.all(inputs >= 0))
                self.assertTrue(numpy.all(inputs < (1 << 24)))
                self.assertTrue(numpy.all((inputs >> 24) == 0))

    def test_batched_statistics_match_direct_statistics(self):
        encoded_inputs, unused_boundaries = comparison.input_vectors(4099, 64)
        inputs = encoded_inputs / comparison.INPUT_SCALE
        references = numpy.exp2(inputs)
        table = comparison.make_table(64)
        cases = (("linear", "mathematical_fractional", lambda values: 1 + values / comparison.INPUT_SCALE), ("cubic", "hardware_fractional", comparison.cubic_hardware), ("bram_64", "hardware_fractional", lambda values: comparison.bram_hardware(values, table)))
        for name, domain, function in cases:
            predictions = function(encoded_inputs)
            if domain == "hardware_fractional":
                predictions = predictions / comparison.OUTPUT_SCALE
            expected = comparison.accuracy_statistics(name, domain, "uniform", inputs, references, predictions, domain == "hardware_fractional")
            actual, profile = comparison.batched_accuracy_statistics(name, domain, "uniform", encoded_inputs, function, 127, collect_profile=True)
            for key, value in expected.items():
                if isinstance(value, (float, int)):
                    self.assertAlmostEqual(actual[key], value, places=10, msg=key)
                else:
                    self.assertEqual(actual[key], value)
            errors = 100 * (predictions - references) / references
            bins = numpy.array_split(numpy.arange(len(inputs)), 512)
            numpy.testing.assert_allclose(profile["means"], [numpy.mean(errors[positions]) for positions in bins], atol=1e-12)
            numpy.testing.assert_allclose(profile["minima"], [numpy.min(errors[positions]) for positions in bins], atol=1e-12)
            numpy.testing.assert_allclose(profile["maxima"], [numpy.max(errors[positions]) for positions in bins], atol=1e-12)
            numpy.testing.assert_allclose(profile["absolute"]["means"], [numpy.mean(numpy.abs(errors[positions])) for positions in bins], atol=1e-12)
            numpy.testing.assert_allclose(profile["absolute"]["minima"], [numpy.min(numpy.abs(errors[positions])) for positions in bins], atol=1e-12)
            numpy.testing.assert_allclose(profile["absolute"]["maxima"], [numpy.max(numpy.abs(errors[positions])) for positions in bins], atol=1e-12)
            self.assertEqual(int(numpy.sum(profile["counts"])), len(inputs))


if __name__ == "__main__":
    unittest.main()
