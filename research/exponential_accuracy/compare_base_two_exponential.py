import argparse
import csv
import copy
import json
import time
from decimal import Decimal, localcontext
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as pyplot
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator
import numpy


INPUT_SCALE = 1 << 24
OUTPUT_FRACTIONAL_BITS = 24
OUTPUT_SCALE = 1 << OUTPUT_FRACTIONAL_BITS
OUTPUT_STEP = 1 / OUTPUT_SCALE
DEFAULT_BRAM_SIZES = [1 << address_bits for address_bits in range(4, 17)]
DEFAULT_TABLE_PATH = Path(__file__).resolve().parents[2] / "ip/scalable_digital_neurons/hdl/math/memory/fractional_exponent_estimation_table.mem"
SOLLYA_COEFFICIENTS = {
    0: (25165824,),
    1: (16055197, 16777216),
    2: (16818757, 10922753, 5771381),
    3: (16775420, 11684617, 3763773, 1328826),
    4: (16777278, 11626044, 4054016, 867224, 229808),
}
IMAGE_LOCATIONS = {
    "degree_0_constant_comparison.png": "02_models_by_degree/01_constant.png",
    "degree_1_linear_comparison.png": "02_models_by_degree/02_linear.png",
    "degree_2_quadratic_comparison.png": "02_models_by_degree/03_quadratic.png",
    "degree_3_cubic_comparison.png": "02_models_by_degree/04_cubic.png",
    "degree_4_quartic_comparison.png": "02_models_by_degree/05_quartic.png",
    "sollya_degrees_zero_to_four.png": "04_sollya_by_degree/01_all_degrees.png",
    "linear_vs_cubic.png": "03_research_vs_maclaurin/01_research_linear_vs_cubic.png",
    "linear_research_vs_maclaurin.png": "03_research_vs_maclaurin/02_linear_research_vs_maclaurin.png",
    "cubic_research_vs_maclaurin.png": "03_research_vs_maclaurin/03_cubic_research_vs_maclaurin.png",
    "maclaurin_degrees_zero_to_four.png": "03_research_vs_maclaurin/04_maclaurin_all_degrees.png",
    "ideal_vs_fixed_point.png": "03_research_vs_maclaurin/05_error_profiles.png",
    "rom_size_tradeoff.png": "05_rom_comparisons/01_accuracy_vs_table_size.png",
    "rom_error_shape.png": "05_rom_comparisons/02_error_shape.png",
    "approximation_formulas.png": "00_formulas/01_formulas.png",
    "sollya_q24_coefficients.png": "01_formulas_and_tables/04_sollya_by_degree_coefficients.png",
    "fractional_accuracy_comparison.png": "06_accuracy_tables/02_percentage_error/01_percentage_error.png",
    "absolute_accuracy_comparison.png": "06_accuracy_tables/01_absolute_error/02_absolute_error.png",
}


def image_path(output_directory, filename, absolute_errors=False, evaluation="ideal"):
    image_directory = output_directory / "images" / ("01_ideal" if evaluation == "ideal" else "02_fixed_point")
    if absolute_errors:
        image_directory = image_directory / "06_absolute_error_plots"
    path = image_directory / IMAGE_LOCATIONS[filename]
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def save_evaluation_figures(figure, output_directory, filename, absolute_errors=False, dpi=180, evaluation=None):
    if evaluation is not None:
        figure.savefig(image_path(output_directory, filename, absolute_errors, evaluation), dpi=dpi, facecolor="white")
        return
    if filename.startswith("degree_"):
        selections = {"ideal": [0, 1], "fixed_point": [2]}
    elif filename == "rom_size_tradeoff.png":
        selections = {"ideal": [0, 1], "fixed_point": [2, 3]}
    elif filename == "ideal_vs_fixed_point.png":
        selections = {"ideal": [0, 2, 4], "fixed_point": [1, 3, 5]}
    elif filename == "sollya_degrees_zero_to_four.png":
        selections = {"ideal": list(range(6)), "fixed_point": list(range(6))}
    else:
        selected = "fixed_point" if filename == "sollya_q24_coefficients.png" else "ideal"
        figure.savefig(image_path(output_directory, filename, absolute_errors, selected), dpi=dpi, facecolor="white")
        return
    for selected, indices in selections.items():
        separated = copy.deepcopy(figure)
        axes = list(separated.axes)
        for position, axis in enumerate(axes):
            if position not in indices:
                axis.set_visible(False)
        if filename == "sollya_degrees_zero_to_four.png":
            for axis in axes[:5]:
                axis.lines[1 if selected == "ideal" else 0].set_visible(False)
                line = axis.lines[0 if selected == "ideal" else 1]
                axis.legend(handles=[line], frameon=False, fontsize=8)
            separated.subplots_adjust(bottom=.16, top=.82, hspace=.55, wspace=.4)
            for text in axes[5].texts:
                convention = "Error magnitudes are nonnegative." if absolute_errors else "Positive error: overestimate.\nNegative error: underestimate."
                text.set_text("Signed 32-bit Q24 coefficients.\n\nEach panel has its own error scale.\n" + convention + "\n\nIndividual display inputs.")
                text.set_fontsize(10)
        else:
            columns = 2 if filename == "rom_size_tradeoff.png" else 1
            rows = (len(indices) + columns - 1) // columns
            separated.set_size_inches(13 if columns == 2 else 11, 5 if columns == 2 else 3.2 * rows + 2)
            for position, index in enumerate(indices):
                axis = axes[index]
                row, column = divmod(position, columns)
                width = .82 / columns
                height = .68 / rows
                axis.set_position((.13 + column * width, .20 + (rows-row-1) * height, width-.07 if columns > 1 else width, height-.075))
                axis.tick_params(labelleft=True, labelbottom=row == rows-1)
                if row == rows-1:
                    axis.set_xlabel("Stored ROM entries (25 bits each)" if filename == "rom_size_tradeoff.png" else "Fractional exponent f")
            if axes[indices[0]].get_legend() is None:
                axes[indices[0]].legend(frameon=False, fontsize=9)
        label = "Ideal arithmetic" if selected == "ideal" else "Fixed-point arithmetic: signed 32-bit Q24 output"
        title = separated._suptitle.get_text()
        if filename == "ideal_vs_fixed_point.png":
            title = "Error profiles across the fractional input range"
        for text in list(separated.texts):
            text.set_visible(False)
        separated.text(.5, .98, title + "\n" + label, ha="center", va="top", fontsize=15)
        note = "Ideal formulas before intermediate/output truncation." if selected == "ideal" else "Q24 input, coefficients and output. Research cubic uses its modified Q24 linear term."
        if filename == "ideal_vs_fixed_point.png":
            note += "\nLines: mean error per bin; shading: tested minimum to maximum. Full selected-input sweep."
        elif filename.startswith("degree_") or filename == "sollya_degrees_zero_to_four.png":
            note += "\nCurves show individual display inputs; full-sweep statistics remain in the accuracy tables."
        separated.text(.5,.035,note,ha="center",fontsize=9)
        separated.savefig(image_path(output_directory, filename, absolute_errors, selected), dpi=dpi, facecolor="white")
        pyplot.close(separated)


def signed_32(values):
    return ((numpy.asarray(values, dtype=numpy.int64) + (1 << 31)) & 0xFFFFFFFF) - (1 << 31)


def shifted_output(fractional_values, integer_exponents):
    unsigned_values = numpy.asarray(fractional_values, dtype=numpy.uint64)
    left_amounts = numpy.clip(integer_exponents, 0, 63).astype(numpy.uint64)
    right_amounts = numpy.clip(-integer_exponents, 0, 63).astype(numpy.uint64)
    shifted_values = numpy.where(integer_exponents >= 0, unsigned_values << left_amounts, unsigned_values >> right_amounts)
    shifted_values = numpy.where((integer_exponents >= 64) | (integer_exponents <= -64), numpy.uint64(0), shifted_values)
    return signed_32(shifted_values.view(numpy.int64) >> 16)


def linear_hardware(encoded_inputs):
    encoded_inputs = numpy.asarray(encoded_inputs, dtype=numpy.int64)
    integer_exponents = encoded_inputs >> 24
    fractional_values = encoded_inputs & (INPUT_SCALE - 1)
    shift_exponents = numpy.where(integer_exponents >= 0, integer_exponents & 63, integer_exponents)
    results = shifted_output(INPUT_SCALE + fractional_values, shift_exponents)
    return numpy.where(integer_exponents < -6, 0, results)


def cubic_hardware(encoded_inputs):
    encoded_inputs = numpy.asarray(encoded_inputs, dtype=numpy.int64)
    fractional_values = encoded_inputs & (INPUT_SCALE - 1)
    squared_values = (fractional_values * fractional_values) >> 24
    correction_values = INPUT_SCALE + ((squared_values - fractional_values) >> 2)
    linear_values = linear_hardware(encoded_inputs)
    results = signed_32((correction_values * linear_values) >> 24)
    return numpy.where((encoded_inputs >> 24) >= 64, 0, results)


def make_table(entry_count, table_path=DEFAULT_TABLE_PATH):
    if entry_count == 1024:
        tokens = Path(table_path).read_text(encoding="utf-8").split()
        table = numpy.array([int(token, 16) for token in tokens], dtype=numpy.int64)
        if len(table) != 1024 or numpy.any(table < INPUT_SCALE) or numpy.any(table >= 2 * INPUT_SCALE):
            raise ValueError("The existing BRAM file must contain 1,024 unsigned Q24 values between one and two.")
        return table
    fractional_positions = numpy.arange(entry_count, dtype=numpy.float64) / entry_count
    return numpy.rint(numpy.exp2(fractional_positions) * INPUT_SCALE).astype(numpy.int64)


def bram_hardware(encoded_inputs, table):
    encoded_inputs = numpy.asarray(encoded_inputs, dtype=numpy.int64)
    address_bits = len(table).bit_length() - 1
    addresses = (encoded_inputs & (INPUT_SCALE - 1)) >> (24 - address_bits)
    return shifted_output(table[addresses], encoded_inputs >> 24)


