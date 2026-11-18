import argparse
import concurrent.futures
import csv
import hashlib
import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path

import generate_designs
import summarize_results


DIRECTORY = Path(__file__).resolve().parent
PROJECT = DIRECTORY.parents[1]
WORKER_STATE = threading.local()
WORKER_SESSIONS = []
WORKER_LOCK = threading.Lock()


class VivadoSession:
    def __init__(self, arguments):
        self.directory = DIRECTORY / "results/_work/workers" / f"{os.getpid()}_{threading.get_ident()}"
        self.directory.mkdir(parents=True, exist_ok=True)
        self.log = (self.directory / "console.log").open("w")
        self.process = subprocess.Popen([str(arguments.vivado_bin / "vivado.bat"), "-mode", "batch", "-nojournal", "-nolog", "-source", str(DIRECTORY / "serve_designs.tcl"), "-tclargs", str(self.directory)], cwd=self.directory, stdout=self.log, stderr=subprocess.STDOUT)
        with WORKER_LOCK:
            WORKER_SESSIONS.append(self)

    def implement(self, definition, arguments, directory):
        console_path = self.directory / "console.log"
        start_position = console_path.stat().st_size
        values = (definition["name"], definition["implementation"], 1000 / arguments.clock_mhz, arguments.part, directory)
        def quoted(value):
            return "{" + str(value).replace("\\", "/").replace("{", "\\{").replace("}", "\\}") + "}"
        status = self.directory / "status.txt"
        status.unlink(missing_ok=True)
        temporary = self.directory / "pending.tcl"
        temporary.write_text("set argv [list " + " ".join(quoted(value) for value in values) + "]\nset worker_task_log " + quoted(directory / "vivado_console.log") + "\n")
        temporary.replace(self.directory / "task.tcl")
        while not status.exists():
            if self.process.poll() is not None:
                raise RuntimeError(f"Vivado worker exited; see {self.directory / 'console.log'}")
            time.sleep(0.2)
        lines = status.read_text().splitlines()
        (directory / "vivado_console.log").write_bytes(console_path.read_bytes()[start_position:])
        if not lines or lines[0] != "PASS":
            raise RuntimeError(f"Vivado implementation failed: {' '.join(lines[1:])}; see {directory / 'vivado_console.log'}")

    def close(self):
        if self.process.poll() is None:
            (self.directory / "stop.txt").write_text("stop\n")
            self.process.wait()
        self.log.close()


def run_tool(arguments, working_directory, log_path):
    working_directory.mkdir(parents=True, exist_ok=True)
    with log_path.open("w") as output:
        completed = subprocess.run([str(argument) for argument in arguments], cwd=working_directory, stdout=output, stderr=subprocess.STDOUT)
    if completed.returncode:
        tail = "\n".join(log_path.read_text(errors="replace").splitlines()[-18:])
        raise RuntimeError(f"Tool failed; see {log_path}\n{tail}")


def configuration():
    source = PROJECT / "ip/scalable_digital_neurons/build/build.srcs/sources_1/ip/signed_multiplier/signed_multiplier.xci"
    instance = json.loads(source.read_text())["ip_inst"]
    parameters = instance["parameters"]["component_parameters"]
    names = ("MultType", "PortAType", "PortAWidth", "PortBType", "PortBWidth", "Multiplier_Construction", "OptGoal", "Use_Custom_Output_Width", "PipeStages", "ClockEnable", "SyncClear")
    values = {name: parameters[name][0]["value"] for name in names}
    if values["PipeStages"] != "6" or values["PortAWidth"] != "32" or values["PortBWidth"] != "32":
        raise ValueError("The research pipeline requires the user's six-stage signed 32-by-32 multiplier configuration.")
    (DIRECTORY / "multiplier_configuration.tcl").write_text("set_property -dict [list " + " ".join(f"CONFIG.{name} {{{value}}}" for name, value in values.items()) + "] [get_ips signed_multiplier]\n")
    return source, values


