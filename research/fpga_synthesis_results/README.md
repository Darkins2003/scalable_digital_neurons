# FPGA synthesis results: Q24 fractional exponential cores

This study measures 47 FPGA designs matching the current exponential accuracy test: research linear and cubic, Maclaurin and Sollya degrees 0 through 4, and ROMs with 16 through 65536 entries. Polynomial multipliers have LUT and DSP variants. ROMs have distributed LUT-memory and BRAM variants.

Every design accepts a 24-bit fractional input, representing `0 <= f < 1`, and returns a **signed 32-bit result with 24 fractional bits**. The integer exponent is zero. There is no integer shift or conversion to Q8. The research cubic retains its full Q24 linear term, matching the modified Python model. Polynomial coefficients and intermediates retain 24 fractional bits. Multiplication uses the project's six-stage signed 32-by-32 multiplier and its registered Q24 result.

The default target is **250 MHz** on **xc7z020clg400-1**, the PYNQ-Z2 device. Resource utilisation comes from synthesis. Place and route are also performed to measure timing, which is reported separately. Passing 250 MHz does not establish the highest achievable frequency.

The previous Q8 designs and measurements are preserved in `archive/q8`. They are not reused as Q24 measurements.

## Run the complete test

Open a terminal in the project folder, then run:

```powershell
python research/fpga_synthesis_results/run_comparison.py --resume
```

This one command generates all 47 Q24 designs, checks their output integers and latency against Python, prepares LUT and DSP multiplier IPs from your multiplier configuration, validates both vendor multiplier implementations, synthesises and routes every design, joins matching Q24 accuracy statistics, and creates the tables and plots. It can take several hours. No full Q24 measurement sweep has been run during this update.

Requirements: Python with NumPy and Matplotlib, and Vivado with support for the Zynq-7000 device. The default Vivado binary folder is `C:/AMDDesignTools/2026.1/Vivado/bin`. Set a different installation with:

```powershell
python research/fpga_synthesis_results/run_comparison.py --resume --vivado-bin "C:/path/to/Vivado/bin"
```

The saved accuracy study at `research/exponential_accuracy/results` must contain signed 32-bit Q24 hardware statistics for every default model and ROM size, with uniform and boundary populations. Your current completed accuracy results satisfy this requirement. The FPGA run saves a copy under `tables/accuracy_reference` so later accuracy runs cannot silently change an existing campaign's comparisons.

Press Ctrl+C to interrupt the default run. Completed designs remain saved, while an unfinished design will need rebuilding. Run the same command with `--resume` after an interruption. Finished designs are reused only when their source signature and clock match. An unfinished design is rebuilt. Use `--jobs 2` to run two FPGA builds at once if your computer has sufficient memory; the default is one.

## Shorter checks

Generate RTL, memory and expected simulation outputs without running Vivado:

```powershell
python research/fpga_synthesis_results/run_comparison.py --generate-only
```

Check all designs against Python using the functional multiplier model, without running synthesis:

```powershell
python research/fpga_synthesis_results/run_comparison.py --validate-only
```

The Q24 update passed this validation: 47 designs, 19670 stimulus cycles, and 845390 checked valid outputs, including resets and gaps in valid inputs. This simulation is a directed and sampled RTL check. It is separate from the exhaustive Python accuracy sweep over 16777216 fractional input encodings. Validation logs are under `results/_work/validation_functional`.

Measure a smaller selection first:

```powershell
python research/fpga_synthesis_results/run_comparison.py --resume --models research_linear_logic research_cubic_lut research_cubic_dsp rom_1024_distributed rom_1024_block
```

Available design names are in `design_manifest.json`. Subset runs preserve completed measurements for other designs. The default complete run validates the functional, LUT-vendor and DSP-vendor multiplier models. Avoid `--skip-validation` for report measurements.

## Find the results

```text
results/
    250MHz/
        README.md
        run_configuration.json
        progress.json
        failures.json
        tables/
            resource_comparison.csv
            synthesis_comparison.csv
            comparison_summary.md
            accuracy_reference/
        images/
            00_tables/
            01_resource_usage/
            02_latency/
            03_accuracy_vs_resources/
            04_accuracy_vs_latency/
            05_accuracy_vs_model_size/
            06_routed_timing/
        reports/
            research_linear_logic/
            research_cubic_lut/
            ...
    _work/
```

Measurement CSVs, configuration and plots are created when the sweep runs. Empty folders do not indicate measured results. `tables/resource_comparison.csv` is the combined numerical result; `tables/comparison_summary.md` is a readable table. The PNG versions are under `images/00_tables`.

Most image categories have `00_all_models`, `01_research`, `02_maclaurin`, `03_sollya` and `04_rom` subfolders. Accuracy trade-offs are separated into mean absolute error and maximum absolute error, then model families. Model-size plots show increasing degree or ROM entries, with separate accuracy and hardware-cost figures. FPGA measurements describe fixed-point hardware, so there is no ideal-resources folder.

Plots use full model names. Scatter plots have numbered points linked to a full-name key. Their logarithmic error axes make small errors visible. Resource axes have six evenly spaced decimal tick labels. All models, including timing failures, are shown; failed designs are marked explicitly. Tables separate LUTs, registers, DSPs and BRAM instead of treating them as one area measure.

`reports/<design>/synthesis_utilization.rpt` is the authoritative resource report. `routed_timing.rpt`, `critical_paths.rpt` and `timing_metrics.csv` contain timing measurements. A half BRAM tile means one RAMB18. `routed_utilization.rpt` is retained as a raw report but is not the source of the resource comparisons.

## Update tables and plots without rebuilding

Collect completed reports, check their source signatures, and regenerate the combined tables and plots:

```powershell
python research/fpga_synthesis_results/collect_results.py --clock-mhz 250
```

Add `--require-complete` to fail if any of the 47 measurements is missing or stale. Regenerate only plots from the existing combined CSV:

```powershell
python research/fpga_synthesis_results/summarize_results.py
```

`plot_resource_tradeoffs.py` is another entry point for the same organised report generator. Neither plotting command runs Vivado.

## Read the comparisons

1. Compare LUT and DSP implementations of the same formula and degree.
2. Compare Maclaurin, Sollya and research formulas at matching degrees.
3. Compare ROM sizes, then LUT memory versus BRAM for the same size.
4. Compare mean and maximum absolute error against each resource separately.
5. Compare accuracy against latency, then inspect routed timing independently.

All designs accept one input every cycle. Latency is elapsed clock periods from the acceptance edge to the corresponding output edge. At 250 MHz one period is 4 ns. A three-register ROM path therefore has a two-period latency under this convention. Existing latency counts are unchanged by the Q24 update and were checked in simulation.

Accuracy values come from the matching fixed-point Python test, before any integer shift. Means use uniform inputs; maxima take the largest error across uniform and boundary populations. Errors are measured against unquantised `2**f`. These scatter plots do not use bins.

A timing pass is one operating point, not a maximum clock speed. Compare routed data-path delay and timing margins, then tighten the constraint in a separate run, for example:

```powershell
python research/fpga_synthesis_results/run_comparison.py --clock-mhz 300 --resume
```

That run writes to `results/300MHz`. A slack-derived frequency is only an estimate. These measurements are standalone cores, not full-system or board timing results.
