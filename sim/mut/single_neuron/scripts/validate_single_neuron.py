"""Compare completed RTL neuron steps with the fixed-point C reference.

Run from any directory. GCC must be on PATH. Vivado's simulator is found on
PATH, in common Windows install locations, or through --vivado-bin. Generated
files stay under build/ by default.
"""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import subprocess
from itertools import zip_longest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = Path(__file__).resolve().parent
IMAGE_DIR = ROOT / "sim" / "mut" / "single_neuron" / "images"
FIELDS = ("step", "current", "vmem", "vk", "vg", "vna")


def run(command: list[str], directory: Path) -> None:
    print("Running:", " ".join(command), flush=True)
    subprocess.run(command, cwd=directory, check=True)


def simulator_tool(name: str, vivado_bin: Path | None) -> str | None:
    if vivado_bin is not None:
        return shutil.which(name, path=str(vivado_bin))
    return shutil.which(name)


def find_vivado_bin(requested: Path | None) -> Path | None:
    if requested is not None:
        return requested
    if all(shutil.which(name) for name in ("xvlog", "xelab", "xsim")):
        return None

    for base in (Path("C:/AMDDesignTools"), Path("C:/Xilinx"), Path("C:/AMD")):
        for candidate in sorted(base.glob("*/Vivado/bin"), reverse=True):
            if all(simulator_tool(name, candidate) for name in
                   ("xvlog", "xelab", "xsim")):
                print("Found Vivado simulator:", candidate)
                return candidate
    return None


def input_values(args: argparse.Namespace) -> list[int]:
    if args.input_values is not None:
        values = [int(line.strip()) for line in args.input_values.read_text().splitlines()
                  if line.strip() and not line.lstrip().startswith("#")]
    else:
        if args.steps <= 0 or args.pulse_start < 0:
            raise ValueError("--steps must be positive and --pulse-start nonnegative")
        values = [0 if step < args.pulse_start else args.pulse_height_q8
                  for step in range(args.steps)]

    if not values:
        raise ValueError("The stimulus must contain at least one step")
    if any(value < -(1 << 31) or value >= (1 << 31) for value in values):
        raise ValueError("Every input current must fit in a signed 32-bit integer")
    return values


def write_stimulus(path: Path, values: list[int]) -> None:
    with path.open("w", newline="\n") as output:
        output.write(f"{len(values)}\n")
        for value in values:
            output.write(f"{value}\n")


def generate_reference(directory: Path, gcc: str, stimulus: Path,
                       wide_reference: bool) -> Path:
    executable = directory / ("single_neuron_reference.exe" if os.name == "nt" else
                              "single_neuron_reference")
    reference = directory / "c_trace.csv"
    compile_command = [gcc, "-std=c11", "-O2", "-Wall", "-Wextra", "-fwrapv"]
    if wide_reference:
        compile_command.append("-DWIDE_MUL=1")
    compile_command.extend([str(SCRIPT_DIR / "single_neuron_reference.c"),
                            "-o", str(executable)])
    run(compile_command, directory)
    run([str(executable), str(stimulus), str(reference)], directory)
    return reference


def run_simulator(directory: Path, vivado_bin: Path | None) -> None:
    tools = {name: simulator_tool(name, vivado_bin)
             for name in ("xvlog", "xelab", "xsim")}
    missing = [name for name, path in tools.items() if path is None]
    if missing:
        raise RuntimeError(
            "Vivado simulator tools unavailable: " + ", ".join(missing) +
            ". Add Vivado's bin directory to PATH, pass --vivado-bin, "
            "or use --reference-only and run the testbench in Vivado manually."
        )

    source_names = (
        "packages/neuron_params_generated_pkg.sv",
        "packages/neuron_params_pkg.sv",
        "packages/fixed_point_package.sv",
        "math/base_two_exponential_pipe_linear.sv",
        "math/base_two_exponential_pipe_cubic.sv",
        "math/compute_current_vector.sv",
        "math/matrix_mul_and_euler_update.sv",
        "neuron/single_neuron.sv",
    )
    sources = [str(ROOT / "hdl" / name) for name in source_names]
    sources.append(str(ROOT / "sim" / "mut" / "single_neuron" / "tb_single_neuron.sv"))

    run([tools["xvlog"], "-sv", "--relax", *sources], directory)
    run([tools["xelab"], "tb_single_neuron", "-s", "tb_single_neuron_sim"], directory)
    run([tools["xsim"], "tb_single_neuron_sim", "-runall"], directory)