def validate(binary_directory, vendor_model=None):
    working = DIRECTORY / "results/_work" / ("validation_" + (vendor_model or "functional"))
    working.mkdir(parents=True, exist_ok=True)
    for name in ("memory", "validation"):
        target = working / name
        target.mkdir(exist_ok=True)
        for source in (DIRECTORY / name).glob("*.mem"):
            (target / source.name).write_bytes(source.read_bytes())
    packages = PROJECT / "ip/scalable_digital_neurons/hdl/packages"
    sources = [packages / name for name in ("neuron_params_generated_pkg.sv", "neuron_params_pkg.sv", "fixed_point_package.sv")]
    sources += [PROJECT / "ip/scalable_digital_neurons/hdl/math/signed_32_32_multiplication.sv"]
    if vendor_model:
        ip_path = Path((DIRECTORY / "results/_work/multiplier_ip" / vendor_model / "ip_path.txt").read_text().strip())
        candidates = list((DIRECTORY / "results/_work/multiplier_ip" / vendor_model).rglob("sim/signed_multiplier.vhd"))
        if len(candidates) != 1:
            raise RuntimeError("Could not identify the generated multiplier simulation model.")
        model = candidates[0]
        run_tool([binary_directory / "xvhdl.bat", model], working, working / "vhdl.log")
    else:
        sources += [PROJECT / "ip/scalable_digital_neurons/sim/common/signed_multiplier_functional.sv"]
    sources += [DIRECTORY / "rtl/fractional_models.sv"]
    sources += sorted(path for path in (DIRECTORY / "rtl").glob("*.sv") if path.name != "fractional_models.sv")
    if vendor_model:
        manifest = json.loads((DIRECTORY / "design_manifest.json").read_text())
        definitions = [value for value in manifest["designs"] if value["implementation"] == vendor_model]
        cycle_count = len((DIRECTORY / "validation/stimulus.mem").read_text().splitlines())
        lines = ["module comparison_testbench;", "    logic clock = 0;", "    logic reset;", "    logic [23:0] fractional_exponent;", "    logic input_valid;", f"    logic [25:0] stimulus [0:{cycle_count-1}];", "    integer checked_outputs = 0;", "    always begin", "        #2;", "        clock = ~clock;", "    end"]
        for position, definition in enumerate(definitions):
            lines += [f"    logic signed [31:0] result_{position};", f"    logic output_valid_{position};", f"    logic [32:0] expected_{position} [0:{cycle_count-1}];", f"    {definition['name']} instance_{position} (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_{position}), .output_valid(output_valid_{position}));"]
        lines += ["    initial begin", '        $readmemh("validation/stimulus.mem", stimulus);']
        for position, definition in enumerate(definitions):
            lines += [f'        $readmemh("validation/{definition["name"]}.mem", expected_{position});']
        lines += [f"        for (integer cycle = 0; cycle < {cycle_count}; cycle = cycle + 1) begin", "            @(negedge clock);", "            {reset, input_valid, fractional_exponent} = stimulus[cycle];", "            @(posedge clock);", "            #0.1;"]
        for position, definition in enumerate(definitions):
            lines += [f"            if (output_valid_{position} !== expected_{position}[cycle][32]) begin", f'                $fatal(1, "{definition["name"]} valid mismatch at cycle %0d", cycle);', "            end", f"            if (expected_{position}[cycle][32]) begin", f"                if (result_{position} !== expected_{position}[cycle][31:0]) begin", f'                    $fatal(1, "{definition["name"]} result mismatch at cycle %0d", cycle);', "                end", "                checked_outputs = checked_outputs + 1;", "            end"]
        lines += ["        end", '        $display("PASS: all models matched Python; checked outputs=%0d", checked_outputs);', "        $finish;", "    end", "endmodule", ""]
        testbench_path = working / "comparison_testbench.sv"
        testbench_path.write_text("\n".join(lines))
    else:
        testbench_path = DIRECTORY / "validation/comparison_testbench.sv"
    sources += [testbench_path]
    run_tool([binary_directory / "xvlog.bat", "-sv", *sources], working, working / "compile.log")
    libraries = ["-L", "mult_gen_v12_0_25"] if vendor_model else []
    run_tool([binary_directory / "xelab.bat", *libraries, "comparison_testbench", "-s", "comparison_simulation", "-timescale", "1ns/1ps"], working, working / "elaborate.log")
    run_tool([binary_directory / "xsim.bat", "comparison_simulation", "-runall"], working, working / "simulate.log")
    if "PASS: all models matched Python" not in (working / "simulate.log").read_text():
        raise RuntimeError(f"Validation did not complete: {working / 'simulate.log'}")
    (working / "validation_result.json").write_text(json.dumps({"status": "PASS", "multiplier_model": vendor_model or "functional", "input_fractional_bits": 24, "output_fractional_bits": 24, "output_total_bits": 32, "checked_designs": len(definitions) if vendor_model else 47, "test": "Exact output integers, pipeline validity, reset and bubbles against the Q24 Python models"}, indent=2))
    print(f"PASS: all designs matched Python using the {vendor_model or 'functional'} multiplier model.", flush=True)