def maclaurin_approximation(fractional_inputs, degree):
    fractional_inputs = numpy.asarray(fractional_inputs, dtype=numpy.float64)
    result = numpy.ones_like(fractional_inputs)
    term = numpy.ones_like(fractional_inputs)
    for power in range(1, degree + 1):
        term = term * (numpy.log(2.0) * fractional_inputs) / power
        result = result + term
    return result


def sollya_approximation(fractional_inputs, degree):
    return numpy.polynomial.polynomial.polyval(fractional_inputs, numpy.asarray(SOLLYA_COEFFICIENTS[degree], dtype=numpy.float64) / INPUT_SCALE)


def polynomial_fixed_point(model_name, encoded_inputs, output_fractional_bits=8):
    if output_fractional_bits not in (8, 24):
        raise ValueError("Polynomial output precision must be 8 or 24 fractional bits.")
    encoded_inputs = numpy.asarray(encoded_inputs, dtype=numpy.int64)
    if model_name == "linear":
        return fractional_fixed_point("linear", encoded_inputs) if output_fractional_bits == 24 else linear_hardware(encoded_inputs)
    if model_name == "cubic":
        return fractional_fixed_point("cubic", encoded_inputs) if output_fractional_bits == 24 else cubic_hardware(encoded_inputs)
    degree = int(model_name.split("_")[1])
    if model_name.startswith("sollya_"):
        coefficients = SOLLYA_COEFFICIENTS[degree]
    else:
        with localcontext() as context:
            context.prec = 80
            term = Decimal(1)
            logarithm = Decimal(2).ln()
            coefficients = [INPUT_SCALE]
            for power in range(1, degree + 1):
                term = term * logarithm / power
                coefficients.append(int((term * INPUT_SCALE).to_integral_value()))
    result = numpy.full_like(encoded_inputs, coefficients[-1])
    for coefficient in reversed(coefficients[:-1]):
        accumulated = ((result * encoded_inputs) >> 24) + coefficient
        result = checked_signed_32(accumulated) if output_fractional_bits == 24 else signed_32(accumulated)
    return result >> (24 - output_fractional_bits)


def checked_signed_32(values):
    values = numpy.asarray(values, dtype=numpy.int64)
    if numpy.any(values < -(1 << 31)) or numpy.any(values > (1 << 31) - 1):
        raise OverflowError("The Q24 result exceeds signed 32-bit storage; no wrapping or clipping was applied.")
    return values


def fractional_fixed_point(model_name, encoded_inputs, table=None):
    encoded_inputs = numpy.asarray(encoded_inputs, dtype=numpy.int64)
    if numpy.any(encoded_inputs < 0) or numpy.any(encoded_inputs >= INPUT_SCALE):
        raise ValueError("The Q24 fractional comparison requires 0 <= f < 1 and no integer shift.")
    if model_name == "linear":
        return checked_signed_32(INPUT_SCALE + encoded_inputs)
    if model_name == "cubic":
        squared_values = (encoded_inputs * encoded_inputs) >> 24
        correction_values = INPUT_SCALE + ((squared_values - encoded_inputs) >> 2)
        return checked_signed_32((correction_values * (INPUT_SCALE + encoded_inputs)) >> 24)
    if model_name.startswith("bram_"):
        if table is None:
            raise ValueError("A ROM table is required for the fractional comparison.")
        address_bits = len(table).bit_length() - 1
        return checked_signed_32(table[encoded_inputs >> (24 - address_bits)])
    return checked_signed_32(polynomial_fixed_point(model_name, encoded_inputs, output_fractional_bits=24))


def mathematical_models(fractional_inputs, tables):
    models = {"linear": 1 + fractional_inputs, "cubic": (1 + fractional_inputs) * (1 + (fractional_inputs**2 - fractional_inputs) / 4)}
    models.update({f"maclaurin_{degree}": maclaurin_approximation(fractional_inputs, degree) for degree in range(5)})
    models.update({f"sollya_{degree}": sollya_approximation(fractional_inputs, degree) for degree in range(5)})
    for entry_count in tables:
        addresses = numpy.minimum((fractional_inputs * entry_count).astype(numpy.int64), entry_count - 1)
        models[f"bram_{entry_count}"] = numpy.exp2(addresses / entry_count)
    return models


