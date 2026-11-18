# Research

Choose the study you want to explore. Run commands from the project root, one level above this folder.

| Study | Purpose | Instructions |
| --- | --- | --- |
| [Exponential accuracy](exponential_accuracy/) | Compare research approximations, Maclaurin, Sollya and ROM accuracy | [README](exponential_accuracy/README.md) |
| [FPGA comparison](fpga_synthesis_results/) | Compare Q24 synthesis resources, latency and routed timing | [README](fpga_synthesis_results/README.md) |
| [Fixed-integer precision](fixed_point_precision/) | Compare every feasible width with fixed integer-bit allocations | [README](fixed_point_precision/README.md) |
| [Input-current sweep](input_current_sweep/) | Measure firing behaviour and individual variable ranges across input currents | [README](input_current_sweep/README.md) |

## Open results

| What you want | Location |
| --- | --- |
| Fixed-integer C precision study | [fixed_point_precision/results_fixed_integer/report.html](fixed_point_precision/results_fixed_integer/report.html) |
| Input-current sweep report | [input_current_sweep/results/report.html](input_current_sweep/results/report.html) |
| Extended sweep up to 1,000,000 pA | [input_current_sweep/results_extended/report.html](input_current_sweep/results_extended/report.html) |
| SV signal names, Q formats and integer-bit graphs | [sv_integer_bits.html](input_current_sweep/results_extended/sv_integer_bits.html) |
| Input-current range tables | [input_current_sweep/results/tables](input_current_sweep/results/tables/) |
| Q24 exponential accuracy plots | [exponential_accuracy/results/images](exponential_accuracy/results/images/) |
| Q24 exponential accuracy tables | [exponential_accuracy/results](exponential_accuracy/results/) |
| FPGA plots | [fpga_synthesis_results/results/250MHz/images](fpga_synthesis_results/results/250MHz/images/) |
| FPGA comparison summary | [comparison_summary.md](fpga_synthesis_results/results/250MHz/tables/comparison_summary.md) |
| FPGA resource table | [resource_comparison.csv](fpga_synthesis_results/results/250MHz/tables/resource_comparison.csv) |


## Main commands

Exponential accuracy (signed 32-bit Q24 output; writes to `results`):

```powershell
python research/exponential_accuracy/compare_base_two_exponential.py
```

Run or resume the fixed-integer C precision study:

```powershell
python -u research/fixed_point_precision/run_fixed_integer_study.py --resume --workers 4
```

FPGA synthesis measurements (Q24 input/output; previous Q8 results are archived):

```powershell
python research/fpga_synthesis_results/run_comparison.py --resume
```

Input-current investigation:

```powershell
python -u research/input_current_sweep/run_current_sweep.py --resume
```

These commands perform computations. Browsing the existing plots and tables does not require rerunning them.

## Folder conventions

- `results`: current outputs.
- `plots` or `images`: figures to inspect.
- `tables`: aggregate neuron precision CSV files.
- `runs`: detailed results for individual neuron simulations.
- `tests`: neuron precision validation code.
- `build`: generated executables and temporary build products.
- `archive`: earlier attempts, development checks and diagnostic logs retained for reference.

The fixed-integer precision study tests 855 candidate simulations across widths 32 through 18 bits and 57 input currents. References use the original 32-bit C model. Hardware results describe actual standalone FPGA implementations and are separate from this C study.