def build_signature(definition, clock_mhz, part):
    digest = hashlib.sha256()
    for source in [DIRECTORY / "implement_design.tcl", DIRECTORY / "prepare_multiplier.tcl", DIRECTORY / "rtl/fractional_models.sv", DIRECTORY / "rtl" / (definition["name"] + ".sv"), DIRECTORY / "multiplier_configuration.tcl", PROJECT / "ip/scalable_digital_neurons/hdl/math/signed_32_32_multiplication.sv", *sorted((DIRECTORY / "memory").glob("*.mem"))]:
        digest.update(source.read_bytes())
    clock_mhz = int(clock_mhz) if float(clock_mhz).is_integer() else clock_mhz
    digest.update(json.dumps({"definition": definition, "part": part, "clock_mhz": clock_mhz}, sort_keys=True).encode())
    return digest.hexdigest()


def implementation_report(definition, arguments):
    directory = DIRECTORY / "results" / f"{arguments.clock_mhz:g}MHz" / "reports" / definition["name"]
    signature = build_signature(definition, arguments.clock_mhz, arguments.part)
    signature_path = directory / "build_signature.txt"
    reusable = (directory / "timing_metrics.csv").is_file() and signature_path.exists() and signature_path.read_text().strip() == signature
    if not arguments.resume or not reusable:
        print(f"Building {definition['name']} at {arguments.clock_mhz:g} MHz.", flush=True)
        directory.mkdir(parents=True, exist_ok=True)
        if arguments.separate_processes:
            run_tool([arguments.vivado_bin / "vivado.bat", "-mode", "batch", "-nojournal", "-nolog", "-source", DIRECTORY / "implement_design.tcl", "-tclargs", definition["name"], definition["implementation"], 1000 / arguments.clock_mhz, arguments.part, directory], directory, directory / "vivado_console.log")
        else:
            session = getattr(WORKER_STATE, "session", None)
            if session is None or session.process.poll() is not None:
                session = VivadoSession(arguments)
                WORKER_STATE.session = session
            session.implement(definition, arguments, directory)
        signature_path.write_text(signature + "\n")
    return read_implementation_report(definition, arguments, directory)


