# Input-current sweep: behaviour and integer ranges

Investigate how external input current changes the existing 32-bit three-neuron model, then measure the integer range needed by each numerical value. This is separate from the fixed-point precision investigation and does not alter the production C model or RTL.

## Initial experiment

| Setting | Value |
| --- | --- |
| External current | 0 to 300 pA, in 1 pA increments: 301 cases |
| Intended operating region | 0 to 150 pA |
| Exploratory region | Above 150 pA |
| Network | Original three-neuron excitatory ring, weight 0.26 |
| Stimulated neuron | Neuron 0 |
| Duration | 190000 steps, nominally 190 ms |
| Pulse | Steps 60000 through 140000 inclusive |
| Numeric formats | Original 32-bit formats, unchanged |
| Proposed integer headroom | One additional bit, reported separately from observed requirements |

The maximum current is a chosen exploratory endpoint, not a proven model or hardware limit. Changing network weights, connectivity, initial conditions, stimulus shape or duration requires a new operating-envelope assessment.

## Run from the project root

```powershell
python -u research/input_current_sweep/run_current_sweep.py --resume
```

Each terminal line reports completed cases, current, crossing counts, overflow and C execution time. The default uses four concurrent current cases. Keep the computer awake during the sweep.

The driver generates a separately instrumented C file under `build/`. For **every current**, it runs both that model and the existing original C harness with 64-bit multiplication, then requires exact agreement of every recorded step and all 18 states. Profiling does not change the numerical equations or formats.

No MATLAB, XSim or physical FPGA is run. These results characterise fixed-point C behaviour, not error against mathematical truth. The earlier 80 pA MATLAB comparison remains a separate investigation.

### Extended investigation up to 1,000,000 pA

```powershell
python -u research/input_current_sweep/run_extended_sweep.py --resume
```

This preserves the original results and adds 136 currents in four bands:

| Range, pA | Increment, pA | Additional cases |
| --- | --- | --- |
| 325 to 1,000 | 25 | 28 |
| 1,250 to 10,000 | 250 | 36 |
| 12,500 to 100,000 | 2,500 | 36 |
| 125,000 to 1,000,000 | 25,000 | 36 |

Open [results_extended/report.html](results_extended/report.html) for the full report starting at **1 pA**. It contains all 436 tested positive currents. The saved 0 pA control remains in the original study, giving 437 total checkpoints. The original network, pulse and numerical formats are unchanged.

The report provides:

- Four selectable Vmem panels, covering every tested current and each neuron, with previous/next controls, shared voltage scales and pulse-onset zoom.
- PNG waveform comparison sheets for low currents, high valid currents and arithmetic failures.
- Integer-bit graphs for every variable type, including neuron states, derivatives, current vectors, matrix products/sums, exponentials, constants and wide products.
- Separate curves for different fractional positions, with dashed lines showing existing integer capacity.
- Overflow graphs and tables separating the first triggering calculation from additional flags in the same stopping step.
- A searchable table and PNG tables covering all currents, including the original 1-300 pA cases.

Each band also retains its detailed report and checkpoints. The main report is self-contained apart from the adjacent `data`, `plots` and `tables` folders; keep them together. Waveform data load directly from local JavaScript files, so no web server or internet connection is required.

### SystemVerilog names, Q formats and bit graphs together

Open [results_extended/sv_integer_bits.html](results_extended/sv_integer_bits.html) for a separate, self-contained page. Start with the **Important variables** section: ten panels covering Vmem, Vk, Vg, Vna, the two triangle states, the current vector, total neuron current, voltage-state derivatives and Euler increments. State graphs take the largest requirement across all three neurons. The complete 26 format groups and all 486 individual profiled quantities remain in expandable sections, closed initially. Every graph retains its RTL name or labelled equivalent and current Q format. One current selector updates every numeric result. Search by a signal name or Q format to automatically open matching sections, change the current range of all graphs together, or hover over a graph for a tested point.

