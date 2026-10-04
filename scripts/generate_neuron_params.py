"""Generate fixed-point SystemVerilog constants for FH neurons and synapses.

The values, fixed-point formats, and conversion method below are reproduced
from the original research team's C_fixedpoint/Single_Neuron/neuron_fixed.c
and C_fixedpoint/1D_Synfire/Synfire_1D_3neur_fixed.c.
The research code accompanies:

    S. Bhattacharyya, P. R. Ayyappan and J. O. Hasler,
    "Towards Scalable Digital Modeling of Networks of Biorealistic
    Silicon Neurons," IEEE JETCAS, 2023.
    DOI: 10.1109/JETCAS.2023.3330069

The conversion matches the research code's C macro:

    fi(value, fractional_bits) = (int)(value * 2^fractional_bits)

The source C arrays and variables use 32-bit IEEE-754 float values, while
some macro arguments are double expressions or already fixed integers. Each
is converted according to its actual C source type. Python's int() truncates
toward zero, just like the C cast to int.
"""

from __future__ import annotations

import argparse
import math
import struct
from pathlib import Path


VALUE_WIDTH = 32

# Fractional-bit counts used by the reference C model.
STATE_FRAC_BITS = 24
CONSTANT_FRAC_BITS = 24
MATRIX_FRAC_BITS = 23
CURRENT_FRAC_BITS = 8
TRIANGLE_FRAC_BITS = 16

# Initial state offsets from neuron_fixed.c.
OFFSET_A = 2.8309
OFFSET_B = -2.1341
OFFSET_C = 4.4310

INITIAL_STATE = [
    -OFFSET_A,  # Vmem
    -OFFSET_B,  # VK
    -OFFSET_C,  # Vg
    -OFFSET_C,  # VNa
]

# Model and simulation constants from neuron_fixed.c.
MODEL_CONSTANTS = {
    "DT": 0.001,
    "EXPMEL": 7.3306,
    "EXPVSAT": 6.6116,
    "EXPMVGK": 0.2279,
    "EXPVNA": 0.0182,
    "EXPEK": 0.1364,
    "KP": -0.75,
}

INPUT_PULSE_HEIGHT = 100.0

# Constant 4 by 8 neuron matrix from neuron_fixed.c.
NEURON_MATRIX = [
    [
        70.785082606739 / 1000,
        20.2173858708657 / 1000,
        1.32921811478727 / 1000,
        2387.77324751470 / 1000,
        -23893.5281204093 / 1000,
        -9026.24819333978 / 1000,
        135.171307831437 / 1000,
        -232.108910489866 / 1000,
    ],
    [
        70.7850826067390 / 1000,
        20.2173858708657 / 1000,
        1.32921811478727 / 1000,
        2387.77324751470 / 1000,
        -23893.5281204093 / 1000,
        -9026.24819333978 / 1000,
        410.668585361385 / 1000,
        -232.108910489866 / 1000,
    ],
    [
        69.6603580753146 / 1000,
        19.8961460133584 / 1000,
        1.30809778595160 / 1000,
        4377.58428711028 / 1000,
        -43804.8015540837 / 1000,
        -8882.82754034463 / 1000,
        133.023532053490 / 1000,
        425.533002564754 / 1000,
    ],
    [
        65.3065856956075 / 1000,
        18.6526368875235 / 1000,
        1.22634167432962 / 1000,
        20587.9115563489 / 1000,
        -206015.309127084 / 1000,
        -8327.65081907309 / 1000,
        124.709561300147 / 1000,
        23636.4240515513 / 1000,
    ],
]

# Network constants from C_fixedpoint/1D_Synfire/Synfire_1D_3neur_fixed.c.
# Each neuron has two triangle states: even index is excitatory, odd is
# inhibitory. Matrix columns select the slope for Vmem above/below threshold.
TRIANGLE_INITIAL_VDD = 144.2695  # Stored as a C float before fi(..., 16).
TRIANGLE_UPPER_BOUND_Q16 = 0x009044FD  # Literal C integer, one LSB below init.
TRIANGLE_MINUS_SPIKE_THRESHOLD = -1.4542  # Direct C double expression.
TRIANGLE_SLOPE_MATRIX = [
    [-71.2378, 13.4597],
    [-272.0602, 3.4893],
]