def read_implementation_report(definition, arguments, directory):
    with (directory / "timing_metrics.csv").open() as source:
        timing = next(csv.DictReader(source))
    text = (directory / "synthesis_utilization.rpt").read_text()
    def resource(label):
        matched = re.search(r"\|\s*" + re.escape(label) + r"\s*\*?\s*\|\s*([\d,.]+)", text)
        if matched is None:
            raise ValueError(f"Missing synthesis resource {label}: {directory}")
        return matched.group(1).replace(",", "")
    row = {key: definition[key] for key in ("name", "model", "implementation", "latency_cycles", "register_stages")}
    row.update({"input_fractional_bits": 24, "output_fractional_bits": 24, "output_total_bits": 32, "output_signed": True, "clock_mhz": arguments.clock_mhz, "initiation_interval_cycles": 1, "latency_ns": definition["latency_cycles"] * 1000 / arguments.clock_mhz, "logic_luts": resource("LUT as Logic"), "memory_luts": resource("LUT as Memory"), "total_luts": resource("Slice LUTs"), "flip_flops": resource("Slice Registers"), "bram_tiles": resource("Block RAM Tile"), **timing})
    row.update({"dsp_cells": resource("DSPs"), "ram18_cells": resource("RAMB18"), "ram36_cells": resource("RAMB36/FIFO"), "resource_stage": "post_synthesis", "timing_stage": "post_route"})
    row["timing_pass"] = bool(timing["setup_slack_ns"] and float(timing["setup_slack_ns"]) >= 0 and timing["hold_slack_ns"] and float(timing["hold_slack_ns"]) >= 0)
    row["estimated_frequency_mhz_from_slack"] = 1000 / (1000 / arguments.clock_mhz - float(timing["setup_slack_ns"])) if timing["setup_slack_ns"] and 1000 / arguments.clock_mhz > float(timing["setup_slack_ns"]) else ""
    row["mapping_matches_request"] = not ((definition["implementation"] == "lut" and int(row["dsp_cells"]) != 0) or (definition["implementation"] == "dsp" and int(row["dsp_cells"]) == 0) or (definition["implementation"] == "block" and int(row["ram18_cells"]) + int(row["ram36_cells"]) == 0) or (definition["implementation"] == "distributed" and int(row["ram18_cells"]) + int(row["ram36_cells"]) != 0))
    summary = directory.parents[1] / "tables/accuracy_reference/accuracy_summary.csv"
    if not summary.exists():
        raise FileNotFoundError(f"Missing matching accuracy snapshot: {summary}")
    if summary.exists():
        accuracy_configuration = json.loads((summary.parent / "run_configuration.json").read_text())
        if accuracy_configuration["output_fractional_bits"] != 24 or accuracy_configuration["input_fractional_bits"] != 24 or accuracy_configuration.get("output_total_bits") != 32 or not accuracy_configuration.get("output_signed"):
            raise ValueError("FPGA results require matching signed 32-bit Q24 accuracy results.")
        with summary.open() as source:
            accuracy_rows = [value for value in csv.DictReader(source) if value["domain"] == "hardware_fractional" and value["model"] == definition["model"]]
        uniform = next((value for value in accuracy_rows if value["population"] == "uniform"), None)
        row["maximum_absolute_error"] = max((float(value["maximum_absolute_error"]) for value in accuracy_rows), default="")
        row["mean_absolute_error"] = uniform["mean_absolute_error"] if uniform else ""
    return row


def verify_accuracy_source():
    directory = DIRECTORY.parent / "exponential_accuracy/results"
    settings = json.loads((directory / "run_configuration.json").read_text())
    if settings["input_fractional_bits"] != 24 or settings["output_fractional_bits"] != 24 or settings.get("output_total_bits") != 32 or not settings.get("output_signed"):
        raise ValueError("Run the signed 32-bit Q24 accuracy comparison before measuring FPGA designs.")
    with (directory / "accuracy_summary.csv").open() as source:
        available = {(row["model"], row["population"]) for row in csv.DictReader(source) if row["domain"] == "hardware_fractional"}
    required = {"linear", "cubic", *[f"maclaurin_{degree}" for degree in range(5)], *[f"sollya_{degree}" for degree in range(5)], *[f"bram_{size}" for size in generate_designs.accuracy_comparison.DEFAULT_BRAM_SIZES]}
    if any((model, population) not in available for model in required for population in ("uniform", "directed_boundaries")):
        raise ValueError("Accuracy results must cover every default model and ROM size, including uniform and boundary populations.")
    return directory