The regular report command regenerates this page too. To rebuild only this page from the existing CSV results:

```powershell
python research/input_current_sweep/make_sv_bit_report.py
start research/input_current_sweep/results_extended/sv_integer_bits.html
```

The mapping CSV is `results_extended/tables/sv_variable_mapping.csv`. C prefix sums and optimised/precomputed RTL expressions are explicitly labelled; their results are C-model measurements, not new RTL intermediate-range measurements. Q formats include sign in the integer count. Invalid runs have no valid complete-run bit requirement.

Runs that encounter detected overflow stop early. Their incomplete crossing counts and ranges are excluded from the combined behaviour and integer-budget recommendations. The first sampled failure is not an exact current limit, and failures need not be monotonic with current. These very large inputs are exploratory rather than a proposed operating range.

Regenerate the full presentation from saved simulations, then open it:

```powershell
python -u research/input_current_sweep/run_extended_sweep.py --report-only
start research/input_current_sweep/results_extended/report.html
```

The CSV `integer_bits_by_type_and_current.csv` contains per-type requirements at every valid current; `all_values_by_current.csv` retains all individual profiles and their validity labels. Integer bits include sign. Mixed formats within a type are reported separately, and invalid profiles never contribute to integer recommendations. Overflow checks identify a neuron and calculation site; some site labels do not retain the individual state index. The first flagged current is sampled, and additional flags can follow the first overflow within the same step.

### Custom current range

Use a new output directory for changed settings:

```powershell
python -u research/input_current_sweep/run_current_sweep.py --minimum-current 0 --maximum-current 150 --current-step 0.5 --output research/input_current_sweep/results_half_pa --resume
```

Current increments must be exactly representable in Q8, meaning multiples of 1/256 pA. The maximum must lie on the requested grid. Negative currents are supported explicitly through `--minimum-current`; they are not part of the default positive-current experiment.

Other options include `--steps`, `--pulse-start`, `--pulse-end`, `--headroom-bits`, `--workers`, `--gcc` and `--keep-traces`. The full pulse must fit inside the selected simulation. Different experiment or source settings cannot be mixed with saved checkpoints.

### Regenerate the report without repeating simulations

```powershell
python research/input_current_sweep/run_current_sweep.py --report-only
```

This also works on a partially completed sweep, using the saved cases. Completion status and the number of available currents are reported explicitly.

## What is measured

- All 18 individual stored states, including their initial values and every update.
- All 18 derivatives and Euler increments.
- All 24 current-vector elements.
- Individual scaled triangles, coupled triangles, exponential inputs and outputs.
- Every synapse scale, scaled weight, contribution and partial sum, including disabled connections.
- Every rescaled neuron-matrix product and partial sum.
- The encoded neuron-matrix coefficients, triangle slopes and other fixed constants.
- Exact raw 64-bit full-product extrema, grouped by neuron, calculation site and operand formats before rescaling.

The report covers numerical neuron-datapath values. Loop indices, pointer aliases, lookup-address bits and control flags are not treated as candidate neuron formats. Existing operation-site diagnostics are retained per current in `calculation_sites.csv` for additional context.

For each profiled value, CSV files retain exact raw integer minimum/maximum, fractional count, times and input currents producing the extremes, observed integer-bit requirement, and a separate headroom allowance. Values from numerically invalid runs are excluded from aggregate integer recommendations.

Integer bits include sign. The minimum allocation is determined using exact signed raw integer boundaries, including the asymmetric positive/negative endpoints. It is not estimated from rounded plot labels. The state PNG table also shows the remaining fractional budget at 28, 24, 20 and 16 total bits after headroom. Those are proposals for a later precision study, not validated reduced-width models.

The proposed formats assume at least one integer/sign bit and `0 <= fractional bits < total width`, matching the current configurable model. Formats with a binary point beyond the stored word are not investigated here.

