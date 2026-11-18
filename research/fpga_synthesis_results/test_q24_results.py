import csv
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import run_comparison
import summarize_results


class Q24ResultChecks(unittest.TestCase):
    def test_old_precision_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "run_configuration.json").write_text(json.dumps({"output_fractional_bits": 8, "output_total_bits": 32, "output_signed": True}))
            with self.assertRaisesRegex(ValueError, "Q24"):
                summarize_results.load_rows(directory)

    def test_statistics_use_synthesis_counts_and_matching_q24_populations(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "250MHz"
            report = output / "reports/research_linear_logic"
            report.mkdir(parents=True)
            reference = output / "tables/accuracy_reference"
            reference.mkdir(parents=True)
            (reference / "run_configuration.json").write_text(json.dumps({"input_fractional_bits": 24, "output_fractional_bits": 24, "output_total_bits": 32, "output_signed": True}))
            with (reference / "accuracy_summary.csv").open("w", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=["model", "domain", "population", "mean_absolute_error", "maximum_absolute_error"])
                writer.writeheader()
                writer.writerows([{"model": "linear", "domain": "hardware_fractional", "population": "uniform", "mean_absolute_error": .01, "maximum_absolute_error": .02}, {"model": "linear", "domain": "hardware_fractional", "population": "directed_boundaries", "mean_absolute_error": .03, "maximum_absolute_error": .04}])
            (report / "timing_metrics.csv").write_text("setup_slack_ns,hold_slack_ns,data_path_delay_ns,dsp_cells,ram18_cells,ram36_cells\n1,0.05,2,99,99,99\n")
            labels = {"LUT as Logic": 10, "LUT as Memory": 2, "Slice LUTs": 12, "Slice Registers": 20, "Block RAM Tile": .5, "DSPs": 0, "RAMB18": 1, "RAMB36/FIFO": 0}
            (report / "synthesis_utilization.rpt").write_text("\n".join(f"| {label} | {value} |" for label, value in labels.items()))
            definition = {"name": "research_linear_logic", "model": "linear", "implementation": "logic", "latency_cycles": 1, "register_stages": 2}
            row = run_comparison.read_implementation_report(definition, SimpleNamespace(clock_mhz=250), report)
            self.assertEqual(row["output_fractional_bits"], 24)
            self.assertEqual(float(row["dsp_cells"]), 0)
            self.assertEqual(float(row["ram18_cells"]), 1)
            self.assertEqual(float(row["mean_absolute_error"]), .01)
            self.assertEqual(float(row["maximum_absolute_error"]), .04)
            self.assertEqual(row["latency_ns"], 4)
            self.assertTrue(row["timing_pass"])
            settings = json.loads((reference / "run_configuration.json").read_text())
            settings["output_fractional_bits"] = 8
            (reference / "run_configuration.json").write_text(json.dumps(settings))
            with self.assertRaisesRegex(ValueError, "Q24"):
                run_comparison.read_implementation_report(definition, SimpleNamespace(clock_mhz=250), report)

    def test_accuracy_snapshot_cannot_change_silently(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = directory / "accuracy"
            source.mkdir()
            (source / "accuracy_summary.csv").write_text("original results")
            (source / "run_configuration.json").write_text("{}")
            with patch.object(run_comparison, "verify_accuracy_source", return_value=source):
                run_comparison.snapshot_accuracy(directory / "measurement")
                run_comparison.snapshot_accuracy(directory / "measurement")
                (source / "accuracy_summary.csv").write_text("changed results")
                with self.assertRaisesRegex(ValueError, "changed"):
                    run_comparison.snapshot_accuracy(directory / "measurement")

    def test_measurement_signature_tracks_clock_and_device(self):
        manifest = json.loads((run_comparison.DIRECTORY / "design_manifest.json").read_text())
        definition = manifest["designs"][0]
        first = run_comparison.build_signature(definition, 250, "xc7z020clg400-1")
        self.assertEqual(first, run_comparison.build_signature(definition, 250.0, "xc7z020clg400-1"))
        self.assertNotEqual(first, run_comparison.build_signature(definition, 300, "xc7z020clg400-1"))
        self.assertNotEqual(first, run_comparison.build_signature(definition, 250, "xc7z020clg400-2"))


if __name__ == "__main__":
    unittest.main()