def snapshot_accuracy(output):
    source = verify_accuracy_source()
    destination = output / "tables/accuracy_reference"
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("accuracy_summary.csv", "run_configuration.json"):
        target = destination / name
        data = (source / name).read_bytes()
        if target.exists() and target.read_bytes() != data:
            raise ValueError("Saved accuracy results changed during this measurement campaign. Use a fresh results directory or restore its accuracy reference.")
        target.write_bytes(data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--clock-mhz", type=float, default=250)
    parser.add_argument("--part", default="xc7z020clg400-1")
    parser.add_argument("--vivado-bin", type=Path, default=Path("C:/AMDDesignTools/2026.1/Vivado/bin"))
    parser.add_argument("--models", nargs="+")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--generate-only", action="store_true")
    parser.add_argument("--skip-validation", action="store_true")
    parser.add_argument("--separate-processes", action="store_true")
    arguments = parser.parse_args()
    if arguments.clock_mhz <= 0 or arguments.jobs < 1:
        parser.error("Clock frequency and job count must be positive.")
    if not arguments.generate_only:
        verify_accuracy_source()
    generate_designs.generate()
    source, values = configuration()
    if arguments.generate_only:
        return
    if not arguments.skip_validation:
        validate(arguments.vivado_bin)
    if arguments.validate_only:
        return
    manifest = json.loads((DIRECTORY / "design_manifest.json").read_text())
    definitions = [value for value in manifest["designs"] if arguments.models is None or value["name"] in arguments.models]
    if arguments.models and set(arguments.models) != {value["name"] for value in definitions}:
        parser.error("Unknown design name. See design_manifest.json for the available names.")
    for implementation in sorted({value["implementation"] for value in definitions} & {"lut", "dsp"}):
        directory = DIRECTORY / "results/_work/multiplier_ip" / implementation
        directory.mkdir(parents=True, exist_ok=True)
        cache_signature = hashlib.sha256(json.dumps({"part": arguments.part, "configuration": values, "implementation": implementation}, sort_keys=True).encode() + (DIRECTORY / "prepare_multiplier.tcl").read_bytes()).hexdigest()
        cache_signature_path = directory / "configuration_signature.txt"
        ip_record = directory / "ip_path.txt"
        reusable = ip_record.exists() and Path(ip_record.read_text().strip()).exists() and cache_signature_path.exists() and cache_signature_path.read_text().strip() == cache_signature
        if not arguments.resume or not reusable:
            print(f"Preparing the user's multiplier with {implementation.upper()} implementation.", flush=True)
            run_tool([arguments.vivado_bin / "vivado.bat", "-mode", "batch", "-nojournal", "-nolog", "-source", DIRECTORY / "prepare_multiplier.tcl", "-tclargs", implementation, arguments.part], directory, directory / "prepare.log")
            cache_signature_path.write_text(cache_signature + "\n")
        if not arguments.skip_validation:
            validate(arguments.vivado_bin, implementation)
    output = DIRECTORY / "results" / f"{arguments.clock_mhz:g}MHz"
    output.mkdir(parents=True, exist_ok=True)
    snapshot_accuracy(output)
    (output / "run_configuration.json").write_text(json.dumps({"part": arguments.part, "clock_mhz": arguments.clock_mhz, "clock_uncertainty_ns": 0.1, "vivado_bin": str(arguments.vivado_bin), "source_multiplier": str(source), "source_multiplier_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "multiplier_configuration": values, "input_fractional_bits": 24, "output_fractional_bits": 24, "output_total_bits": 32, "output_signed": True, "jobs": arguments.jobs, "resource_stage": "post_synthesis", "timing_stage": "post_route"}, indent=2) + "\n")
    previous_path = output / "tables/resource_comparison.csv"
    selected_names = {definition["name"] for definition in definitions}
    if previous_path.exists():
        with previous_path.open() as previous:
            rows = [row for row in csv.DictReader(previous) if row["name"] not in selected_names]
    else:
        rows = []
    failures = []
    (output / "tables").mkdir(exist_ok=True)
    start = time.monotonic()
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=arguments.jobs)
    futures = {}
    try:
        futures = {executor.submit(implementation_report, value, arguments): value for value in definitions}
        for future in concurrent.futures.as_completed(futures):
            definition = futures[future]
            try:
                row = future.result()
                rows.append(row)
                print(f"Completed {definition['name']}: timing={'PASS' if row['timing_pass'] else 'FAIL'}, LUTs={row['total_luts']}, DSPs={row['dsp_cells']}, BRAM tiles={row['bram_tiles']} ({time.monotonic() - start:.0f}s).", flush=True)
            except Exception as error:
                failures.append({"name": definition["name"], "error": str(error)})
                print(f"FAILED {definition['name']}: {error}", flush=True)
            if rows:
                with (output / "tables/resource_comparison.csv").open("w", newline="") as target:
                    writer = csv.DictWriter(target, fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows(sorted(rows, key=lambda value: value["name"]))
            (output / "failures.json").write_text(json.dumps(failures, indent=2) + "\n")
    except KeyboardInterrupt:
        for future in futures:
            future.cancel()
        for session in WORKER_SESSIONS:
            if session.process.poll() is None:
                session.process.terminate()
        print("Interrupted. Completed reports are saved; rerun with --resume to continue.", flush=True)
        raise
    finally:
        executor.shutdown(wait=True, cancel_futures=True)
        for session in WORKER_SESSIONS:
            session.close()
    if rows:
        from collect_results import collect
        rows = collect(arguments.clock_mhz)
        if rows:
            summarize_results.summarize(output)
    print(f"Completed {len(rows)} builds; {len(failures)} tool failures. Results: {output}", flush=True)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