### Behaviour definitions

A spike is counted as an upward crossing of 1.4542 with interpolated crossing time. The initial-to-first-sample interval is included. Counts are reported before, during and after the pulse. Pulse-window firing rate uses the actual nominal pulse duration, 80.001 ms in the default experiment. It differs from the total count divided by 190 ms.

The driver also records first-crossing latency, interspike intervals, interval variability, excursion peaks, late-pulse crossings and the fraction of late-pulse samples above threshold. A sustained above-threshold excursion can count once. These diagnostics do not by themselves prove a physiological spike or depolarisation block.

### Overflow behaviour

The instrumented model retains the existing checks before hardware-style narrowing. On detected overflow, it stops at the end of that simulation step. The affected case is labelled invalid/incomplete; its ranges do not contribute to integer recommendations. The original C comparison is required for the prefix strictly before the first flagged step. Complete valid runs must match the original trace throughout.

Constant-to-zero diagnostics and lost Euler updates are recorded as well. Do not infer absence of numerical problems from spike counts alone.

## Results

Open [results/report.html](results/report.html) after the sweep, or [results/README.md](results/README.md).

| Output | Purpose |
| --- | --- |
| `plots/behaviour/` | Counts, pulse firing rate, peak voltage, latency, spike raster and activity map |
| `plots/states/` | Each state type's minimum/maximum versus current and integer-bit heatmap |
| `plots/intermediates/` | Total neuron current and derivative ranges |
| `plots/waveforms/` | Example responses at selected input currents |
| `tables/images/01_state_integer_bits.png` | Visible per-state ranges and proposed bit allocations |
| `tables/images/behaviour_*.png` | Readable tables covering every current level |
| `tables/images/variables_*.png` | Readable range tables covering every profiled value |
| `tables/behaviour_by_current.csv` | All per-neuron behaviour measurements |
| `tables/state_integer_bits.csv` | Per-state range and integer requirements across valid currents |
| `tables/state_integer_bits_operating_range.csv` | Separate state budgets using only the intended 0–150 pA region |
| `tables/images/02_state_integer_bits_operating_range.png` | Visible table of state budgets for 0–150 pA |
| `tables/all_value_ranges.csv` | Every variable's aggregate extrema and currents producing them |
| `tables/all_value_ranges_operating_range.csv` | Every variable's extrema within 0–150 pA only |
| `tables/all_values_by_current.csv` | Every profiled value at every current |
| `tables/numeric_checks.csv` | Exact C checks, overflow, zero constants, lost updates and execution times |
| `tables/upward_crossings.csv` | Individual crossing times and excursion peaks |
| `tables/transitions.csv` | Adjacent tested currents where counts, integer requirements or validity change |
| `runs/current_XXX/` | Independent checkpoints, exact raw ranges and display data per current |
| `manifest.json` | Source hashes, current grid, compiler and experiment settings |
| `study_summary.json` | Completion and numeric validity summary |

All metrics use the complete trace. Waveform plots use a reduced display grid plus each bin's full minimum/maximum envelope, so narrow peaks are retained visually. Full CSV traces and stimulus files are removed only after the case is checkpointed unless `--keep-traces` is selected. This keeps the default sweep from retaining many gigabytes of repeatable traces. Raw profiles, spike times, metrics and compressed display data are retained.

## Interpretation

The sweep tells us the **largest observed range requirement**, not a mathematical bound over all possible inputs. One extra headroom bit doubles the signed range but is not a universal safety proof. Always recheck reduced-width candidates, since quantisation can change the states they reach. A format validated for this network cannot automatically be claimed to support a larger or differently connected network.

## Checks

```powershell
python -m unittest discover -s research/input_current_sweep/tests -v
```

Unit checks cover exact integer-range endpoints, Q8 current grids, the initial crossing interval and exclusion of invalid runs from integer recommendations. The sweep additionally performs the full original-C trace comparison at every current.
