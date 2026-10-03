"""Compare every completed three-neuron RTL network step with fixed-point C."""
from __future__ import annotations

import argparse
import csv
import os
import shutil
import subprocess
from itertools import zip_longest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
IMAGE_DIR = HERE.parent / "images"
FIELDS = ("step", "current", *(f"n{n}_{name}" for n in range(3)
          for name in ("vmem", "vk", "vg", "vna")),
          *(f"n{n}_{name}" for n in range(3) for name in ("te", "ti")))


def run(command: list[str], directory: Path) -> None:
    print("Running:", " ".join(command), flush=True)
    subprocess.run(command, cwd=directory, check=True)


def simulator_tools(requested: Path | None) -> dict[str, str]:
    names = ("xvlog", "xelab", "xsim")
    candidates = [requested] if requested else [None]
    if requested is None:
        for base in (Path("C:/AMDDesignTools"), Path("C:/Xilinx"), Path("C:/AMD")):
            candidates.extend(sorted(base.glob("*/Vivado/bin"), reverse=True))
    for candidate in candidates:
        found = {name: shutil.which(name, path=str(candidate)) if candidate
                 else shutil.which(name) for name in names}
        if all(found.values()):
            return found  # type: ignore[return-value]
    raise RuntimeError("Vivado xvlog, xelab and xsim are required; pass --vivado-bin")


def compare(expected: Path, actual: Path) -> bool:
    with expected.open(newline="") as source, actual.open(newline="") as result:
        c_rows, hdl_rows = csv.DictReader(source), csv.DictReader(result)
        if tuple(c_rows.fieldnames or ()) != FIELDS or tuple(hdl_rows.fieldnames or ()) != FIELDS:
            raise ValueError("Trace headers do not match the expected network fields")
        count = 0
        for count, (c_row, hdl_row) in enumerate(zip_longest(c_rows, hdl_rows), 1):
            if c_row is None or hdl_row is None:
                print(f"FAIL: trace length differs at row {count}")
                return False
            for field in FIELDS:
                c_value, hdl_value = int(c_row[field]), int(hdl_row[field])
                if c_value != hdl_value:
                    print(f"FAIL: step {count-1}, {field}: C={c_value}, HDL={hdl_value}, difference={hdl_value-c_value}")
                    return False
        if not count:
            raise ValueError("No network steps in the traces")
        print(f"PASS: all {count} steps and {len(FIELDS)-2} state values per step match exactly")
        return True


