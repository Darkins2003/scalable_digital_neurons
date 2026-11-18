# Archived Q8 study

These are the previous Q8-output designs and measurements. They are preserved for reference and are not current Q24 results. Use ../../README.md for current commands. The original study documentation follows.

# Fractional base-two exponential FPGA comparison

The first comparison targets 250 MHz, a 4 ns period, on `xc7z020clg400-1`, matching the device configured for the project's multiplier. Frequency and FPGA part are command-line options. This does not change the main project's clock constraint or HDL.

All designs accept an unsigned 24-bit fractional exponent representing `0 <= f < 1` with 24 fractional bits. Results use signed 32-bit storage with 8 fractional bits. There is no integer-exponent shift logic. Every implementation can accept a new input every cycle, accompanied by `input_valid`; `output_valid` identifies the corresponding result. Reset is synchronous and flushes pending transactions.

## Designs

There are 47 independently buildable top modules under `rtl`, listed in `design_manifest.json`:

| Models | Implementations | Designs |
|---|---|---:|
| Research linear | Logic | 1 |
| Research cubic | LUT multiplier and DSP multiplier | 2 |
| Maclaurin and Sollya, degree 0 | Constant with valid pipeline | 2 |
| Maclaurin and Sollya, degrees 1 through 4 | LUT multiplier and DSP multiplier | 16 |
| ROMs with 16 through 65,536 entries, powers of two | Distributed ROM and block ROM | 26 |

Each top instantiates the shared arithmetic in `rtl/fractional_models.sv`. Arithmetic follows `research/exponential_accuracy/compare_base_two_exponential.py`: research cubic truncates its linear term to Q8 before correction; Maclaurin/Sollya use Q24 coefficients and Horner intermediates, with truncation after each product and final conversion to Q8. The 1,024-entry table uses the original project's memory contents; other tables match Python's generation.

Multiplication instantiates the project's existing `signed_32_32_multiplication` module without changing it. `run_comparison.py` reads the project's actual multiplier XCI configuration. Both backends preserve its signed 32-by-32 inputs, 64-bit product, six internal pipeline stages, synchronous clear, and wrapper output stage. The DSP backend preserves `Use_Mults`; the LUT backend changes only construction to `Use_LUTs`. Each design build chooses one backend, so the LUT and DSP tops are built separately. Additions remain ordinary inferred logic; degrees zero and research linear do not get artificial DSP variants.

Sollya degree 1 also goes through the common Horner pipeline in this controlled comparison. Its coefficient of f is exactly one, so a specialised version can use an adder without a multiplier and with fewer pipeline registers. Its reported DSP cost describes the supplied multiplier-based implementation. All counts apply to the concrete architectures in this folder.

The ROM array has 25 storage bits per entry: one integer bit and 24 fractional bits. This is independent of the 24 fractional input bits and the 8 fractional output bits. Vivado can trim unused bits and constant columns, so resources are measured from synthesis utilisation reports rather than estimated from logical table size. All resource comparisons use this same reporting stage. Distributed constant ROM can appear under logic LUTs rather than memory LUTs in Vivado's reports.

## Run

From the project folder:

```powershell
python research/fpga_synthesis_results/run_comparison.py
```

This regenerates the designs and Python-derived validation data, simulates all tops, prepares both multiplier backends, checks both generated vendor simulation models, then synthesises, places and routes every design. One Vivado session runs by default, limited to two tool threads; `--jobs 2` enables two concurrent sessions when enough memory is available. Each core is synthesised, placed and routed afresh, while its worker retains the loaded device and source project to reduce repeated startup and loading. Switching between LUT and DSP multiplier backends opens a fresh project to avoid mixing the two IP definitions. Use `--separate-processes` to launch a new Vivado process for each core instead. No bitstream or board connection is needed.

```powershell
python research/fpga_synthesis_results/run_comparison.py --clock-mhz 250 --jobs 1 --resume
python research/fpga_synthesis_results/run_comparison.py --clock-mhz 300 --jobs 1 --resume
python research/fpga_synthesis_results/run_comparison.py --validate-only
python research/fpga_synthesis_results/run_comparison.py --generate-only
python research/fpga_synthesis_results/run_comparison.py --models research_cubic_lut research_cubic_dsp rom_1024_block
```

The default tool directory is `C:/AMDDesignTools/2026.1/Vivado/bin`; change it with `--vivado-bin`. The part can be changed with `--part`. Keep tool version, device, clock and settings equal within a comparison. `--skip-validation` is for builds whose arithmetic was already verified. `--resume` reuses completed implementations only when their source and configuration signatures match. Multiplier IP is cached separately; use a fresh run if its source configuration, tool version or FPGA part changes.