# The 3-neuron file uses these fixed integer literals in Network_ODE.
SYNAPSE_TRIANGLE_SCALE_Q24 = 0xCCCCC
SYNAPSE_GATE_OFFSETS_Q16 = [8509364, 945487]  # Excitatory, inhibitory.
SYNAPSE_EFFECTIVE_COUPLING_Q24 = -10066329
SYNAPSE_EXCITATORY_EXP_BIAS_Q24 = 0x56000000
SYNAPSE_OFF = 21
SYNAPSE_EXCITATORY_SCALE_Q8 = 0x58

# Source weights are C floats. Values >= 2.5 disable a connection. Rows are
# receiving neurons; each sending neuron has excitatory and inhibitory columns.
SYNFIRE_1D_3_WEIGHTS = [
    [2.5, 2.5, 2.5, 2.5, 0.26, 2.5],
    [0.26, 2.5, 2.5, 2.5, 2.5, 2.5],
    [2.5, 2.5, 0.26, 2.5, 2.5, 2.5],
]
SYNAPSE_MATRIX_FIXED_TERM = 2.1425  # Stored as a C float.
SYNAPSE_KP = 0.75  # C double macro used only while computing the matrix.
SYNAPSE_UT = 0.025  # C double macro used only while computing the matrix.
SYNAPSE_WEIGHT_EXP_BIAS = 9.9658

SYNFIRE_1D_3_NEURON_COUNT = 3
SYNFIRE_1D_3_STEPS = 190000
SYNFIRE_1D_3_PULSE_START = 60000
SYNFIRE_1D_3_PULSE_END = 140000  # Inclusive in the C loop.
SYNFIRE_1D_3_INPUT_NEURON = 0
SYNFIRE_1D_3_PULSE_HEIGHT = 80.0


def as_c_float(value: float) -> float:
    """Round a Python float to the same precision as a C float."""

    return struct.unpack("f", struct.pack("f", value))[0]


def to_fixed(value: float, fractional_bits: int) -> int:
    """Convert a C float value to a signed fixed-point integer."""

    c_value = as_c_float(value)
    return int(c_value * (1 << fractional_bits))


def c_expression_to_fixed(value: float, fractional_bits: int) -> int:
    """Convert a direct C double expression without rounding it to float."""

    return int(value * (1 << fractional_bits))


def synapse_coefficient(weight: float) -> int:
    """Reproduce compute_synapse_mat and float_synarray_to_fix in the C model."""

    c_weight = as_c_float(weight)
    if c_weight >= 2.5:
        return 0
    c_fixed_term = as_c_float(SYNAPSE_MATRIX_FIXED_TERM)
    exponent = (
        (-SYNAPSE_KP * c_weight) / (SYNAPSE_UT * math.log(2))
        + SYNAPSE_WEIGHT_EXP_BIAS
    )
    coefficient = as_c_float(c_fixed_term * math.pow(2, exponent))
    return to_fixed(coefficient, STATE_FRAC_BITS)


def sv_signed(value: int) -> str:
    """Format an integer as an explicit signed SystemVerilog literal."""

    if value < 0:
        return f"-{VALUE_WIDTH}'sd{abs(value)}"
    return f"{VALUE_WIDTH}'sd{value}"


def format_array(values: list[int], indent: str = "        ") -> str:
    """Format a one-dimensional SystemVerilog assignment pattern."""

    return indent + "'{" + ", ".join(sv_signed(value) for value in values) + "}"