def plot_voltages(reference: Path, hdl: Path, destination: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as error:
        raise RuntimeError("Install matplotlib to use --plot") from error

    def read_trace(path: Path) -> tuple[list[int], list[float], list[list[float]]]:
        with path.open(newline="") as source:
            rows = csv.DictReader(source)
            steps, stimulus = [], []
            voltages = [[], [], []]
            for row in rows:
                steps.append(int(row["step"]))
                stimulus.append(int(row["current"]) / (1 << 8))
                for neuron in range(3):
                    voltages[neuron].append(int(row[f"n{neuron}_vmem"]) / (1 << 24))
        return steps, stimulus, voltages

    c_steps, currents, c_voltages = read_trace(reference)
    hdl_steps, _, hdl_voltages = read_trace(hdl)
    fig, axes = plt.subplots(4, 1, figsize=(11, 9), sharex=True,
                             gridspec_kw={"height_ratios": [2, 2, 2, 1]})
    for neuron in range(3):
        axes[neuron].plot(c_steps, c_voltages[neuron], label="C reference", linewidth=1.5)
        axes[neuron].plot(hdl_steps, hdl_voltages[neuron], label="HDL",
                          linewidth=1, linestyle="--")
        axes[neuron].set_ylabel(f"Neuron {neuron}\nVmem")
        axes[neuron].grid(True, alpha=0.3)
    axes[0].legend(loc="best")
    axes[3].plot(c_steps, currents, color="black", linewidth=1)
    axes[3].set_ylabel("Input\ncurrent")
    axes[3].set_xlabel("Completed network step")
    axes[3].grid(True, alpha=0.3)
    fig.suptitle("Three-neuron Vmem comparison")
    fig.tight_layout()
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination, dpi=160)
    plt.close(fig)
    print("Plot:", destination)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, default=190000)
    parser.add_argument("--pulse-start", type=int, default=60000)
    parser.add_argument("--pulse-end", type=int, default=140000)
    parser.add_argument("--pulse-height-q8", type=int, default=20480)
    parser.add_argument("--input-values", type=Path,
                        help="One signed Q8 external current per step, applied to neuron 0")
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "build" / "three_neurons_1D_validation")
    parser.add_argument("--gcc", default="gcc")
    reference_width = parser.add_mutually_exclusive_group()
    reference_width.add_argument("--wide-reference", dest="wide_reference",
                                 action="store_true", default=True,
                                 help="Use 64-bit C products to match RTL (default)")
    reference_width.add_argument("--native-reference", dest="wide_reference",
                                 action="store_false",
                                 help="Use native C long width (32-bit on Windows)")
    parser.add_argument("--vivado-bin", type=Path)
    parser.add_argument("--reference-only", action="store_true")
    parser.add_argument("--compare-only", action="store_true")
    parser.add_argument("--plot", action="store_true",
                        help="Save a C/HDL Vmem comparison PNG")
    args = parser.parse_args()
    if args.reference_only and args.compare_only:
        parser.error("--reference-only and --compare-only cannot be combined")
    directory = args.output_dir.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    stimulus, reference, hdl = (directory / name for name in
                                ("stimulus.txt", "c_trace.csv", "hdl_trace.csv"))
    try:
        if not args.compare_only:
            if args.input_values:
                values = [int(line) for line in args.input_values.read_text().splitlines()
                          if line.strip() and not line.lstrip().startswith("#")]
            else:
                if args.steps < 1 or args.pulse_start < 0 or args.pulse_end < args.pulse_start:
                    parser.error("Invalid step count or pulse interval")
                values = [args.pulse_height_q8 if args.pulse_start <= i <= args.pulse_end
                          else 0 for i in range(args.steps)]
            if not values or any(not -(1 << 31) <= v < (1 << 31) for v in values):
                raise ValueError("Stimulus must contain signed 32-bit values")
            stimulus.write_text(f"{len(values)}\n" + "\n".join(map(str, values)) + "\n")
            executable = directory / ("three_neurons_reference.exe" if os.name == "nt"
                                      else "three_neurons_reference")
            run([args.gcc, "-std=c11", "-O0", "-w", "-fwrapv",
                 *(["-DWIDE_MUL"] if args.wide_reference else []),
                 str(HERE / "three_neurons_reference.c"), "-lm", "-o", str(executable)], directory)
            run([str(executable), str(stimulus), str(reference)], directory)
            if args.reference_only:
                print("C trace:", reference)
                return 0
            hdl.unlink(missing_ok=True)
            tools = simulator_tools(args.vivado_bin)
            source_names = ("neuron_params_generated_pkg.sv", "neuron_params_pkg.sv",
                            "fixed_point_package.sv", "base_two_exponential_pipe_linear.sv",
                            "base_two_exponential_pipe_cubic.sv", "compute_current_vector.sv",
                            "matrix_mul_and_euler_update.sv", "single_neuron.sv",
                            "synaptic_triangular_generator.sv", "synaptic_pulse_generator.sv",
                            "neuron_with_pulse_generator.sv", "synapse.sv", "three_neurons_1D.sv")
            sources = [str(ROOT / "hdl" / name) for name in source_names]
            sources.append(str(HERE.parent / "tb_three_neurons_1D.sv"))
            run([tools["xvlog"], "-sv", "--relax", *sources], directory)
            run([tools["xelab"], "tb_three_neurons_1D", "-s", "tb_three_neurons_1D_sim"], directory)
            run([tools["xsim"], "tb_three_neurons_1D_sim", "-runall"], directory)
        if not reference.is_file() or not hdl.is_file():
            raise FileNotFoundError("Both c_trace.csv and hdl_trace.csv are required")
        passed = compare(reference, hdl)
        if args.plot:
            plot_voltages(reference, hdl, IMAGE_DIR / "vmem_comparison.png")
        return 0 if passed else 1
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(2, f"Validation could not complete: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
