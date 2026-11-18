import argparse
import csv
import json
import re
from pathlib import Path
from types import SimpleNamespace

import run_comparison


DIRECTORY = Path(__file__).resolve().parent


def collect(clock_mhz=250, require_complete=False):
    manifest = json.loads((DIRECTORY / "design_manifest.json").read_text())
    output = DIRECTORY / "results" / f"{clock_mhz:g}MHz"
    if not (output / "run_configuration.json").exists():
        raise FileNotFoundError("No Q24 measurements exist at this clock yet. Run run_comparison.py first.")
    settings = json.loads((output / "run_configuration.json").read_text())
    if manifest["output_fractional_bits"] != 24 or settings.get("output_fractional_bits") != 24:
        raise ValueError("Only matching Q24 measurements can be collected here.")
    arguments = SimpleNamespace(clock_mhz=clock_mhz, part=settings["part"])
    (output / "tables").mkdir(exist_ok=True)
    rows = []
    synthesis_rows = []
    missing = []
    for definition in manifest["designs"]:
        directory = output / "reports" / definition["name"]
        signature_path = directory / "build_signature.txt"
        if not signature_path.exists() or signature_path.read_text().strip() != run_comparison.build_signature(definition, clock_mhz, arguments.part):
            missing.append(definition["name"])
            continue
        synthesis_path = directory / "synthesis_utilization.rpt"
        if synthesis_path.is_file():
            synthesis_text = synthesis_path.read_text()
            synthesis_row = {"name": definition["name"]}
            for field, label in (("luts", "Slice LUTs"), ("registers", "Slice Registers"), ("dsps", "DSPs"), ("bram_tiles", "Block RAM Tile")):
                resource = re.search(r"\|\s*" + re.escape(label) + r"\s*\*?\s*\|\s*([\d,.]+)", synthesis_text)
                synthesis_row[field] = resource.group(1).replace(",", "") if resource else ""
            synthesis_rows.append(synthesis_row)
        required = ("build_signature.txt", "timing_metrics.csv", "synthesis_utilization.rpt", "routed_timing.rpt", "routed.dcp", "clock.xdc")
        if not all((directory / name).is_file() for name in required):
            missing.append(definition["name"])
            continue
        matched = re.search(r"create_clock -name comparison_clock -period ([0-9.]+)", (directory / "clock.xdc").read_text())
        if matched is None or abs(float(matched.group(1)) - 1000 / clock_mhz) > 1e-9:
            raise RuntimeError(f"Clock constraint mismatch: {definition['name']}")
        rows.append(run_comparison.read_implementation_report(definition, arguments, directory))
    if rows:
        temporary = output / "tables/resource_comparison.pending.csv"
        with temporary.open("w", newline="") as target:
            writer = csv.DictWriter(target, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        temporary.replace(output / "tables/resource_comparison.csv")
    if synthesis_rows:
        with (output / "tables/synthesis_comparison.csv").open("w", newline="") as target:
            writer = csv.DictWriter(target, fieldnames=list(synthesis_rows[0]))
            writer.writeheader()
            writer.writerows(synthesis_rows)
    progress = {"target_designs": len(manifest["designs"]), "synthesis_reports": len(synthesis_rows), "completed_designs": len(rows), "timing_passes": sum(row["timing_pass"] for row in rows), "mapping_mismatches": [row["name"] for row in rows if not row["mapping_matches_request"]], "missing_designs": missing, "clock_mhz": clock_mhz, "input_fractional_bits": 24, "output_fractional_bits": 24, "output_total_bits": 32, "output_signed": True, "resource_stage": "post_synthesis", "timing_stage": "post_route"}
    (output / "progress.json").write_text(json.dumps(progress, indent=2) + "\n")
    print(f"Collected {len(rows)}/{len(manifest['designs'])} completed designs; {progress['timing_passes']} pass setup and hold timing.")
    if require_complete and missing:
        raise RuntimeError("Missing completed measurements: " + ", ".join(missing))
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--clock-mhz", type=float, default=250)
    parser.add_argument("--require-complete", action="store_true")
    arguments = parser.parse_args()
    rows = collect(arguments.clock_mhz, arguments.require_complete)
    if rows:
        run_comparison.summarize_results.summarize(DIRECTORY / "results" / f"{arguments.clock_mhz:g}MHz")
