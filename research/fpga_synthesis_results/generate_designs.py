import csv
import importlib.util
import json
from decimal import Decimal, localcontext
from pathlib import Path

import numpy


DIRECTORY = Path(__file__).resolve().parent
PROJECT = DIRECTORY.parents[1]
specification = importlib.util.spec_from_file_location("accuracy_comparison", DIRECTORY.parent / "exponential_accuracy/compare_base_two_exponential.py")
accuracy_comparison = importlib.util.module_from_spec(specification)
specification.loader.exec_module(accuracy_comparison)


def generate():
    for name in ("rtl", "memory", "validation"):
        (DIRECTORY / name).mkdir(exist_ok=True)
    definitions = []
    coefficients = {}
    for degree in range(5):
        with localcontext() as context:
            context.prec = 80
            logarithm = Decimal(2).ln()
            term = Decimal(1)
            values = [accuracy_comparison.INPUT_SCALE]
            for power in range(1, degree + 1):
                term = term * logarithm / power
                values.append(int((term * accuracy_comparison.INPUT_SCALE).to_integral_value()))
        coefficients[f"maclaurin_{degree}"] = values
        coefficients[f"sollya_{degree}"] = list(accuracy_comparison.SOLLYA_COEFFICIENTS[degree])
    for model, values in coefficients.items():
        degree = len(values) - 1
        for implementation in (("logic",) if degree == 0 else ("lut", "dsp")):
            definitions.append({"name": f"{model}_{implementation}", "model": model, "implementation": implementation, "kind": "polynomial", "degree": degree, "coefficients": values + [0] * (5 - len(values)), "latency_cycles": 1 + 8 * degree, "register_stages": 2 + 8 * degree})
    definitions.append({"name": "research_linear_logic", "model": "linear", "implementation": "logic", "kind": "linear", "latency_cycles": 1, "register_stages": 2})
    for implementation in ("lut", "dsp"):
        definitions.append({"name": f"research_cubic_{implementation}", "model": "cubic", "implementation": implementation, "kind": "cubic", "latency_cycles": 17, "register_stages": 18})
    for size in accuracy_comparison.DEFAULT_BRAM_SIZES:
        table = accuracy_comparison.make_table(size)
        (DIRECTORY / "memory" / f"rom_{size}.mem").write_text("".join(f"{int(value):07x}\n" for value in table))
        for implementation in ("distributed", "block"):
            definitions.append({"name": f"rom_{size}_{implementation}", "model": f"bram_{size}", "implementation": implementation, "kind": "rom", "entries": size, "latency_cycles": 2, "register_stages": 3})
    ports = """    input logic clock,
    input logic reset,
    input logic [23:0] fractional_exponent,
    input logic input_valid,
    output logic signed [31:0] result,
    output logic output_valid
"""
    connections = """        .clock(clock),
        .reset(reset),
        .fractional_exponent(fractional_exponent),
        .input_valid(input_valid),
        .result(result),
        .output_valid(output_valid)
"""
    for definition in definitions:
        kind = definition["kind"]
        if kind == "polynomial":
            parameters = [f".DEGREE({definition['degree']})"] + [f".COEFFICIENT_{position}(32'sd{value})" for position, value in enumerate(definition["coefficients"])]
            instance = "    fractional_polynomial #(\n        " + ",\n        ".join(parameters) + "\n    ) design_instance (\n" + connections + "    );\n"
        elif kind == "rom":
            instance = f"    fractional_rom #(.ADDRESS_BITS({definition['entries'].bit_length() - 1}), .MEMORY_STYLE(\"{definition['implementation']}\"), .MEMORY_FILE(\"memory/rom_{definition['entries']}.mem\")) design_instance (\n" + connections + "    );\n"
        else:
            instance = f"    fractional_research_{kind} design_instance (\n" + connections + "    );\n"
        (DIRECTORY / "rtl" / f"{definition['name']}.sv").write_text(f"module {definition['name']} (\n{ports});\n\n{instance}\nendmodule\n")
    (DIRECTORY / "design_manifest.json").write_text(json.dumps({"part": "xc7z020clg400-1", "clock_mhz": 250, "input_fractional_bits": 24, "output_fractional_bits": 24, "input_total_bits": 24, "output_total_bits": 32, "output_signed": True, "research_cubic_variant": "Q24 linear term and Q24 correction", "initiation_interval_cycles": 1, "designs": definitions}, indent=2) + "\n")
    generator = numpy.random.default_rng(250)
    boundaries = numpy.arange(65536, dtype=numpy.int64) * 256
    directed = numpy.concatenate((boundaries, numpy.maximum(0, boundaries - 1), numpy.minimum((1 << 24) - 1, boundaries + 1)))
    inputs = numpy.unique(numpy.concatenate((numpy.arange(0, 1 << 24, 4096), directed[::17], generator.integers(0, 1 << 24, 4096), [0, 1, (1 << 24) - 1])))
    resets = numpy.zeros(len(inputs) + 160, dtype=numpy.int64)
    resets[:4] = 1
    resets[503:506] = 1
    resets[2049:2051] = 1
    encoded = numpy.zeros_like(resets)
    encoded[4:4 + len(inputs)] = inputs
    valid = numpy.zeros_like(resets)
    valid[4:4 + len(inputs)] = 1
    valid[numpy.arange(len(valid)) % 13 == 0] = 0
    valid[resets == 1] = 0
    (DIRECTORY / "validation" / "stimulus.mem").write_text("".join(f"{(int(reset) << 25) | (int(accepted) << 24) | int(value):07x}\n" for reset, accepted, value in zip(resets, valid, encoded)))
    testbench = ["module comparison_testbench;", "    logic clock = 0;", "    logic reset;", "    logic [23:0] fractional_exponent;", "    logic input_valid;", f"    logic [25:0] stimulus [0:{len(encoded) - 1}];", "    integer checked_outputs = 0;", "", "    always begin", "        #2;", "        clock = ~clock;", "    end", ""]
    for position, definition in enumerate(definitions):
        name = definition["name"]
        model = definition["model"]
        predictions = accuracy_comparison.fractional_fixed_point(model, encoded, accuracy_comparison.make_table(definition["entries"]) if definition["kind"] == "rom" else None)
        latency = definition["latency_cycles"]
        expected = numpy.zeros(len(encoded), dtype=numpy.int64)
        for cycle in range(len(encoded)):
            source_cycle = cycle - latency
            if source_cycle >= 0 and valid[source_cycle] and not numpy.any(resets[source_cycle:cycle + 1]):
                expected[cycle] = (1 << 32) | (int(predictions[source_cycle]) & 0xFFFFFFFF)
        (DIRECTORY / "validation" / f"{name}.mem").write_text("".join(f"{int(value):09x}\n" for value in expected))
        testbench += [f"    logic signed [31:0] result_{position};", f"    logic output_valid_{position};", f"    logic [32:0] expected_{position} [0:{len(encoded) - 1}];", f"    {name} instance_{position} (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_{position}), .output_valid(output_valid_{position}));", ""]
    testbench += ["    initial begin", "        $readmemh(\"validation/stimulus.mem\", stimulus);"]
    for position, definition in enumerate(definitions):
        testbench += [f"        $readmemh(\"validation/{definition['name']}.mem\", expected_{position});"]
    testbench += [f"        for (integer cycle = 0; cycle < {len(encoded)}; cycle = cycle + 1) begin", "            @(negedge clock);", "            {reset, input_valid, fractional_exponent} = stimulus[cycle];", "            @(posedge clock);", "            #0.1;"]
    for position, definition in enumerate(definitions):
        testbench += [f"            if (output_valid_{position} !== expected_{position}[cycle][32]) begin", f"                $fatal(1, \"{definition['name']} valid mismatch at cycle %0d\", cycle);", "            end", f"            if (expected_{position}[cycle][32]) begin", f"                if (result_{position} !== expected_{position}[cycle][31:0]) begin", f"                    $fatal(1, \"{definition['name']} result mismatch at cycle %0d: actual=%0d expected=%0d\", cycle, result_{position}, expected_{position}[cycle][31:0]);", "                end", "                checked_outputs = checked_outputs + 1;", "            end"]
    testbench += ["        end", '        $display("PASS: all models matched Python, including bubbles and reset; checked outputs=%0d", checked_outputs);', "        $finish;", "    end", "endmodule", ""]
    (DIRECTORY / "validation" / "comparison_testbench.sv").write_text("\n".join(testbench))
    print(f"Generated {len(definitions)} designs and {len(encoded):,} validation cycles.")


if __name__ == "__main__":
    generate()