def generate_package() -> str:
    """Build the complete SystemVerilog package as text."""

    initial_state = [to_fixed(value, STATE_FRAC_BITS) for value in INITIAL_STATE]
    fixed_constants = {
        name: to_fixed(value, CONSTANT_FRAC_BITS)
        for name, value in MODEL_CONSTANTS.items()
    }
    pulse_height = to_fixed(INPUT_PULSE_HEIGHT, CURRENT_FRAC_BITS)
    fixed_matrix = [
        [to_fixed(value, MATRIX_FRAC_BITS) for value in row]
        for row in NEURON_MATRIX
    ]
    triangle_initial = to_fixed(TRIANGLE_INITIAL_VDD, TRIANGLE_FRAC_BITS)
    triangle_threshold = -c_expression_to_fixed(
        TRIANGLE_MINUS_SPIKE_THRESHOLD, STATE_FRAC_BITS
    )
    triangle_slopes = [
        [to_fixed(value, TRIANGLE_FRAC_BITS) for value in row]
        for row in TRIANGLE_SLOPE_MATRIX
    ]
    synapse_coefficients = [
        [synapse_coefficient(weight) for weight in row]
        for row in SYNFIRE_1D_3_WEIGHTS
    ]
    synapse_exp_biases = [
        SYNAPSE_EXCITATORY_EXP_BIAS_Q24,
        c_expression_to_fixed(SYNAPSE_OFF - 2.0, STATE_FRAC_BITS),
    ]
    inhibitory_vmem_offset = c_expression_to_fixed(
        13.2053 - SYNAPSE_OFF, STATE_FRAC_BITS
    )
    synfire_pulse_height = to_fixed(SYNFIRE_1D_3_PULSE_HEIGHT, CURRENT_FRAC_BITS)

    lines = [
        "// This file is generated by scripts/generate_neuron_params.py.",
        "// Edit the Python source values and rerun the script instead of editing this file.",
        "// Values, formats, and conversion method reproduce the research team's",
        "// C_fixedpoint/Single_Neuron/neuron_fixed.c and",
        "// C_fixedpoint/1D_Synfire/Synfire_1D_3neur_fixed.c reference models.",
        "// DOI: 10.1109/JETCAS.2023.3330069",
        "",
        "package neuron_params_generated_pkg;",
        "",
        f"    localparam int VALUE_WIDTH = {VALUE_WIDTH};",
        f"    localparam int STATE_FRAC_BITS = {STATE_FRAC_BITS};",
        f"    localparam int CONSTANT_FRAC_BITS = {CONSTANT_FRAC_BITS};",
        f"    localparam int MATRIX_FRAC_BITS = {MATRIX_FRAC_BITS};",
        f"    localparam int CURRENT_FRAC_BITS = {CURRENT_FRAC_BITS};",
        f"    localparam int TRIANGLE_FRAC_BITS = {TRIANGLE_FRAC_BITS};",
        "",
        "    typedef logic signed [VALUE_WIDTH-1:0] fixed_t;",
        "",
        "    // Initial state order: Vmem, VK, Vg, VNa.",
        "    localparam fixed_t INITIAL_STATE [0:3] = '{",
        "        " + ", ".join(sv_signed(value) for value in initial_state),
        "    };",
        "",
        "    // Constants use 24 fractional bits unless stated otherwise.",
    ]

    for name in ("DT", "EXPMEL", "EXPVSAT", "EXPMVGK", "EXPVNA", "EXPEK", "KP"):
        lines.append(
            f"    localparam fixed_t {name} = {sv_signed(fixed_constants[name])};"
        )

    lines.extend(
        [
            "",
            "    // Input current uses 8 fractional bits.",
            "    localparam fixed_t INPUT_PULSE_HEIGHT = " + sv_signed(pulse_height) + ";",
            "",
            "    // Matrix coefficients use 23 fractional bits.",
            "    localparam fixed_t NEURON_MATRIX [0:3][0:7] = '{",
        ]
    )

    for row_index, row in enumerate(fixed_matrix):
        comma = "," if row_index < len(fixed_matrix) - 1 else ""
        lines.append(format_array(row) + comma)

    lines.extend(
        [
            "    };",
            "",
            "    // Triangle states and slopes use Q16.16; Vmem threshold uses Q8.24.",
            f"    localparam fixed_t TRIANGLE_INITIAL_STATE_Q16 = {sv_signed(triangle_initial)};",
            f"    localparam fixed_t TRIANGLE_UPPER_BOUND_Q16 = {sv_signed(TRIANGLE_UPPER_BOUND_Q16)};",
            f"    localparam fixed_t TRIANGLE_SPIKE_THRESHOLD_Q24 = {sv_signed(triangle_threshold)};",
            "    // Rows: excitatory, inhibitory. Columns: Vmem above, below threshold.",
            "    localparam fixed_t TRIANGLE_SLOPE_MATRIX_Q16 [0:1][0:1] = '{",
        ]
    )

    for row_index, row in enumerate(triangle_slopes):
        comma = "," if row_index < len(triangle_slopes) - 1 else ""
        lines.append(format_array(row) + comma)

    lines.extend(
        [
            "    };",
            "",
            "    // Per-source synapse signals. Channel 0 is excitatory; 1 is inhibitory.",
            f"    localparam fixed_t SYNAPSE_TRIANGLE_SCALE_Q24 = {sv_signed(SYNAPSE_TRIANGLE_SCALE_Q24)};",
            "    localparam fixed_t SYNAPSE_GATE_OFFSET_Q16 [0:1] = "
            + format_array(SYNAPSE_GATE_OFFSETS_Q16, "") + ";",
            f"    localparam fixed_t SYNAPSE_EFFECTIVE_COUPLING_Q24 = {sv_signed(SYNAPSE_EFFECTIVE_COUPLING_Q24)};",
            "    localparam fixed_t SYNAPSE_EXP_BIAS_Q24 [0:1] = "
            + format_array(synapse_exp_biases, "") + ";",
            f"    localparam fixed_t SYNAPSE_EXCITATORY_SCALE_Q8 = {sv_signed(SYNAPSE_EXCITATORY_SCALE_Q8)};",
            f"    localparam fixed_t SYNAPSE_INHIBITORY_VMEM_OFFSET_Q24 = {sv_signed(inhibitory_vmem_offset)};",
            "",
            "    // Fixed 3-neuron recurrent 1D synfire configuration.",
            f"    localparam int SYNFIRE_1D_3_NEURON_COUNT = {SYNFIRE_1D_3_NEURON_COUNT};",
            f"    localparam int SYNFIRE_1D_3_STEPS = {SYNFIRE_1D_3_STEPS};",
            f"    localparam int SYNFIRE_1D_3_PULSE_START = {SYNFIRE_1D_3_PULSE_START};",
            f"    localparam int SYNFIRE_1D_3_PULSE_END = {SYNFIRE_1D_3_PULSE_END};",
            f"    localparam int SYNFIRE_1D_3_INPUT_NEURON = {SYNFIRE_1D_3_INPUT_NEURON};",
            f"    localparam fixed_t SYNFIRE_1D_3_PULSE_HEIGHT_Q8 = {sv_signed(synfire_pulse_height)};",
            "    // Rows: receiving neuron. Column 2*n: source n excitatory channel;",
            "    // column 2*n+1: source n inhibitory channel. Zero means no link.",
            "    localparam fixed_t SYNFIRE_1D_3_SYNAPSE_COEFFICIENT_Q24 [0:2][0:5] = '{",
        ]
    )

    for row_index, row in enumerate(synapse_coefficients):
        comma = "," if row_index < len(synapse_coefficients) - 1 else ""
        lines.append(format_array(row) + comma)

    lines.extend(["    };", "", "endpackage", ""])

    return "\n".join(lines)


def main() -> None:
    """Write the generated package, or check that it is current."""

    parser = argparse.ArgumentParser(
        description="Generate the fixed-point FH neuron SystemVerilog package."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the generated package is missing or out of date.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    output_path = repo_root / "hdl" / "packages" / "neuron_params_generated_pkg.sv"
    generated_text = generate_package()

    if args.check:
        if not output_path.exists() or output_path.read_text(encoding="utf-8") != generated_text:
            raise SystemExit(
                "hdl/packages/neuron_params_generated_pkg.sv is out of date. "
                "Run: python scripts/generate_neuron_params.py"
            )
        print("hdl/packages/neuron_params_generated_pkg.sv is up to date.")
        return

    output_path.write_text(generated_text, encoding="utf-8")
    print(f"Wrote {output_path.relative_to(repo_root)}")


if __name__ == "__main__":
    main()