def compare(reference: Path, hdl: Path) -> bool:
    with reference.open(newline="") as expected_file, hdl.open(newline="") as actual_file:
        expected_rows = csv.DictReader(expected_file)
        actual_rows = csv.DictReader(actual_file)
        if tuple(expected_rows.fieldnames or ()) != FIELDS:
            raise ValueError(f"Unexpected reference columns in {reference}")
        if tuple(actual_rows.fieldnames or ()) != FIELDS:
            raise ValueError(f"Unexpected HDL columns in {hdl}")

        first_difference: str | None = None
        differences = 0
        row_count = 0
        for row_count, (expected, actual) in enumerate(
            zip_longest(expected_rows, actual_rows), start=1
        ):
            if expected is None or actual is None:
                differences += 1
                if first_difference is None:
                    first_difference = (
                        f"trace length differs at row {row_count}: "
                        f"C row={expected is not None}, HDL row={actual is not None}"
                    )
                continue

            for field in FIELDS:
                try:
                    expected_value = int(expected[field])
                    actual_value = int(actual[field])
                except (KeyError, TypeError, ValueError) as error:
                    raise ValueError(f"Invalid {field} at trace row {row_count}") from error
                if expected_value != actual_value:
                    differences += 1
                    if first_difference is None:
                        first_difference = (
                            f"step {expected['step']}, {field}: "
                            f"C={expected_value}, HDL={actual_value}, "
                            f"difference={actual_value - expected_value}"
                        )

    if row_count == 0:
        raise ValueError("The traces contain no completed neuron steps")
    if differences:
        print(f"FAIL: {differences} differing values across {row_count} trace rows")
        print("First difference:", first_difference)
        return False
    print(f"PASS: all {row_count} completed steps match the C reference exactly")
    return True


def plot_voltages(reference: Path, hdl: Path, destination: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError as error:
        raise RuntimeError("Install matplotlib to use --plot") from error

    def trace(path: Path) -> tuple[list[int], list[float]]:
        with path.open(newline="") as source:
            rows = csv.DictReader(source)
            steps, volts = [], []
            for row in rows:
                steps.append(int(row["step"]))
                volts.append(int(row["vmem"]) / (1 << 24))
            return steps, volts

    c_steps, c_voltage = trace(reference)
    hdl_steps, hdl_voltage = trace(hdl)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(c_steps, c_voltage, label="C reference", linewidth=1.5)
    ax.plot(hdl_steps, hdl_voltage, label="HDL", linewidth=1, linestyle="--")
    ax.set(xlabel="Completed neuron step", ylabel="Vmem (Q24 converted to real)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(destination, dpi=160)
    plt.close(fig)
    print("Plot:", destination)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, default=100000,
                        help="Number of model steps (default: original C model's 100000)")
    parser.add_argument("--pulse-start", type=int, default=20000,
                        help="First step with nonzero input (default: 20000)")
    parser.add_argument("--pulse-height-q8", type=int, default=25600,
                        help="Signed Q8 input after pulse start (default: 100 pA)")
    parser.add_argument("--input-values", type=Path,
                        help="Optional file with one signed Q8 current per step")
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "build" / "single_neuron_validation")
    parser.add_argument("--gcc", default="gcc", help="C compiler (default: gcc)")
    parser.add_argument("--wide-reference", action="store_true",
                        help="Use 64-bit C products even when native long is 32 bits")
    parser.add_argument("--vivado-bin", type=Path,
                        help="Directory containing xvlog, xelab and xsim")
    parser.add_argument("--reference-only", action="store_true",
                        help="Create stimulus and C trace without running HDL simulation")
    parser.add_argument("--compare-only", action="store_true",
                        help="Compare existing C and HDL traces in --output-dir")
    parser.add_argument("--plot", action="store_true",
                        help="Save a Vmem plot after comparing the traces")
    args = parser.parse_args()

    if args.reference_only and args.compare_only:
        parser.error("--reference-only and --compare-only cannot be combined")

    directory = args.output_dir.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    stimulus = directory / "stimulus.txt"
    reference = directory / "c_trace.csv"
    hdl = directory / "hdl_trace.csv"

    try:
        if not args.compare_only:
            write_stimulus(stimulus, input_values(args))
            generate_reference(directory, args.gcc, stimulus, args.wide_reference)
            print("Stimulus:", stimulus)
            print("C trace:", reference)
            if args.reference_only:
                print("Run tb_single_neuron with this directory as the simulator working directory.")
                print("Then use --compare-only --output-dir", directory)
                return 0
            # Never compare a trace left by an earlier simulation run.
            if hdl.exists():
                hdl.unlink()
            run_simulator(directory, find_vivado_bin(args.vivado_bin))

        if not reference.is_file() or not hdl.is_file():
            raise FileNotFoundError("Both c_trace.csv and hdl_trace.csv are required")
        passed = compare(reference, hdl)
        if args.plot:
            IMAGE_DIR.mkdir(parents=True, exist_ok=True)
            plot_voltages(reference, hdl, IMAGE_DIR / "vmem_comparison.png")
        return 0 if passed else 1
    except (FileNotFoundError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(2, f"Validation could not complete: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