def input_vectors(sample_count, maximum_table_size, step_size=None):
    if step_size is None:
        uniform_inputs = numpy.arange(sample_count, dtype=numpy.int64) * INPUT_SCALE // sample_count
    else:
        uniform_inputs = numpy.arange(0, INPUT_SCALE, step_size, dtype=numpy.int64)
    table_boundaries = numpy.arange(maximum_table_size + 1, dtype=numpy.int64) * (INPUT_SCALE // maximum_table_size)
    directed_inputs = numpy.unique(numpy.concatenate([table_boundaries + offset for offset in (-1, 0, 1)]))
    directed_inputs = directed_inputs[(directed_inputs >= 0) & (directed_inputs < INPUT_SCALE)]
    return uniform_inputs, directed_inputs


def accuracy_statistics(model_name, domain, population, inputs, references, predictions, quantised_reference=False, output_scale=OUTPUT_SCALE):
    signed_errors = predictions - references
    absolute_errors = numpy.abs(signed_errors)
    relative_errors = signed_errors / references
    absolute_relative_errors = numpy.abs(relative_errors)
    worst_absolute_position = int(numpy.argmax(absolute_errors))
    worst_relative_position = int(numpy.argmax(absolute_relative_errors))
    row = {
        "model": model_name,
        "domain": domain,
        "population": population,
        "sample_count": len(inputs),
        "maximum_absolute_error": float(absolute_errors[worst_absolute_position]),
        "worst_absolute_input": float(inputs[worst_absolute_position]),
        "maximum_relative_error_percent": float(100 * absolute_relative_errors[worst_relative_position]),
        "worst_relative_input": float(inputs[worst_relative_position]),
        "mean_absolute_error": float(numpy.mean(absolute_errors)),
        "root_mean_square_error": float(numpy.sqrt(numpy.mean(signed_errors**2))),
        "mean_signed_error": float(numpy.mean(signed_errors)),
        "mean_relative_error_percent": float(100 * numpy.mean(absolute_relative_errors)),
        "mean_signed_relative_error_percent": float(100 * numpy.mean(relative_errors)),
        "relative_error_95th_percentile_percent": float(100 * numpy.percentile(absolute_relative_errors, 95)),
        "underestimate_percent": float(100 * numpy.mean(signed_errors < 0)),
        "overestimate_percent": float(100 * numpy.mean(signed_errors > 0)),
        "negative_output_count": int(numpy.count_nonzero(predictions < 0)),
        "zero_output_count": int(numpy.count_nonzero(predictions == 0)),
        "sampled_monotonicity_violations": int(numpy.count_nonzero(numpy.diff(predictions) < 0)),
    }
    if quantised_reference:
        output_steps = predictions * output_scale
        nearest_reference = numpy.rint(references * output_scale)
        row.update({
            "maximum_absolute_error_output_steps": float(numpy.max(absolute_errors) * output_scale),
            "nearest_reference_match_percent": float(100 * numpy.mean(output_steps == nearest_reference)),
            "within_one_output_step_percent": float(100 * numpy.mean(absolute_errors <= 1 / output_scale)),
            "premature_zero_count": int(numpy.count_nonzero((output_steps == 0) & (nearest_reference > 0))),
        })
    return row


def write_csv(path, rows):
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with Path(path).open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def batched_accuracy_statistics(model_name, domain, population, encoded_inputs, prediction_function, batch_size, collect_profile=False, requested_bin_count=512):
    sample_count = len(encoded_inputs)
    absolute_relative_errors = numpy.empty(sample_count, dtype=numpy.float64)
    aggregate = None
    previous_prediction = None
    bin_count = min(requested_bin_count, sample_count)
    bin_positions = numpy.arange(bin_count + 1, dtype=numpy.int64)
    bin_edges = bin_positions * (sample_count // bin_count) + numpy.minimum(bin_positions, sample_count % bin_count)
    profile = {"centres": numpy.zeros(bin_count), "means": numpy.zeros(bin_count), "minima": numpy.full(bin_count, numpy.inf), "maxima": numpy.full(bin_count, -numpy.inf), "counts": numpy.zeros(bin_count, dtype=numpy.int64)} if collect_profile else None
    if profile is not None:
        profile["absolute"] = {"centres": numpy.zeros(bin_count), "means": numpy.zeros(bin_count), "minima": numpy.full(bin_count, numpy.inf), "maxima": numpy.full(bin_count, -numpy.inf), "counts": numpy.zeros(bin_count, dtype=numpy.int64)}
    quantised_reference = domain == "hardware_fractional"
    output_scale = OUTPUT_SCALE
    weighted_fields = ("mean_absolute_error", "mean_signed_error", "mean_relative_error_percent", "mean_signed_relative_error_percent", "underestimate_percent", "overestimate_percent", "nearest_reference_match_percent", "within_one_output_step_percent")
    count_fields = ("negative_output_count", "zero_output_count", "sampled_monotonicity_violations", "premature_zero_count")
    square_error_sum = 0.0
    for start in range(0, sample_count, batch_size):
        stop = min(start + batch_size, sample_count)
        inputs = encoded_inputs[start:stop] / INPUT_SCALE
        references = numpy.exp2(inputs)
        predictions = prediction_function(encoded_inputs[start:stop])
        if quantised_reference:
            predictions = predictions / output_scale
        row = accuracy_statistics(model_name, domain, population, inputs, references, predictions, quantised_reference, output_scale)
        relative_errors = (predictions - references) / references
        absolute_relative_errors[start:stop] = numpy.abs(relative_errors)
        square_error_sum += row["root_mean_square_error"] ** 2 * len(inputs)
        if previous_prediction is not None and predictions[0] < previous_prediction:
            row["sampled_monotonicity_violations"] += 1
        previous_prediction = predictions[-1]
        if aggregate is None:
            aggregate = row.copy()
            for field in weighted_fields:
                if field in aggregate:
                    aggregate[field] *= len(inputs)
        else:
            for criterion in ("absolute", "relative"):
                error_field = "maximum_absolute_error" if criterion == "absolute" else "maximum_relative_error_percent"
                if row[error_field] > aggregate[error_field]:
                    aggregate[error_field] = row[error_field]
                    aggregate[f"worst_{criterion}_input"] = row[f"worst_{criterion}_input"]
            for field in weighted_fields:
                if field in row:
                    aggregate[field] += row[field] * len(inputs)
            for field in count_fields:
                if field in row:
                    aggregate[field] += row[field]
        if profile is not None:
            for position in range(bin_count):
                first = max(start, int(bin_edges[position])) - start
                last = min(stop, int(bin_edges[position + 1])) - start
                if first < last:
                    errors = 100 * relative_errors[first:last]
                    profile["centres"][position] += numpy.sum(inputs[first:last])
                    profile["means"][position] += numpy.sum(errors)
                    profile["minima"][position] = min(profile["minima"][position], float(numpy.min(errors)))
                    profile["maxima"][position] = max(profile["maxima"][position], float(numpy.max(errors)))
                    profile["counts"][position] += last - first
                    absolute_profile = profile["absolute"]
                    absolute_errors = numpy.abs(errors)
                    absolute_profile["centres"][position] += numpy.sum(inputs[first:last])
                    absolute_profile["means"][position] += numpy.sum(absolute_errors)
                    absolute_profile["minima"][position] = min(absolute_profile["minima"][position], float(numpy.min(absolute_errors)))
                    absolute_profile["maxima"][position] = max(absolute_profile["maxima"][position], float(numpy.max(absolute_errors)))
                    absolute_profile["counts"][position] += last - first
    aggregate["sample_count"] = sample_count
    aggregate["root_mean_square_error"] = float(numpy.sqrt(square_error_sum / sample_count))
    aggregate["relative_error_95th_percentile_percent"] = float(100 * numpy.percentile(absolute_relative_errors, 95, overwrite_input=True))
    for field in weighted_fields:
        if field in aggregate:
            aggregate[field] /= sample_count
    if quantised_reference:
        aggregate["maximum_absolute_error_output_steps"] = aggregate["maximum_absolute_error"] * output_scale
    if profile is not None:
        profile["centres"] /= profile["counts"]
        profile["means"] /= profile["counts"]
        profile["absolute"]["centres"] /= profile["absolute"]["counts"]
        profile["absolute"]["means"] /= profile["absolute"]["counts"]
    return aggregate, profile


def decimal_reference(exponent):
    with localcontext() as context:
        context.prec = 60
        return (Decimal(2).ln() * Decimal.from_float(float(exponent))).exp()


def audit_worst_cases(rows, tables):
    audit_rows = []
    for row in rows:
        if row["domain"] != "hardware_fractional":
            continue
        for criterion in ("absolute", "relative"):
            exponent = row[f"worst_{criterion}_input"]
            encoded_input = numpy.array([int(round(exponent * INPUT_SCALE))], dtype=numpy.int64)
            output_scale = OUTPUT_SCALE
            if row["model"].startswith(("maclaurin_", "sollya_")):
                output_integer = int(fractional_fixed_point(row["model"], encoded_input)[0])
            elif row["model"] == "linear":
                output_integer = int(fractional_fixed_point("linear", encoded_input)[0])
            elif row["model"] == "cubic":
                output_integer = int(fractional_fixed_point("cubic", encoded_input)[0])
            else:
                output_integer = int(fractional_fixed_point(row["model"], encoded_input, tables[int(row["model"].split("_")[1])])[0])
            with localcontext() as context:
                context.prec = 60
                reference = decimal_reference(exponent)
                prediction = Decimal(output_integer) / output_scale
                error = prediction - reference
                audit_rows.append({"model": row["model"], "domain": row["domain"], "population": row["population"], "criterion": criterion, "input": exponent, "output_integer": output_integer, "reference_60_digits": str(reference), "absolute_error_60_digits": str(abs(error)), "relative_error_percent_60_digits": str(100 * abs(error) / reference)})
    return audit_rows


def model_label(name):
    if name.startswith("bram_"):
        return f"ROM: {int(name.split('_')[1]):,} entries"
    if name.startswith("maclaurin_"):
        return f"Maclaurin degree {name.split('_')[1]}"
    if name.startswith("sollya_"):
        return f"Sollya degree {name.split('_')[1]}"
    return "Research cubic (Q24 variant)" if name == "cubic" else name.capitalize()


def signed_error_ticks(axis, lower_value, upper_value, percentage=False):
    lower_value = min(lower_value, 0)
    upper_value = max(upper_value, 0)
    target = max(upper_value - lower_value, 1e-15) / 5
    initial_exponent = int(numpy.floor(numpy.log10(target)))
    for exponent in range(initial_exponent, initial_exponent + 3):
        for factor in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
            increment = factor * 10 ** exponent
            lower_tick = numpy.floor(lower_value / increment) * increment
            if increment >= target and lower_tick + 5 * increment >= upper_value:
                ticks = lower_tick + numpy.arange(6) * increment
                axis.set(ylim=(ticks[0], ticks[-1]), yticks=ticks)
                axis.yaxis.set_major_formatter(FuncFormatter(lambda value, position: numpy.format_float_positional(value, precision=6, unique=False, fractional=False, trim="-") + ("%" if percentage else "")))
                axis.yaxis.set_minor_locator(NullLocator())
                return


def save_formula_table(output_directory):
    rows = [("Actual function", "", r"$2^f$", "2**f")]
    research = {
        1: (r"$1+f$", "1 + f"),
        3: (r"$(1+f)\left(1+\frac{f^2-f}{4}\right)=1+0.75f+0.25f^3$", "(1 + f) * (1 + (f**2 - f)/4) = 1 + 0.75*f + 0.25*f**3"),
    }
    maclaurin = [r"$1$", r"$1+\ln(2)f$", r"$1+\ln(2)f+\frac{(\ln(2))^2f^2}{2}$", r"$1+\ln(2)f+\frac{(\ln(2))^2f^2}{2}+\frac{(\ln(2))^3f^3}{6}$", r"$1+\ln(2)f+\frac{(\ln(2))^2f^2}{2}+\frac{(\ln(2))^3f^3}{6}+\frac{(\ln(2))^4f^4}{24}$"]
    for degree in range(5):
        if degree in research:
            formula, plain_formula = research[degree]
            rows.append(("Research", str(degree), formula, plain_formula))
        terms = ["1"] + [f"ln(2)**{power} * f**{power} / {power}!" for power in range(1, degree + 1)]
        formula = maclaurin[degree]
        if degree:
            numerical_terms = ["1"]
            coefficient = 1.0
            for power in range(1, degree + 1):
                coefficient *= numpy.log(2) / power
                numerical_terms.append(f"{coefficient:.12f}" + ("f" if power == 1 else f"f^{{{power}}}"))
            formula = formula[:-1] + "=" + "+".join(numerical_terms) + "$"
        rows.append(("Maclaurin", str(degree), formula, " + ".join(terms)))
        coefficients = SOLLYA_COEFFICIENTS[degree]
        displayed_terms = []
        exact_terms = []
        for power, value in enumerate(coefficients):
            decimal_value = Decimal(value) / INPUT_SCALE
            coefficient = format(decimal_value, ".12f").rstrip("0").rstrip(".")
            if power and value == INPUT_SCALE:
                coefficient = ""
            displayed_terms.append(coefficient + ("f" if power == 1 else f"f^{{{power}}}" if power else ""))
            exact_terms.append(str(decimal_value) + (f" * f**{power}" if power else ""))
        rows.append(("Sollya", str(degree), "$" + "+".join(displayed_terms) + "$", " + ".join(exact_terms)))
    write_csv(output_directory / "approximation_formulas.csv", [{"model": family, "degree": degree, "formula": plain_formula} for family, degree, formula, plain_formula in rows])
    figure, axis = pyplot.subplots(figsize=(20, 10.5))
    axis.axis("off")
    axis.set_position((0.025, 0.16, 0.95, 0.75))
    table = axis.table(cellText=[[family, degree, formula] for family, degree, formula, plain_formula in rows], colLabels=["Method", "Degree", "Formula for approximating 2^f"], cellLoc="left", bbox=(0, 0, 1, 1), colWidths=[0.17, 0.075, 0.755])
    table.auto_set_font_size(False)
    table.set_fontsize(13)
    colours = {"Research": "#eef4fb", "Maclaurin": "#f5f0fa", "Sollya": "#edf7f1"}
    for (row_number, column), cell in table.get_celld().items():
        cell.set_edgecolor("#d3dce5")
        cell.set_linewidth(0.7)
        if row_number == 0:
            cell.set_facecolor("#20364d")
            cell.set_text_props(color="white", weight="bold")
        else:
            cell.set_facecolor(colours.get(rows[row_number - 1][0], "#f4f6f8"))
        if column == 1:
            cell.set_text_props(ha="center")
    figure.suptitle("Base-two exponential approximations: all formulas", fontsize=20, fontweight="bold", y=0.965)
    figure.text(0.5, 0.925, "Fractional input only: 0 <= f < 1", ha="center", fontsize=13)
    figure.text(0.035, 0.105, "Maclaurin expansions are centred at f = 0. ln(2) is the natural logarithm of 2.", fontsize=12)
    figure.text(0.035, 0.073, "Sollya coefficients are displayed to 12 decimal places; exact values are retained in the script and approximation_formulas.csv.", fontsize=12)
    figure.text(0.035, 0.041, "These are approximation formulas before intermediate/output truncation.", fontsize=12, color="#4c5965")
    for evaluation in ("ideal", "fixed_point"):
        save_evaluation_figures(figure, output_directory, "approximation_formulas.png", dpi=200, evaluation=evaluation)
    pyplot.close(figure)


def save_polynomial_comparisons(output_directory, fractional_inputs, mathematical_predictions, summary_rows, absolute_errors=False):
    error_kind = "Absolute" if absolute_errors else "Signed"
    error_values = numpy.abs if absolute_errors else numpy.asarray
    reference = numpy.exp2(fractional_inputs)
    stride = max(1, len(fractional_inputs) // 4000)
    positions = numpy.arange(0, len(fractional_inputs), stride)
    comparison_rows = [row for row in summary_rows if row["domain"] == "mathematical_fractional" and not row["model"].startswith("bram_")]

    def percentage_ticks(axis, lower_value, upper_value):
        target_increment = (upper_value - lower_value) / 5
        initial_exponent = int(numpy.floor(numpy.log10(target_increment)))
        for exponent in range(initial_exponent, initial_exponent + 3):
            for factor in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
                increment = factor * 10 ** exponent
                lower_tick = numpy.floor(lower_value / increment) * increment
                if increment >= target_increment and lower_tick + 5 * increment >= upper_value:
                    ticks = lower_tick + numpy.arange(6) * increment
                    axis.set(ylim=(ticks[0], ticks[-1]), yticks=ticks)
                    axis.yaxis.set_major_formatter(FuncFormatter(lambda value, position: numpy.format_float_positional(value, precision=6, unique=False, fractional=False, trim="-") + "%"))
                    return
    write_csv(output_directory / "polynomial_accuracy_summary.csv", comparison_rows)
    if not absolute_errors:
        save_formula_table(output_directory)

    write_csv(output_directory / "polynomial_value_samples.csv", [{"fractional_exponent": float(fractional_inputs[position]), "actual_2_to_f": float(reference[position]), **{name: float(values[position]) for name, values in mathematical_predictions.items() if not name.startswith("bram_")}} for position in positions])
    for name, degree, research_colour in (("linear", 1, "#2166ac"), ("cubic", 3, "#d95f02")):
        maclaurin_name = f"maclaurin_{degree}"
        figure, axes = pyplot.subplots(2, 1, figsize=(10, 8), sharex=True)
        axes[0].plot(fractional_inputs[positions], reference[positions], color="#222222", linewidth=2.6, label="Actual: 2^f")
        for model, label, colour, linestyle in ((name, "Research cubic (Q24 variant)" if name == "cubic" else "Research linear", research_colour, "--"), (maclaurin_name, f"Maclaurin degree {degree}", "#7a3db8", ":")):
            values = mathematical_predictions[model]
            axes[0].plot(fractional_inputs[positions], values[positions], color=colour, linestyle=linestyle, linewidth=2, label=label)
            axes[1].plot(fractional_inputs[positions], error_values(100 * (values[positions] - reference[positions]) / reference[positions]), color=colour, linestyle=linestyle, linewidth=2, label=label)
        axes[0].set(ylabel="Calculated value", ylim=(1, 2), yticks=numpy.linspace(1, 2, 6))
        axes[0].legend(frameon=False)
        axes[1].axhline(0, color="#777777", linewidth=0.8)
        lower_error = min(float(numpy.min(line.get_ydata())) for line in axes[1].lines)
        upper_error = max(float(numpy.max(line.get_ydata())) for line in axes[1].lines)
        percentage_ticks(axes[1], lower_error, upper_error)
        axes[1].set(xlabel="Fractional exponent f", ylabel=f"{error_kind} relative error", xlim=(0, 1))
        for axis in axes:
            axis.grid(True, alpha=0.2)
            axis.spines[["top", "right"]].set_visible(False)
        figure.suptitle(f"Actual 2^f versus research and Maclaurin {name} approximations", fontsize=14)
        figure.text(0.5, 0.015, "Ideal arithmetic on the same Q24 input domain. Maclaurin expansion about f = 0. No fixed-point truncation.", ha="center", fontsize=9)
        figure.tight_layout(rect=(0, 0.05, 1, 0.95))
        save_evaluation_figures(figure, output_directory, f"{name}_research_vs_maclaurin.png", absolute_errors)
        pyplot.close(figure)
    figure, axes = pyplot.subplots(2, 3, figsize=(13, 8))
    for degree, axis in zip(range(5), axes.flat):
        errors = error_values(100 * (mathematical_predictions[f"maclaurin_{degree}"] - reference) / reference)
        axis.plot(fractional_inputs[positions], errors[positions], color="#7a3db8", linewidth=2)
        worst_error = max(row["maximum_relative_error_percent"] for row in comparison_rows if row["model"] == f"maclaurin_{degree}")
        axis.set(title=f"Maclaurin degree {degree} | max error {worst_error:.4g}%", xlabel="Fractional exponent f", ylabel=f"{error_kind} relative error", xlim=(0, 1), ylim=(-worst_error * 1.05, 0))
        percentage_ticks(axis, 0 if absolute_errors else -worst_error, worst_error if absolute_errors else 0)
        axis.grid(True, alpha=0.2)
        axis.spines[["top", "right"]].set_visible(False)
    axes.flat[-1].axis("off")
    axes.flat[-1].text(0.05, 0.6, "Maclaurin expansion about f = 0\n\nEach panel uses its own vertical range.\nHigher degrees add more terms.\nAll coefficients use full float64 precision.\nNo Maclaurin HDL implementation is assumed.", fontsize=11, va="center", linespacing=1.6)
    figure.suptitle("Maclaurin approximations of 2^f: degrees 0 through 4", fontsize=15)
    figure.tight_layout(rect=(0, 0, 1, 0.94))
    save_evaluation_figures(figure, output_directory, "maclaurin_degrees_zero_to_four.png", absolute_errors)
    pyplot.close(figure)


def save_degree_comparisons(output_directory, fractional_inputs, mathematical_predictions, summary_rows, absolute_errors=False):
    error_kind = "Absolute" if absolute_errors else "Signed"
    error_values = numpy.abs if absolute_errors else numpy.asarray
    reference = numpy.exp2(fractional_inputs)
    encoded_inputs = numpy.rint(fractional_inputs * INPUT_SCALE).astype(numpy.int64)
    names_by_degree = {degree: (["linear"] if degree == 1 else ["cubic"] if degree == 3 else []) + [f"maclaurin_{degree}", f"sollya_{degree}"] for degree in range(5)}
    degree_names = ("constant", "linear", "quadratic", "cubic", "quartic")
    colours = {"research": "#2166ac", "maclaurin": "#7a3db8", "sollya": "#19845b"}

    def label(name):
        return "Research linear" if name == "linear" else model_label(name)

    def colour(name):
        return colours[name.split("_")[0]] if "_" in name else colours["research"]

    def signed_ticks(axis, maximum):
        lower = min(float(numpy.min(line.get_ydata())) for line in axis.lines)
        upper = max(float(numpy.max(line.get_ydata())) for line in axis.lines)
        if absolute_errors:
            lower = 0
            upper = maximum
        elif abs(lower) >= abs(upper):
            lower = -maximum
        else:
            upper = maximum
        signed_error_ticks(axis, lower, upper)
        axis.axhline(0, color="#777777", linewidth=0.8)

    def maximum_error(name, domain):
        return max(row["maximum_absolute_error"] for row in summary_rows if row["model"] == name and row["domain"] == domain)

    coefficient_rows = []
    for degree, coefficients in SOLLYA_COEFFICIENTS.items():
        for power, integer in enumerate(coefficients):
            coefficient_rows.append({"degree": degree, "power": power, "exact_decimal": str(Decimal(integer) / INPUT_SCALE), "signed_32_bit_integer": integer, "hexadecimal_32_bits": f"{integer & 0xFFFFFFFF:08X}", "binary_32_bits": f"{integer & 0xFFFFFFFF:032b}", "fractional_bits": 24})
    write_csv(output_directory / "sollya_q24_coefficients.csv", coefficient_rows)
    figure, axis = pyplot.subplots(figsize=(12, 4))
    axis.axis("off")
    cells = [[degree, *[f"{coefficients[power]:,}" if power < len(coefficients) else "" for power in range(5)]] for degree, coefficients in SOLLYA_COEFFICIENTS.items()]
    table = axis.table(cellText=cells, colLabels=["Degree", "Constant", "f", "f squared", "f cubed", "f to power 4"], cellLoc="center", loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 2)
    figure.suptitle("Sollya coefficients: signed 32-bit stored integers", fontsize=15)
    figure.text(0.5, 0.06, "Each coefficient equals its stored integer divided by 16,777,216. All coefficients fit signed 32-bit Q24 exactly.", ha="center", fontsize=10)
    figure.tight_layout(rect=(0, 0.1, 1, 0.93))
    save_evaluation_figures(figure, output_directory, "sollya_q24_coefficients.png")
    pyplot.close(figure)

    fixed_predictions = {name: fractional_fixed_point(name, encoded_inputs) / OUTPUT_SCALE for names in names_by_degree.values() for name in names}
    compact_rows = []
    for degree, names in names_by_degree.items():
        figure, axes = pyplot.subplots(3, 1, figsize=(11, 10), sharex=True)
        axes[0].plot(fractional_inputs, reference, color="#222222", linewidth=2.5, label="Actual: 2^f")
        for name in names:
            axes[0].plot(fractional_inputs, mathematical_predictions[name], color=colour(name), linewidth=1.7, linestyle="--", label=label(name))
            axes[1].plot(fractional_inputs, error_values(mathematical_predictions[name] - reference), color=colour(name), linewidth=1.5, label=label(name))
            axes[2].plot(fractional_inputs, error_values(fixed_predictions[name] - reference), color=colour(name), linewidth=1.2, label=label(name))
            ideal_mean = next(row["mean_absolute_error"] for row in summary_rows if row["model"] == name and row["domain"] == "mathematical_fractional" and row["population"] == "uniform")
            fixed_mean = next(row["mean_absolute_error"] for row in summary_rows if row["model"] == name and row["domain"] == "hardware_fractional" and row["population"] == "uniform")
            compact_rows.append({"degree": degree, "model": label(name), "ideal_maximum_absolute_error": maximum_error(name, "mathematical_fractional"), "ideal_mean_absolute_error": ideal_mean, "q24_maximum_absolute_error": maximum_error(name, "hardware_fractional"), "q24_mean_absolute_error": fixed_mean})
        axes[0].set(ylabel="Calculated value", ylim=(0.95, 2.05), yticks=numpy.linspace(1, 2, 6), title="Approximation formulas versus the actual function")
        axes[0].legend(frameon=False, fontsize=9)
        for axis, domain, title in ((axes[1], "mathematical_fractional", "Formula error before arithmetic truncation"), (axes[2], "hardware_fractional", "Fixed-point error: 24 fractional input bits, 24 fractional output bits")):
            signed_ticks(axis, max(maximum_error(name, domain) for name in names))
            axis.set(ylabel=f"{error_kind} error (output units)", title=title)
        for axis in axes:
            axis.set_xlim(0, 1)
            axis.grid(True, alpha=0.2)
            axis.spines[["top", "right"]].set_visible(False)
        axes[-1].set_xlabel("Fractional exponent f")
        figure.suptitle(f"Degree {degree}: {degree_names[degree]} approximation comparison", fontsize=15)
        figure.text(0.5, 0.015, "Q24 input and coefficients; signed 32-bit Q24 output. Maclaurin/Sollya use Horner evaluation; research cubic uses the modified Q24 linear term.\nError curves show individual display inputs, without bin averaging. Full-sweep statistics are in degree_accuracy_comparison.csv.", ha="center", fontsize=9)
        figure.tight_layout(rect=(0, 0.065, 1, 0.95))
        save_evaluation_figures(figure, output_directory, f"degree_{degree}_{degree_names[degree]}_comparison.png", absolute_errors)
        pyplot.close(figure)
    write_csv(output_directory / "degree_accuracy_comparison.csv", compact_rows)

    figure, axes = pyplot.subplots(2, 3, figsize=(13, 8))
    for degree, axis in zip(range(5), axes.flat):
        name = f"sollya_{degree}"
        axis.plot(fractional_inputs, error_values(mathematical_predictions[name] - reference), color=colours["sollya"], label="Formula", linewidth=1.8)
        axis.plot(fractional_inputs, error_values(fixed_predictions[name] - reference), color="#222222", linestyle="--", label="Q24 output evaluation", linewidth=1)
        signed_ticks(axis, max(maximum_error(name, domain) for domain in ("mathematical_fractional", "hardware_fractional")))
        axis.set(title=f"Sollya degree {degree}", xlabel="Fractional exponent f", ylabel=f"{error_kind} error", xlim=(0, 1))
        axis.grid(True, alpha=0.2)
        axis.legend(frameon=False, fontsize=8)
    axes.flat[-1].axis("off")
    convention = "Error = magnitude of approximation minus actual.\nAll errors are nonnegative." if absolute_errors else "Error = approximation minus actual value.\nPositive: overestimate; negative: underestimate."
    axes.flat[-1].text(0.03, 0.6, "All coefficients are signed 32-bit Q24.\n\nEach panel has its own vertical range.\n" + convention + "\nNo new HDL implementation is assumed.", fontsize=11, va="center", linespacing=1.7)
    figure.suptitle(f"Sollya solutions: degrees 0 through 4 | {error_kind.lower()} error", fontsize=15)
    figure.tight_layout(rect=(0, 0, 1, 0.94))
    save_evaluation_figures(figure, output_directory, "sollya_degrees_zero_to_four.png", absolute_errors)
    pyplot.close(figure)

def save_accuracy_tables(output_directory, summary_rows, exhaustive):
    available_names = {row["model"] for row in summary_rows}
    names = []
    for degree in range(5):
        if degree == 1:
            names.append("linear")
        if degree == 3:
            names.append("cubic")
        names.extend((f"maclaurin_{degree}", f"sollya_{degree}"))
    names.extend(sorted((name for name in available_names if name.startswith("bram_")), key=lambda name: int(name.split("_")[1])))
    domains = (("ideal", "mathematical_fractional"), ("fixed_point", "hardware_fractional"))
    compact_rows = []
    for name in names:
        if name not in available_names:
            continue
        row = {"model": f"Research {name}" if name in ("linear", "cubic") else model_label(name)}
        for prefix, domain in domains:
            selected = [item for item in summary_rows if item["model"] == name and item["domain"] == domain]
            fields = ("maximum_error_percent", "mean_error_percent", "worst_input", "maximum_absolute_error", "mean_absolute_error", "worst_absolute_input")
            if not selected:
                row.update({f"{prefix}_{field}": "" for field in fields})
                continue
            worst_relative = max(selected, key=lambda item: item["maximum_relative_error_percent"])
            worst_absolute = max(selected, key=lambda item: item["maximum_absolute_error"])
            uniform = next(item for item in selected if item["population"] == "uniform")
            row.update({f"{prefix}_maximum_error_percent": worst_relative["maximum_relative_error_percent"], f"{prefix}_mean_error_percent": uniform["mean_relative_error_percent"], f"{prefix}_worst_input": worst_relative["worst_relative_input"], f"{prefix}_maximum_absolute_error": worst_absolute["maximum_absolute_error"], f"{prefix}_mean_absolute_error": uniform["mean_absolute_error"], f"{prefix}_worst_absolute_input": worst_absolute["worst_absolute_input"]})
        compact_rows.append(row)
    write_csv(output_directory / "fractional_accuracy_comparison.csv", compact_rows)
    for evaluation, prefix in (("ideal", "ideal"), ("fixed_point", "fixed_point")):
        for absolute_values, filename in ((False, "fractional_accuracy_comparison.png"), (True, "absolute_accuracy_comparison.png")):
            cells = []
            for row in compact_rows:
                values = []
                for selected_prefix in (prefix,):
                    fields = ("maximum_absolute_error", "mean_absolute_error") if absolute_values else ("maximum_error_percent", "mean_error_percent")
                    for field in fields:
                        value = row[f"{selected_prefix}_{field}"]
                        values.append("-" if value == "" else numpy.format_float_positional(float(value), precision=6, unique=False, fractional=False, trim="-"))
                cells.append([row["model"], *values])
            figure, axis = pyplot.subplots(figsize=(17, max(6, 0.38 * len(compact_rows) + 2.5)))
            axis.axis("off")
            axis.set_position((0.025, 0.13, 0.95, 0.76))
            unit = "" if absolute_values else " (%)"
            labels = ["Model", f"Maximum{unit}", f"Mean{unit}"]
            table = axis.table(cellText=cells, colLabels=labels, cellLoc="center", bbox=(0, 0, 1, 1), colWidths=[0.34, 0.33, 0.33])
            table.auto_set_font_size(False)
            table.set_fontsize(10.5)
            for (row_number, column), cell in table.get_celld().items():
                cell.set_edgecolor("#d3dce5")
                cell.set_linewidth(0.6)
                if row_number == 0:
                    cell.set_facecolor("#20364d")
                    cell.set_text_props(weight="bold", color="white")
                else:
                    name = compact_rows[row_number - 1]["model"]
                    cell.set_facecolor("#eef4fb" if name.startswith("Research") else "#f5f0fa" if name.startswith("Maclaurin") else "#edf7f1" if name.startswith("Sollya") else "#f4f6f8")
            title = "All models: absolute error in output units" if absolute_values else "All models: absolute percentage error"
            figure.suptitle(title + (" | Ideal" if evaluation == "ideal" else " | Fixed point Q24"), fontsize=18, fontweight="bold", y=0.96)
            figure.text(0.5, 0.915, "Fractional input only: 0 <= f < 1 | Research, Maclaurin, Sollya and every requested ROM size", ha="center", fontsize=11)
            figure.text(0.035, 0.085, "Ideal formulas before arithmetic truncation." if evaluation == "ideal" else "Signed 32-bit Q24 output. Research cubic uses its modified Q24 linear term.", fontsize=10)
            coverage = "All 16,777,216 fractional inputs tested." if exhaustive else "Sampled input sweep with additional boundary checks."
            figure.text(0.035, 0.055, coverage + " Maxima include boundary checks; means use the uniform sweep. All errors are magnitudes.", fontsize=10)
            figure.text(0.035, 0.025, "The CSV also includes worst-case inputs. Maclaurin/Sollya arithmetic models have not yet been verified in HDL.", fontsize=10, color="#4c5965")
            save_evaluation_figures(figure, output_directory, filename, dpi=200, evaluation=evaluation)
            pyplot.close(figure)


def save_figures(output_directory, fractional_inputs, mathematical_predictions, summary_rows, tables, error_profiles, exhaustive, only_rom_size=False, absolute_errors=False):
    error_kind = "Absolute" if absolute_errors else "Signed"
    error_values = numpy.abs if absolute_errors else numpy.asarray
    colours = {"linear": "#2166ac", "cubic": "#d95f02", "rom": "#19845b"}
    sizes = sorted(tables)
    representative_size = min(sizes, key=lambda size: abs(numpy.log2(size / 1024)))
    representative_name = f"bram_{representative_size}"
    representative_names = ("linear", "cubic", representative_name)
    fractional_reference = numpy.exp2(fractional_inputs)

    def colour(name):
        return colours["rom"] if name.startswith("bram_") else colours[name]

    def finish(figure, filename, note):
        figure.text(0.5, 0.015, note, ha="center", fontsize=9, color="#555555")
        figure.tight_layout(rect=(0, 0.055, 1, 0.94))
        save_evaluation_figures(figure, output_directory, filename, absolute_errors)
        pyplot.close(figure)

    def style(axis, signed=False):
        axis.grid(True, alpha=0.2)
        axis.spines[["top", "right"]].set_visible(False)
        axis.tick_params(labelsize=10)
        if signed:
            axis.axhline(0, color="#777777", linewidth=0.8)

    def selected_rows(domain, population):
        return {row["model"]: row for row in summary_rows if row["domain"] == domain and row["population"] == population}

    def maximum_row(domain, name):
        candidates = [row for row in summary_rows if row["domain"] == domain and row["model"] == name]
        return max(candidates, key=lambda row: row["maximum_relative_error_percent"])

    if not only_rom_size:
        figure, axis = pyplot.subplots(figsize=(10, 5.5))
        for name in ("linear", "cubic"):
            errors = error_values(100 * (mathematical_predictions[name] - fractional_reference) / fractional_reference)
            stride = max(1, len(fractional_inputs) // 4000)
            axis.plot(fractional_inputs[::stride], errors[::stride], label=model_label(name), color=colour(name), linewidth=2)
            worst = maximum_row("mathematical_fractional", name)
            axis.plot(worst["worst_relative_input"], numpy.interp(worst["worst_relative_input"], fractional_inputs, errors), "o", color=colour(name))
        axis.set(xlabel="Fractional exponent f", ylabel=f"{error_kind} relative error (%)", xlim=(0, 1))
        axis.legend(frameon=False)
        style(axis, signed=True)
        figure.suptitle("Linear versus cubic: ideal approximation error", fontsize=15)
        finish(figure, "linear_vs_cubic.png", "Error magnitude, with no fixed-point truncation." if absolute_errors else "Above zero = overestimate; below zero = underestimate. No fixed-point truncation.")

    def signed_worst_error(domain, name):
        row = maximum_row(domain, name)
        inputs = numpy.array([row["worst_relative_input"]])
        reference = numpy.exp2(inputs)
        if domain == "mathematical_fractional":
            prediction = mathematical_models(inputs, tables)[name]
        else:
            encoded = numpy.rint(inputs * INPUT_SCALE).astype(numpy.int64)
            if name == "linear":
                prediction = fractional_fixed_point("linear", encoded) / OUTPUT_SCALE
            elif name == "cubic":
                prediction = fractional_fixed_point("cubic", encoded) / OUTPUT_SCALE
            else:
                prediction = fractional_fixed_point(name, encoded, tables[int(name.split("_")[1])]) / OUTPUT_SCALE
        return float(100 * (prediction[0] - reference[0]) / reference[0])

    figure, axes = pyplot.subplots(2, 2, figsize=(13, 9))
    tick_sizes = sizes if len(sizes) <= 8 else sizes[::2] + ([sizes[-1]] if sizes[-1] not in sizes[::2] else [])
    for row_number, (domain, title) in enumerate((("mathematical_fractional", "Ideal mathematics"), ("hardware_fractional", "Fixed-point arithmetic: 24 fractional input bits, 24 fractional output bits"))):
        uniform_rows = selected_rows(domain, "uniform")
        for column, heading in enumerate((f"{error_kind} error at the worst-case input", f"Mean {error_kind.lower()} error")):
            axis = axes[row_number, column]
            mean_field = "mean_relative_error_percent" if absolute_errors else "mean_signed_relative_error_percent"
            values = [float(error_values(signed_worst_error(domain, f"bram_{size}"))) if column == 0 else uniform_rows[f"bram_{size}"][mean_field] for size in sizes]
            axis.plot(sizes, values, "o-", color=colours["rom"], label="ROM", linewidth=2)
            for name in ("linear", "cubic"):
                value = float(error_values(signed_worst_error(domain, name))) if column == 0 else uniform_rows[name][mean_field]
                axis.axhline(value, color=colour(name), linestyle="--", label=model_label(name), linewidth=1.5)
            axis.set_xscale("log", base=2)
            lower_error = min(float(numpy.min(line.get_ydata())) for line in axis.lines)
            upper_error = max(float(numpy.max(line.get_ydata())) for line in axis.lines)
            signed_error_ticks(axis, lower_error, upper_error, percentage=True)
            axis.axhline(0, color="#777777", linewidth=0.8)
            axis.set_xticks(tick_sizes, [f"{size:,}" for size in tick_sizes], rotation=35, ha="right")
            axis.set(xlabel="Stored ROM entries (25 bits each)", ylabel=f"{error_kind} relative error (%)", title=f"{title}\n{heading}")
            axis.legend(frameon=False, fontsize=9)
            style(axis)
    figure.suptitle(f"ROM {error_kind.lower()} error versus table size", fontsize=16)
    rom_note = "Maximum and mean absolute relative errors. Magnitudes are taken before averaging; all errors are nonnegative." if absolute_errors else "Worst-case input means the input with largest error magnitude; the plotted error retains its sign. Means use signed errors.\nPositive = overestimate; negative = underestimate. Mean signed error can hide cancellation between positive and negative errors."
    finish(figure, "rom_size_tradeoff.png", rom_note)

    if only_rom_size:
        return

    save_polynomial_comparisons(output_directory, fractional_inputs, mathematical_predictions, summary_rows, absolute_errors)
    save_degree_comparisons(output_directory, fractional_inputs, mathematical_predictions, summary_rows, absolute_errors)

    preferred_sizes = [size for size in (16, 64, 256) if size in tables]
    if len(preferred_sizes) < min(3, len(sizes)):
        positions = numpy.linspace(0, len(sizes) - 1, min(3, len(sizes))).astype(int)
        preferred_sizes = sorted(set(preferred_sizes + [sizes[position] for position in positions]))[:3]
    figure, axes = pyplot.subplots(len(preferred_sizes), 1, figsize=(10, 3 * len(preferred_sizes)), squeeze=False)
    for axis, size in zip(axes[:, 0], preferred_sizes):
        interval_count = min(4, size)
        boundaries = numpy.arange(interval_count + 1) / size
        local_inputs = numpy.unique(numpy.concatenate((numpy.linspace(0, interval_count / size, 4001), boundaries, boundaries[1:] - 1 / INPUT_SCALE)))
        local_inputs = local_inputs[local_inputs < 1]
        addresses = numpy.minimum((local_inputs * size).astype(numpy.int64), size - 1)
        reference = numpy.exp2(local_inputs)
        errors = error_values(100 * (numpy.exp2(addresses / size) - reference) / reference)
        axis.plot(local_inputs, errors, color=colours["rom"], linewidth=1.8)
        for boundary in boundaries:
            axis.axvline(boundary, color="#999999", linestyle=":", linewidth=0.7)
        axis.set(title=f"ROM: {size:,} entries | first {interval_count} address intervals", xlabel="Fractional exponent f (zoomed view)", ylabel=f"{error_kind} error (%)", xlim=(0, interval_count / size))
        style(axis, signed=True)
    figure.suptitle("Why ROM approximation error forms a sawtooth", fontsize=15)
    finish(figure, "rom_error_shape.png", "Ideal mathematics. Each panel has its own axis range. Dotted lines mark address changes; values are sampled at interval starts.")

    figure, axes = pyplot.subplots(3, 2, figsize=(12, 10), sharex=True, sharey="row")
    for row_number, name in enumerate(representative_names):
        for axis, domain, heading in ((axes[row_number, 0], "mathematical_fractional", "Ideal mathematics"), (axes[row_number, 1], "hardware_fractional", "Fixed-point arithmetic")):
            profile = error_profiles[(domain, name)]
            if absolute_errors:
                profile = profile["absolute"]
            axis.fill_between(profile["centres"], profile["minima"], profile["maxima"], color=colour(name), alpha=0.22, label="Tested error range")
            axis.plot(profile["centres"], profile["means"], color=colour(name), linewidth=1.8, label="Mean error")
            axis.set(title=f"{model_label(name)} | {heading}", ylabel=f"{error_kind} relative error (%)", xlim=(0, 1))
            style(axis, signed=True)
    for axis in axes[-1]:
        axis.set_xlabel("Fractional exponent f")
    figure.suptitle("How fixed-point arithmetic changes the error", fontsize=16)
    axes[0, 0].legend(frameon=False, fontsize=9)
    plot_bin_count = len(error_profiles[("mathematical_fractional", "linear")]["means"])
    finish(figure, "ideal_vs_fixed_point.png", f"Lines: mean error in {plot_bin_count:,} bins; shading: tested minimum to maximum, using every selected input. Matching vertical scales within each row.\nFixed-point: 24 fractional input bits, 24 fractional output bits. Binning affects only presentation, not the error statistics.")

    if not absolute_errors:
        save_accuracy_tables(output_directory, summary_rows, exhaustive)


def save_cross_method_comparisons(output_directory, tables, requested_bin_count, maximum_errors=False):
    category = "08_max_error_comparisons" if maximum_errors else "07_mean_error_comparisons"
    statistic = "maximum" if maximum_errors else "mean"
    uniform_inputs, boundary_inputs = input_vectors(262144, max(tables))
    encoded_inputs = numpy.unique(numpy.concatenate((uniform_inputs, boundary_inputs)))
    inputs = encoded_inputs / INPUT_SCALE
    references = numpy.exp2(inputs)
    bin_count = min(requested_bin_count, len(encoded_inputs))
    identifiers = encoded_inputs * bin_count // INPUT_SCALE
    positions = numpy.concatenate(([0], numpy.flatnonzero(numpy.diff(identifiers)) + 1))
    counts = numpy.diff(numpy.concatenate((positions, [len(encoded_inputs)])))
    centres = (identifiers[positions] + 0.5) / bin_count
    ideal_predictions = mathematical_models(inputs, tables)
    ideal_profiles = {name: numpy.maximum.reduceat(numpy.abs(values - references), positions) if maximum_errors else numpy.add.reduceat(numpy.abs(values - references), positions) / counts for name, values in ideal_predictions.items()}
    fixed_predictions = {name: fractional_fixed_point(name, encoded_inputs, tables[int(name.split("_")[1])]) / OUTPUT_SCALE if name.startswith("bram_") else fractional_fixed_point(name, encoded_inputs) / OUTPUT_SCALE for name in ideal_predictions}
    fixed_profiles = {name: numpy.maximum.reduceat(numpy.abs(values - references), positions) if maximum_errors else numpy.add.reduceat(numpy.abs(values - references), positions) / counts for name, values in fixed_predictions.items()}
    all_names = list(ideal_profiles)
    colours = {name: pyplot.get_cmap("tab20")(position % 20) for position, name in enumerate(all_names)}
    styles = {name: "--" if position >= 20 else "-" for position, name in enumerate(all_names)}
    groups = (
        ("01_all_models", "All methods and degrees", all_names),
        ("02_mixed_coarse_accuracy", "Mixed comparison: linear, quadratic and small ROMs", ["linear", "sollya_1", "maclaurin_2", "bram_16", "bram_32"]),
        ("03_mixed_medium_accuracy", "Mixed comparison: cubic, quadratic, quartic and ROM", ["cubic", "maclaurin_3", "sollya_2", "maclaurin_4", "bram_128", "bram_1024"]),
        ("04_mixed_high_accuracy", "Mixed comparison: Sollya cubic, Sollya quartic and larger ROMs", ["sollya_3", "sollya_4", "bram_8192", "bram_16384", "bram_32768", "bram_65536"]),
    )
    manifest = []
    for domain, profiles, domain_title in (("ideal", ideal_profiles, "Ideal approximation formulas"), ("q24", fixed_profiles, "Fixed-point arithmetic: 24 fractional input bits, 24 fractional output bits")):
        directory = output_directory / "images" / ("01_ideal" if domain == "ideal" else "02_fixed_point") / category
        directory.mkdir(parents=True, exist_ok=True)
        for filename, title, requested_names in groups:
            names = [name for name in requested_names if name in profiles]
            if not names:
                continue
            figure, axis = pyplot.subplots(figsize=(13, 8 if filename == "01_all_models" else 6))
            for name in names:
                label = f"Research {name}" if name in ("linear", "cubic") else model_label(name)
                axis.plot(centres, profiles[name], color=colours[name], linestyle=styles[name], label=label, linewidth=1.8)
                manifest.append({"figure": f"{filename}.png", "evaluation": domain, "model": label})
            maximum = max(float(numpy.max(profiles[name])) for name in names)
            target = max(maximum, 1e-15) / 5
            scale = 10 ** numpy.floor(numpy.log10(target))
            increment = next(value for value in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10) if value >= target / scale) * scale
            ticks = numpy.arange(6) * increment
            axis.set(xlabel="Fractional exponent f", ylabel=f"{statistic.capitalize()} absolute error within each display bin", xlim=(0, 1), ylim=(0, ticks[-1]), yticks=ticks)
            axis.yaxis.set_major_formatter(FuncFormatter(lambda value, position: numpy.format_float_positional(value, precision=6, unique=False, fractional=False, trim="-")))
            axis.grid(True, alpha=0.2)
            axis.spines[["top", "right"]].set_visible(False)
            figure.suptitle(title, fontsize=15)
            axis.set_title(domain_title, fontsize=11)
            if filename == "01_all_models":
                axis.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=4, fontsize=8, frameon=False)
                bottom_margin = 0.28
            else:
                axis.legend(frameon=False, fontsize=9)
                bottom_margin = 0.12
            note = f"All curves share the same axes. Each point is the {statistic} absolute error among display inputs in one of {bin_count:,} bins."
            figure.text(0.5, 0.04, note, ha="center", fontsize=9)
            figure.text(0.5, 0.015, "Display grid: 262,144 uniform inputs plus adjacent ROM-boundary inputs. Full-sweep statistics remain in the accuracy tables.", ha="center", fontsize=9)
            figure.tight_layout(rect=(0, bottom_margin, 1, 0.94))
            if filename == "01_all_models":
                axis.set_position((0.13, 0.34, 0.84, 0.5))
            else:
                figure.subplots_adjust(left=0.14)
            figure.savefig(directory / f"{filename}.png", dpi=180, facecolor="white")
            pyplot.close(figure)
    rom_groups = (
        ("05_rom_all_sizes", "ROM comparison: all table sizes", sorted(tables)),
        ("06_rom_small_tables", "ROM comparison: smaller tables", [size for size in sorted(tables) if size <= 1024]),
        ("07_rom_large_tables", "ROM comparison: larger tables", [size for size in sorted(tables) if size >= 2048]),
        ("08_rom_error_zoom", "ROM absolute error: individual inputs near zero", [size for size in sorted(tables) if size <= 128]),
    )
    for domain, rom_predictions, rom_profiles, domain_title in (("ideal", ideal_predictions, ideal_profiles, "Ideal reference"), ("q24", fixed_predictions, fixed_profiles, "24 fractional input bits, 24 fractional output bits")):
        domain_directory = output_directory / "images" / ("01_ideal" if domain == "ideal" else "02_fixed_point")
        directory = domain_directory / category
        rom_directories = (directory,) if maximum_errors else (directory, domain_directory / "06_absolute_error_plots" / "05_rom_comparisons")
        for filename, title, sizes in rom_groups:
            if not sizes:
                continue
            figure, axis = pyplot.subplots(figsize=(13, 6))
            zoomed = filename == "08_rom_error_zoom"
            for position, size in enumerate(sizes):
                name = f"bram_{size}"
                selected = inputs <= 1 / min(sizes) if zoomed else slice(None)
                horizontal_values = inputs[selected] if zoomed else centres
                errors = numpy.abs(rom_predictions[name][selected] - references[selected]) if zoomed else rom_profiles[name]
                axis.plot(horizontal_values, errors, label=model_label(name), color=pyplot.get_cmap("tab20")(position), linewidth=1.5)
                manifest.append({"figure": f"{filename}.png", "evaluation": domain, "model": model_label(name)})
            axis.set(xlabel="Fractional exponent f", ylabel="Absolute error" if zoomed else f"{statistic.capitalize()} absolute error within each display bin", xlim=(0, 1 / min(sizes) if zoomed else 1))
            maximum = max(float(numpy.max(numpy.abs(rom_predictions[f"bram_{size}"][selected] - references[selected]))) if zoomed else float(numpy.max(rom_profiles[f"bram_{size}"])) for size in sizes)
            target = max(maximum, 1e-15) / 5
            scale = 10 ** numpy.floor(numpy.log10(target))
            increment = next(value for value in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10) if value >= target / scale) * scale
            ticks = numpy.arange(6) * increment
            axis.set(ylim=(0, ticks[-1]), yticks=ticks)
            axis.yaxis.set_major_formatter(FuncFormatter(lambda value, position: numpy.format_float_positional(value, precision=6, unique=False, fractional=False, trim="-")))
            axis.grid(True, alpha=0.2)
            axis.spines[["top", "right"]].set_visible(False)
            axis.legend(frameon=False, fontsize=9, ncol=2)
            axis.set_title(title + "\n" + domain_title, fontsize=15)
            note = "Each point is an individual input error; the lines connect sampled inputs across ROM address boundaries." if zoomed else f"Each point is the {statistic} absolute error among display inputs in one of {bin_count:,} bins."
            figure.text(0.5, 0.04, note, ha="center", fontsize=9)
            figure.text(0.5, 0.015, "Ideal reference before rounding." if domain == "ideal" else "24 fractional input bits; rounded Q24 ROM entries; signed 32-bit output retains 24 fractional bits.", ha="center", fontsize=9)
            figure.tight_layout(rect=(0, 0.12, 1, 1))
            figure.subplots_adjust(left=0.14)
            for rom_directory in rom_directories:
                rom_directory.mkdir(parents=True, exist_ok=True)
                figure.savefig(rom_directory / f"{filename}.png", dpi=180, facecolor="white")
            pyplot.close(figure)
    for evaluation in ("ideal", "q24"):
        directory = output_directory / "images" / ("01_ideal" if evaluation == "ideal" else "02_fixed_point") / category
        write_csv(directory / "comparison_contents.csv", [row for row in manifest if row["evaluation"] == evaluation])


def parse_step_size(value):
    try:
        step_size = int(value, 2) if value.lower().startswith("0b") else int(value, 10)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Use a decimal integer such as 8 or a binary integer such as 0b1000.") from error
    if not 1 <= step_size < INPUT_SCALE:
        raise argparse.ArgumentTypeError("Step size must be between 1 and 16777215 encoded units.")
    return step_size


def parse_arguments():
    parser = argparse.ArgumentParser(description="Compare linear, cubic and variable-size ROM approximations of 2**f, with 0 <= f < 1 and the integer exponent fixed at zero.")
    parser.add_argument("--rom-sizes", "--bram-sizes", dest="bram_sizes", nargs="+", type=int, default=DEFAULT_BRAM_SIZES, help="Power-of-two ROM entry counts between 2 and 65536. Default: 16 through 65536.")
    sampling_options = parser.add_mutually_exclusive_group()
    sampling_options.add_argument("--step-size", type=parse_step_size, help="Encoded input increment: decimal 8 or binary 0b1000. Default: 1 (exhaustive Q24 sweep). Real exponent increment = step size / 2**24.")
    sampling_options.add_argument("--fractional-samples", "--samples", dest="fractional_samples", type=int, help="Choose the sample count instead of the step size.")
    parser.add_argument("--bins", type=int, default=256, help="Number of plot bins. Default: 256; limited to the number of tested inputs. Changes presentation, not accuracy statistics.")
    parser.add_argument("--batch-size", type=int, default=262144, help="Inputs processed together. Default: 262144; affects memory use, not accuracy.")
    parser.add_argument("--table-file", type=Path, default=DEFAULT_TABLE_PATH, help="Existing 1024-entry HDL table, loaded whenever that size is requested.")
    parser.add_argument("--output-directory", type=Path, default=Path(__file__).resolve().parent / "results")
    parser.add_argument("--save-samples", action="store_true", help="Also save every uniform fractional input and model output to CSV.")
    arguments = parser.parse_args()
    arguments.bram_sizes = sorted(set(arguments.bram_sizes))
    if any(size < 2 or size > 65536 or size & (size - 1) for size in arguments.bram_sizes):
        parser.error("ROM sizes must be powers of two between 2 and 65536.")
    if arguments.fractional_samples is None:
        if arguments.step_size is None:
            arguments.step_size = 1
        arguments.fractional_samples = (INPUT_SCALE - 1) // arguments.step_size + 1
    if not 2 <= arguments.fractional_samples <= INPUT_SCALE:
        parser.error("The fractional sample count must be between 2 and 16777216.")
    if arguments.batch_size < 1:
        parser.error("Batch size must be positive.")
    if arguments.bins < 1:
        parser.error("The number of bins must be positive.")
    return arguments


def main():
    arguments = parse_arguments()
    start_time = time.perf_counter()
    output_directory = arguments.output_directory.resolve()
    configuration_path = output_directory / "run_configuration.json"
    if configuration_path.exists() and json.loads(configuration_path.read_text())["output_fractional_bits"] != OUTPUT_FRACTIONAL_BITS:
        raise ValueError("This folder contains results at another output precision. Choose a separate --output-directory for Q24 results.")
    output_directory.mkdir(parents=True, exist_ok=True)
    tables = {size: make_table(size, arguments.table_file) for size in arguments.bram_sizes}
    uniform_inputs, directed_inputs = input_vectors(arguments.fractional_samples, max(tables), arguments.step_size)
    exhaustive = arguments.fractional_samples == INPUT_SCALE
    representative_size = min(tables, key=lambda size: abs(numpy.log2(size / 1024)))
    representative_names = ("linear", "cubic", f"bram_{representative_size}")
    names = ["linear", "cubic", *[f"bram_{size}" for size in tables], *[f"maclaurin_{degree}" for degree in range(5)], *[f"sollya_{degree}" for degree in range(5)]]
    summary_rows = []
    error_profiles = {}
    print(f"Testing {len(uniform_inputs):,} fractional inputs per model, integer exponent zero, signed 32-bit Q24 output, in batches of {arguments.batch_size:,}.", flush=True)
    if arguments.step_size is not None:
        print(f"Encoded step: {arguments.step_size} ({bin(arguments.step_size)}); fractional exponent step: {arguments.step_size / INPUT_SCALE:.15g}.", flush=True)
    for name in names:
        for domain in ("mathematical_fractional", "hardware_fractional"):
            if domain == "hardware_fractional" and name.startswith(("maclaurin_", "sollya_")):
                prediction_function = lambda values, name=name: fractional_fixed_point(name, values)
            elif name.startswith("sollya_"):
                if domain == "hardware_fractional":
                    continue
                degree = int(name.split("_")[1])
                prediction_function = lambda values, degree=degree: sollya_approximation(values / INPUT_SCALE, degree)
            elif name.startswith("maclaurin_"):
                if domain == "hardware_fractional":
                    continue
                degree = int(name.split("_")[1])
                prediction_function = lambda values, degree=degree: maclaurin_approximation(values / INPUT_SCALE, degree)
            elif domain == "mathematical_fractional":
                if name == "linear":
                    prediction_function = lambda values: 1 + values / INPUT_SCALE
                elif name == "cubic":
                    prediction_function = lambda values: (1 + values / INPUT_SCALE) * (1 + ((values / INPUT_SCALE)**2 - values / INPUT_SCALE) / 4)
                else:
                    size = int(name.split("_")[1])
                    prediction_function = lambda values, size=size: numpy.exp2((values >> (24 - (size.bit_length() - 1))) / size)
            elif name == "linear":
                prediction_function = lambda values: fractional_fixed_point("linear", values)
            elif name == "cubic":
                prediction_function = lambda values: fractional_fixed_point("cubic", values)
            else:
                table = tables[int(name.split("_")[1])]
                prediction_function = lambda values, table=table, name=name: fractional_fixed_point(name, values, table)
            for population, encoded_inputs in (("uniform", uniform_inputs), ("directed_boundaries", directed_inputs)):
                collect_profile = population == "uniform" and name in representative_names
                row, profile = batched_accuracy_statistics(name, domain, population, encoded_inputs, prediction_function, arguments.batch_size, collect_profile, arguments.bins)
                summary_rows.append(row)
                if profile is not None:
                    error_profiles[(domain, name)] = profile
        print(f"Completed {model_label(name)} ({time.perf_counter() - start_time:.1f} seconds elapsed)", flush=True)
    write_csv(output_directory / "accuracy_summary.csv", summary_rows)
    write_csv(output_directory / "worst_case_decimal_audit.csv", audit_worst_cases(summary_rows, tables))
    write_csv(output_directory / "bram_storage.csv", [{"entries": size, "address_bits": size.bit_length() - 1, "bits_per_entry": 25, "logical_storage_bits": 25 * size, "logical_storage_bytes": 25 * size / 8, "source": str(arguments.table_file.resolve()) if size == 1024 else "round_to_nearest(2**(address/entries) * 2**24)"} for size in tables])
    if arguments.save_samples:
        hardware_names = names
        print("Writing raw samples; this optional CSV can be large for an exhaustive run.", flush=True)
        with (output_directory / "hardware_samples.csv").open("w", newline="", encoding="utf-8") as output_file:
            writer = csv.writer(output_file)
            writer.writerow(["encoded_input", "fractional_exponent", "reference", *[f"{name}_output_integer" for name in hardware_names]])
            for start in range(0, len(uniform_inputs), arguments.batch_size):
                encoded_inputs = uniform_inputs[start:start + arguments.batch_size]
                inputs = encoded_inputs / INPUT_SCALE
                references = numpy.exp2(inputs)
                predictions = {"linear": fractional_fixed_point("linear", encoded_inputs), "cubic": fractional_fixed_point("cubic", encoded_inputs)}
                predictions.update({f"bram_{size}": fractional_fixed_point(f"bram_{size}", encoded_inputs, table) for size, table in tables.items()})
                predictions.update({name: fractional_fixed_point(name, encoded_inputs) for name in names if name.startswith(("maclaurin_", "sollya_"))})
                writer.writerows((int(value), float(inputs[position]), float(references[position]), *[int(predictions[name][position]) for name in hardware_names]) for position, value in enumerate(encoded_inputs))
    elif (output_directory / "hardware_samples.csv").is_file():
        (output_directory / "hardware_samples.csv").unlink()
    metadata = {
        "rom_sizes": arguments.bram_sizes,
        "maclaurin_degrees": list(range(5)),
        "maclaurin_expansion_point": 0,
        "maclaurin_arithmetic": "Ideal references and Q24 input/coefficient/intermediate Horner evaluation with coefficients rounded to nearest, ties to even; each product shifted by 24, final output retained as signed 32-bit Q24.",
        "sollya_coefficient_integers": SOLLYA_COEFFICIENTS,
        "sollya_coefficient_fractional_bits": 24,
        "polynomial_fixed_point": "Q24 input, coefficients and intermediates; Q24 output. Maclaurin/Sollya use Horner evaluation with 64-bit products shifted by 24; there is no final shift by 16. Research cubic retains its linear term in Q24, unlike the original Q8 IP. Maclaurin/Sollya models are not verified HDL implementations.",
        "integer_exponent": 0,
        "fractional_exponent_range": "0 <= f < 1",
        "input_fractional_bits": 24,
        "output_fractional_bits": OUTPUT_FRACTIONAL_BITS,
        "output_total_bits": 32,
        "output_signed": True,
        "output_storage": "NumPy int64 container, range checked against signed 32-bit Q24",
        "overflow_policy": "Raise OverflowError before any signed 32-bit Q24 overflow; no clipping at 2.",
        "research_cubic_variant": "Q24 linear term and Q24 correction, followed by a 64-bit product shifted by 24; modified from the original Q8 IP.",
        "table_fractional_bits": 24,
        "table_width_bits": 25,
        "uniform_encoded_input_count": len(uniform_inputs),
        "directed_input_count": len(directed_inputs),
        "exhaustive_q24_coverage": exhaustive,
        "batch_size": arguments.batch_size,
        "encoded_step_size": arguments.step_size,
        "fractional_step_size": arguments.step_size / INPUT_SCALE if arguments.step_size is not None else None,
        "requested_plot_bin_count": arguments.bins,
        "plot_bin_count": min(arguments.bins, len(uniform_inputs)),
        "plot_profile_uses_every_input": False,
        "plot_profile_sampling": "262144 uniform display inputs plus ROM boundaries and neighbours; accuracy tables use the full selected sweep.",
        "raw_samples_saved": arguments.save_samples,
        "first_uniform_exponent": float(uniform_inputs[0] / INPUT_SCALE),
        "second_uniform_exponent": float(uniform_inputs[1] / INPUT_SCALE),
        "last_uniform_exponent": float(uniform_inputs[-1] / INPUT_SCALE),
        "last_directed_exponent": float(directed_inputs[-1] / INPUT_SCALE),
        "sampling": "Encoded inputs start at zero and increase by the selected step size, excluding 2**24." if arguments.step_size is not None else "Encoded inputs are floor(index * 2**24 / sample_count). Integer bits are always zero.",
        "reference": "NumPy float64 sweep; hardware worst-case candidates independently reevaluated using 60-digit Decimal arithmetic.",
        "reference_rounding": "Nearest integer, ties to even, for the reference-match statistic; fixed-point product shifts truncate instead.",
        "boundary_coverage": "Every ROM boundary and adjacent Q24 inputs inside [0,1). These are already included in exhaustive mode and remain a separate diagnostic population.",
        "mathematical_model": "Ideal linear, cubic and ROM fractional approximations evaluated in float64 before table rounding and fixed-point truncation.",
        "hardware_model": "Fractional core only, before the integer shift: Q24 input and signed 32-bit Q24 output; rounded Q24 ROM entries; research cubic retains the full Q24 linear term. Existing Q8 HDL/resource results describe different implementations.",
        "limitations": ["Exhaustive means all representable Q24 inputs, not every real number in [0,1)." if exhaustive else "Reduced-sample maxima are sampled estimates, not exhaustive bounds.", "Sweeps use float64 reference arithmetic; the Decimal audit reevaluates identified hardware worst cases, not all references.", "Uniform and directed means have different input weighting.", "Logical ROM storage does not measure physical hardware resources."],
        "runtime_seconds": round(time.perf_counter() - start_time, 3),
        "numpy_version": numpy.__version__,
    }
    (output_directory / "run_configuration.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    from plot_accuracy_results import render_results
    render_results(output_directory, refresh_tables=True, tables=tables)
    print("Fixed-point accuracy, fractional exponent only:")
    print(f"{'Model':<24} {'Max relative (%)':>18} {'Mean relative (%)':>19} {'Max error (steps)':>19}")
    for row in summary_rows:
        if row["domain"] == "hardware_fractional" and row["population"] == "uniform":
            print(f"{model_label(row['model']):<24} {row['maximum_relative_error_percent']:>18.7g} {row['mean_relative_error_percent']:>19.7g} {row['maximum_absolute_error_output_steps']:>19.7g}")
    print(f"Completed in {time.perf_counter() - start_time:.1f} seconds. Results saved to {output_directory}")


if __name__ == "__main__":
    main()