## Measurements

Results are under `results/250MHz` for the default run. `resource_comparison.csv` contains post-synthesis logic LUTs, memory LUTs, total LUTs, registers, DSP48 cells, RAMB18/RAMB36 cells and BRAM tiles. Setup and hold slack, critical-path data delay and timing status remain post-route. Throughput and latency describe the validated RTL pipeline; accuracy metrics come from Python. The `resource_stage` and `timing_stage` columns identify the measurement sources explicitly. Each design directory contains synthesis and routed utilisation reports, routed timing summary, ten critical paths, timing checks, the exact clock constraints, console log and routed checkpoint. `failures.json` records tool failures separately from timing failures.

At the end, `comparison_summary.md` collects the results in one table. The `images` subfolder contains post-synthesis LUT, flip-flop, DSP and BRAM comparisons, plus RTL latency comparisons, plus accuracy-versus-LUT scatter plots for designs that pass timing. Recreate these from an existing results CSV with `python research/fpga_synthesis_results/summarize_results.py research/fpga_synthesis_results/results/250MHz`. A full routed sweep can take hours; `--models` selects a smaller set when only specific comparisons are needed.

After measuring in separate batches, `python research/fpga_synthesis_results/collect_results.py --clock-mhz 250` combines all completed report directories into one CSV without rebuilding. This reads existing measurements for the unchanged model set; rerun the implementation after changing a design. Add `--require-complete` to check that every design has finished. Then rerun `summarize_results.py` to refresh the combined table and images.

Every build uses out-of-context implementation, registered input/output boundaries, a common BUFG clock-source location and 0.1 ns clock uncertainty. Unplaced external port paths, including the incoming synchronous reset, are excluded from timing; internal register-to-register arithmetic and valid paths are timed. These are standalone core comparisons, not measurements of the complete neuron system or its external interfaces. A failed internal timing target remains in the comparison and is not reported as a successful 250 MHz design. Resource mapping is checked separately; for example, a block-ROM request optimised entirely into logic is flagged rather than silently counted as BRAM.

`latency_cycles` counts complete periods between the input acceptance edge and the corresponding output edge. `register_stages` includes both endpoint edges. A polynomial of degree n has latency `1 + 8*n` periods; research cubic has 17; ROM has 2; research linear and degree-zero constants have 1. Research cubic splits subtraction and correction addition into separate stages for the 250 MHz target. The automated scoreboard checks these exact edge relationships, including reset flushes and invalid gaps. Latency and register costs are reported instead of being equalised by adding unnecessary registers to simpler designs.

The frequency estimate derived from routed slack is a guide for the particular placed-and-routed design, not a verified maximum frequency. Tighten the clock and rerun to measure achievable frequency. Passing the initial 250 MHz target does not establish that a design has reached its useful frequency limit. The shared multiplier architecture is held constant across arithmetic variants; results compare these concrete pipelines and do not prove a globally minimum-resource implementation.

Existing exhaustive accuracy results are joined by model name. Those values describe the Q24-input/Q8-output arithmetic validated here. The simulation covers directed table boundaries, random inputs, reset flushes and valid gaps, but is not exhaustive over all input sequences.

AMD references: [multiplier mapping](https://docs.amd.com/r/en-US/ug901-vivado-synthesis/Multipliers-Implementation), [ROM inference](https://docs.amd.com/r/2023.2-English/ug901-vivado-synthesis/ROM_STYLE), and [utilisation reporting](https://docs.amd.com/r/en-US/ug906-vivado-design-analysis/Report-Utilization).

The seven resource/accuracy/latency plots in `research/fpga_synthesis_results/results/250MHz/images/10_fpga_resource_tradeoffs` use the same post-synthesis resource counts. Regenerate them with `python research/fpga_synthesis_results/plot_resource_tradeoffs.py`. Folder 09 contains the synthesis utilisation and latency table, which already used synthesis counts. Original Vivado routed reports and earlier batch snapshots remain historical measurement records; report tables and plots use the aggregated post-synthesis CSV.

The Maclaurin polynomial family is expanded at zero. The terminology change does not change coefficients, arithmetic, latency or measured resources. Existing Vivado logs and checkpoints retain their originally recorded top names; `original_measured_top_names` in `results/250MHz/run_configuration.json` maps the renamed models to those historical records. Result folders, source tops, tables and plots use the current names.
