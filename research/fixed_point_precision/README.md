# Fixed-integer C precision study

Find smaller formats that preserve neuron behaviour while reducing FPGA resources and improving achievable clock frequency. The experimental C model is separate from the production model and RTL.

## Run the study

This is the only precision study in this folder. It uses the configurable C model with one fixed integer allocation per shared Q type. Numerical helpers live in `precision_support.py`; common report drawing helpers live in `plotting_support.py`. The old combination sweep and its results have been removed. No RTL formats or production model are changed.

Run from the project root:

```powershell
python -u research/fixed_point_precision/run_fixed_integer_study.py --resume --workers 4
```

Open the report with:

```powershell
start research/fixed_point_precision/results_fixed_integer/report.html
```

The default experiment is **855 candidate simulations**: all 15 widths from **32 down to 18 bits**, at 57 currents. Currents are 0-100 pA in 5 pA steps, then 125-1,000 pA in 25 pA steps. Each run uses 190,000 nominal 0.001 ms steps and the existing pulse at steps 60,000 through 140,000 inclusive. No screening combinations or headroom combinations are searched.

The saved 0-1,000 pA range investigation supplies the budgets. The driver verifies its source hashes and checkpoint provenance, combines every measured variable and checked pre-truncation operation range, and adds one headroom bit. All C groups that originally shared a Q type receive the same allocation:

| Original shared type | C groups | Observed integer/sign bits | Allocated with headroom |
| --- | --- | ---: | ---: |
| Q8.24 | State, constant, timestep | 8 | 9 |
| Q9.23 | Matrix | 9 | 10 |
| Q24.8 | Current, including exponential results and voltage derivatives | 17 | 18 |
| Q16.16 | Triangle states, slopes, derivatives and offsets | 10 | 11 |

For each candidate, **fractional bits = total width - allocated integer bits**. The 18-bit current type therefore has zero fractional bits. Full products remain signed 64-bit. These are C-model budgets and do not establish RTL intermediate ranges.

There are also **57 original-format 32-bit reference runs**, each checked step by step against the original C harness. That is 912 precision-model executions plus 57 original-harness verification executions for a fresh full study. The reallocated 32-bit candidate is distinct from this reference. The study compares only with C, so MATLAB is not required and no golden-reference substitution is made.

The report shows every Q configuration, the encoded timestep at every width, numeric-validity and error heatmaps, voltage overlays with separate signed-error plots at 80 and 1,000 pA, and per-current tables. Numeric checks cover pre-narrowing overflow, nonzero constants becoming zero and lost Euler updates. State RMSE, maximum errors, threshold-crossing counts, unmatched crossings and matched timing errors use the complete traces. Display files retain bin extrema. Results with overflow or zero constants are excluded from the valid-error heatmaps; their diagnostic metrics remain labelled in the CSVs. No automatic accuracy pass/fail limit is assumed.

The [interactive width comparison table](results_fixed_integer/comparison_table.html) adds an input-current slider with a linked typed value. It shows every recorded width, total local peaks across all three neurons, maximum normalised cross-correlation for the selected neuron, the best shift applied to the candidate and arithmetic faults. The maximum is searched over selectable bounded shifts, with overlap-specific mean and energy normalisation. A positive shift moves an early candidate later. Correlation is not a percentage overlap and does not establish amplitude agreement.

The bit-width slider and linked typed value select a highlighted table row and update three plots beside the table: original-time voltage overlay, voltage overlay after the best shift, and correlation versus shift. Clicking a width row also selects it. Neuron, shift-range and viewing-window controls update the plots. Peak markers show the local maxima counted for the selected neuron. Waveforms load on demand and are cached; no C simulations run when using these controls. Keep `similarity_plot_controls.js` and `comparison_waveforms/` beside `comparison_table.html`.

These additional metrics are **sampled-waveform estimates** from the retained 2,000-point display traces, approximately 0.095 ms apart for full runs. They do not use the deleted full candidate traces. Correlation uses 60-190 ms, while local peaks use the entire saved trace. Peaks require height 1.4542, prominence 1 normalised voltage unit and separation 1 ms; incomplete endpoint peaks are excluded. This definition differs from the existing full-resolution threshold-crossing counts. Invalid cases have no similarity score. Method details are visible on the page and saved in `similarity_method.json`. Cached post-processing results are kept under `similarity_cache/`.

To generate only that table, without running C simulations:

```powershell
python research/fixed_point_precision/make_similarity_table.py
start research/fixed_point_precision/results_fixed_integer/comparison_table.html
```

To add the individual signal-type sweeps to the same comparison page:

```powershell
python -u research/fixed_point_precision/make_similarity_table.py --run-type-sweep --resume --workers 4
start research/fixed_point_precision/results_fixed_integer/comparison_table.html
```

This runs 127 unique candidates at 80 pA: one shared 32-bit starting configuration and six sweeps with only the selected signal group reduced. State, constant and timestep each sweep independently from 32 to 9 bits, matrix to 10, current to 18 and triangle to 11. Every sweep reaches zero fractional bits, even when constants become zero or overflow occurs. All other signal types stay at 32 bits in each experiment; reductions are not carried into the next sweep. Select the sweep in the HTML, then use the existing width slider, table rows and plots. The selected waveform lists every group's actual Q format. Current controls are fixed at 80 pA for individual sweeps. New results and independent resumable checkpoints are under `results_fixed_integer/individual_signal_type_sweep/`. Previous results under `results_fixed_integer/signal_type_sweep/` remain unchanged, and the previous combined state/constant/timestep sweep is omitted from the HTML table. The existing all-types study is preserved. Add `--prepare-only` to prepare the plan without simulating. Running the table generator without `--run-type-sweep` also includes any saved individual-sweep results.

Low widths still run even if they zero constants. In particular, the timestep uses the same fixed integer allocation as other original Q8.24 values; it can quantise to zero at the minimum width. The format catalog exposes this rather than silently changing the timestep format.

Useful commands:

```powershell
python research/fixed_point_precision/run_fixed_integer_study.py --prepare-only
python research/fixed_point_precision/run_fixed_integer_study.py --resume --check-resume
python research/fixed_point_precision/run_fixed_integer_study.py --report-only
```

`--prepare-only` writes the complete plan and a clearly labelled prepared report without executing C simulations. `--resume` reuses compatible checkpoints. Changing widths, currents, headroom, sources or other numerical settings requires a new `--output` directory. `--report-only` regenerates a complete or partial report from saved checkpoints. Each current retains a compressed original-format reference and each candidate retains compressed comparison display data. Add `--keep-traces` to keep the much larger full CSV traces.

To run a smaller development check without changing the production plan:

```powershell
python -u research/fixed_point_precision/run_fixed_integer_study.py --widths 32 24 18 --currents 0 80 1000 --output research/fixed_point_precision/build/fixed_integer_smoke --resume
```

Output files live under `results_fixed_integer/`: `integer_budgets.json`, `configurations.json`, `manifest.json`, `progress.json`, `study_summary.json`, `tables/`, `plots/` and independent `runs/` checkpoints. The CSV `tested_combinations.csv` lists every requested width/current pair. Keep the report beside its output folders.

Saved range-profile source checks and pre-cleanup fixed-integer checkpoints remain verifiable through `profile_source_compatibility.json`. It records exact old/new source hashes and unchanged numerical-function AST hashes. Numerical source or setting changes outside this recorded cleanup still require a fresh output directory.
