# Fractional base-two exponential comparison

This script compares the research linear and modified Q24 cubic approximations, Maclaurin polynomials and the supplied Sollya fits of degrees 0 through 4, and ROM approximations of `2**f` for `0 <= f < 1`. The integer exponent is always zero. There is no negative-exponent or integer-shift sweep.

Run from the project folder:

```powershell
python research/exponential_accuracy/compare_base_two_exponential.py
```

The comparison now retains 24 fractional bits in signed 32-bit results, before any integer shift or Q8 conversion. Current results are saved in `results`. Previous Q8 FPGA measurements are archived. The FPGA study now generates matching Q24 designs, which need a fresh synthesis sweep.

Running without arguments is equivalent to adding `--step-size 1 --bins 256`. You can still override either setting.

Requirements are Python 3, NumPy and Matplotlib. Install missing packages with:

```powershell
python -m pip install numpy matplotlib
```

## Inputs and ROM sizes

All comparison inputs have 24 fractional bits and zero integer bits. The default uniform sweep contains all 16777216 representable fractional values:

```text
f = 0, 0.000000059604644775390625, 0.00000011920928955078125, ...
reference = 2**f
```

That is a default fractional step of `2**-24`, or 1 encoded unit (binary `1`) of the Q24 representation. The comparison starts with `2**0 = 1`. It approaches `2**1 = 2`, but excludes `f = 1` because that would change the integer part. The default uniform sweep is exhaustive over the Q24 input representation. The calculation is processed in batches of 262144 inputs, so all models do not need to be stored for the entire sweep at once.

A separate boundary population includes the smallest positive fractional input `2**-24`, the largest fractional input `1 - 2**-24`, and every ROM address boundary with its adjacent Q24 inputs. Smaller power-of-two ROMs share the boundaries of the largest requested ROM. All boundary inputs remain inside `0 <= f < 1`.

The default ROM sizes are 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768 and 65536 stored entries. Each entry has 25 bits, including 24 fractional bits. These are entry counts, not FPGA LUT counts or physical BRAM block counts.

Choose ROM sizes and the encoded input step:

```powershell
python research/exponential_accuracy/compare_base_two_exponential.py --rom-sizes 16 64 256 1024 --step-size 8
```

`--step-size 8` and `--step-size 0b1000` mean the same increment. Plain numbers are decimal; binary numbers require the `0b` prefix. For example, `--step-size 1000` means decimal 1000, while `--step-size 0b1000` means decimal 8.

```powershell
python research/exponential_accuracy/compare_base_two_exponential.py --step-size 0b1000
```

A smaller step tests more inputs. The default step is 1, testing all 16777216 fractional bit patterns. Step 8 tests 2097152 inputs for a quicker sweep. Step 64 tests 262144 inputs. Inputs always start at zero and stay below one, even when the chosen step does not divide `2**24` exactly. The real exponent increment is `step_size / 2**24`. Boundary checks remain at adjacent Q24 values regardless of the uniform step.

Alternatively, choose `--fractional-samples COUNT` (or `--samples COUNT`). This option cannot be combined with `--step-size`. Sample-count mode encodes inputs as `floor(index * 2**24 / sample_count)`; for non-power-of-two counts, adjacent steps may differ by one encoded unit. `--bram-sizes` remains an alias for `--rom-sizes`. The integer exponent is always zero.

Choose the number of plot bins with `--bins`:

```powershell
python research/exponential_accuracy/compare_base_two_exponential.py --step-size 8 --bins 1024
```

The default is 256 bins. More bins show finer detail and average fewer errors together. Bin count changes only the error profile plot, not the inputs tested or accuracy statistics. A positive bin count is required; if it exceeds the sample count, the script uses one bin per sample. The plot caption and configuration record the actual count. With the default step of 1, 256 bins contain 65536 inputs each, while 1024 bins contain 16384 inputs each.

Use `--save-samples` to save each uniform fractional input and all fixed-point outputs to CSV. Use `--output-directory PATH` to choose another result folder. Use `--batch-size` to change processing batch size without changing the selected inputs or accuracy. Run `--help` for all options.

## Models

The ideal models approximate `2**f` as follows:

- Linear: `1 + f`.
- Cubic: `(1 + f) * (1 + (f*f - f)/4)`.
- ROM: `2**(address/entries)`, using the interval's starting address.

Ideal results exclude table rounding and fixed-point truncation. Every fixed-point comparison now retains 24 fractional bits in a signed 32-bit result, with the integer exponent held at zero. NumPy int64 containers hold integers during calculations; the script explicitly checks signed 32-bit bounds and raises an error rather than clipping or wrapping. The signed Q24 range is -128 to 128 - 2**-24, so estimates above 2 are preserved.

The research cubic is a modified Q24 variant: its linear term remains `2**24 + encoded_input`; the square is truncated back to Q24, the correction is formed in Q24, and their 64-bit product is shifted right by 24. It is not bit-identical to the original IP, which reduces the linear term to Q8. No integer shift or final shift by 16 is applied in this comparison.

The 1024-entry ROM reads the actual project memory file. Other sizes use `round_to_nearest(2**(address/entries) * 2**24)`, matching the sampling and rounding of that file. No HDL or memory files are modified. The same numerical ROM accuracy applies whether the table is implemented using BRAM, distributed ROM or other logic, provided its values and arithmetic remain the same.

## Maclaurin comparison

A Maclaurin series is the special case of a Taylor series centred at zero. All polynomials in this comparison use that expansion point.

Maclaurin polynomials are expanded about `f = 0`, using full-precision coefficients `ln(2)**k / k!`. Let `L = ln(2)`:

| Function or approximation | Formula |
|---|---|
| Actual function | `2**f` |
| Research linear | `1 + f` |
| Maclaurin linear | `1 + L*f` |
| Research cubic | `(1 + f)*(1 + (f*f - f)/4)` |
| Maclaurin cubic | `1 + L*f + L**2*f**2/2 + L**3*f**3/6` |
| Maclaurin degree 0 | `1` |
| Maclaurin degree 2 | `1 + L*f + L**2*f**2/2` |
| Maclaurin degree 4 | `1 + L*f + L**2*f**2/2 + L**3*f**3/6 + L**4*f**4/24` |

The script compares ideal formula references and fixed-point models on identical Q24 encoded inputs. Every fixed-point model outputs signed 32-bit Q24. Maclaurin and Sollya use signed 32-bit Q24 coefficients and intermediates, with 64-bit products shifted right by 24 after each multiplication and no final output precision reduction. Maclaurin coefficients use nearest rounding with ties to even; Sollya coefficients retain the supplied exact values. Research linear retains its full Q24 sum; ROM returns its stored Q24 entry; research cubic uses the modified Q24 variant described above. The matching Q24 FPGA study requires fresh measurements; archived Q8 resource counts are not reused.

## Results

PNG images are organised under two top-level folders: `results/images/01_ideal` and `results/images/02_fixed_point`. Both use the same structure:

```text
01_ideal/ or 02_fixed_point/
    00_formulas/
    01_signed_error/
    02_absolute_error/
    03_mean_absolute_error/
    04_maximum_absolute_error/
    05_accuracy_vs_model_size/
    06_accuracy_tables/
```

Each of the four error folders has these subfolders: `00_comparisons`, `01_research`, `02_maclaurin`, `03_sollya` and `04_rom`. Individual PNGs are grouped by model family. The comparisons subfolder contains `00_all_models_comparison.png` comparing every model. Signed error is the predicted value minus the reference: positive means overestimation and negative means underestimation. Absolute error is its magnitude. Mean and maximum folders aggregate individual absolute errors into equal-width display bins. Taking the mean of absolute errors prevents positive and negative errors cancelling.

Individual-input signed and absolute plots use no bin averaging. ROM plots include a zoom of the first four address intervals so their sawtooth shapes remain visible. Curves use 262144 uniform display inputs plus ROM boundaries and neighbours. Display-bin statistics therefore describe that plotting subset, rather than every tested input. Changing `--bins` changes the display profiles, not the accuracy tables.

The model-size folder groups its comparisons into `00_comparisons`, `02_maclaurin`, `03_sollya` and `04_rom`, with linear and logarithmic views together. Its four comparisons are:

- `01_rom_table_size.png`: error versus stored ROM entries.
- `02_maclaurin_degree.png`: error versus Maclaurin degree, from 0 through 4.
- `03_sollya_degree.png`: error versus Sollya degree, from 0 through 4.
- `04_polynomial_comparison.png`: Maclaurin, Sollya and research models together, versus degree.

Each comparison has separate mean and maximum absolute-error panels. A second image ending in `_log_scale.png` uses a logarithmic error axis so small errors remain visible. On that axis equal vertical spacing represents equal ratios, rather than equal differences. These use saved whole-test statistics, without plotting bins. Means use the uniform population; maxima take the larger result across uniform and directed-boundary populations. Research approximations appear only as individual points at degrees 1 and 3. No research quadratic or quartic is assumed.

`00_formulas` holds the same full formula image in both branches, describing the polynomials before intermediate/output truncation. The fixed-point branch also contains stored Sollya coefficient integers. `06_accuracy_tables` contains separate `01_absolute_error` and `02_percentage_error` subfolders, each holding a table for every model. Formula folders do not have extra nesting. Percentage errors divide by the unquantised positive reference. One fixed-point output step is `1/16777216`.

CSV data and run settings remain directly in `results`:

| File | Contents |
|---|---|
| `accuracy_summary.csv` | Full statistics by model, arithmetic domain and input population |
| `fractional_accuracy_comparison.csv` | Compact ideal and fixed-point accuracy comparison |
| `degree_accuracy_comparison.csv` | Polynomial mean and maximum errors by degree |
| `approximation_formulas.csv` | Approximation formulas |
| `sollya_q24_coefficients.csv` | Exact decimal, integer, hexadecimal and binary coefficients |
| `polynomial_accuracy_summary.csv` | Ideal polynomial statistics |
| `polynomial_value_samples.csv` | A reduced set of actual and approximate values |
| `worst_case_decimal_audit.csv` | Fixed-point worst-case candidates checked using 60-digit arithmetic |
| `bram_storage.csv` | Logical ROM storage sizes, retaining its historical filename |
| `run_configuration.json` | Input range, precision, sample counts and assumptions |
| `hardware_samples.csv` | Optional per-input fixed-point outputs |

The ideal domain is `mathematical_fractional`; the fixed-point domain is `hardware_fractional`. Both cover only the fractional exponent. Detailed CSV identifiers retain `bram_` for compatibility; image labels say ROM.

Regenerate just the plots from existing results, without running the complete accuracy sweep:

```powershell
python research/exponential_accuracy/plot_accuracy_results.py
```

The normal comparison script also generates this layout after completing its accuracy sweep. Plot-only regeneration preserves the saved numerical CSVs and run configuration. Old layouts are archived outside `images`, in `previous_combined_plots` and `previous_model_group_plots`.

An exhaustive sweep covers all representable Q24 inputs, rather than every real input. Reduced sweeps and display plots provide sampled maxima. Reference calculations use NumPy float64; the Decimal audit checks identified fixed-point worst cases, rather than every reference.

## Checks

```powershell
python -m unittest discover -s research/exponential_accuracy -p test_compare_base_two_exponential.py -v
```

The tests verify that comparison inputs stay inside the fractional field, check address-boundary coverage, compare vectorised arithmetic against independent integer calculations, and check ROM values against high-precision generation. Legacy Q8 helper validation also covers signed input edge cases; those cases are not included in the Q24 comparison. The Q24 comparison rejects inputs outside the fractional range.

Historical Q8 validation: on 13 November 2026, the three original arithmetic models matched the current HDL outputs for 6767 shared validation inputs using Vivado Simulator 2026.1 and the project's functional multiplier model. That validation used the existing 1024-entry ROM module and does not validate the modified Q24-output comparison against HDL. Alternative sizes were checked using Python integer arithmetic and high-precision table samples. HDL validation files are in `output/exponential_comparison_validation`.

## Supplied Sollya coefficients

Sollya used `fpminimax(2^x, degree, [|24,24,24,24,24|], [0;1], fixed, absolute)`. The supplied decimals are already exact fixed-point values with 24 fractional bits and all fit signed 32-bit storage. Multiplying by `16777216` gives the stored integer; no additional rounding is applied.

| Degree | Constant | f | f squared | f cubed | f to power 4 |
|---|---:|---:|---:|---:|---:|
| 0 | 25165824 | | | | |
| 1 | 16055197 | 16777216 | | | |
| 2 | 16818757 | 10922753 | 5771381 | | |
| 3 | 16775420 | 11684617 | 3763773 | 1328826 | |
| 4 | 16777278 | 11626044 | 4054016 | 867224 | 229808 |

Every fixed-point model uses 24 fractional input, coefficient, intermediate and output bits. The research cubic uses the modified Q24 linear term described above. These Python comparisons do not change the HDL.

## FPGA resource comparison

`fpga_synthesis_results` contains matching Q24 synthesizable RTL tops, LUT and DSP multiplication variants using the project multiplier, and distributed and BRAM ROM variants. The default target is 250 MHz on `xc7z020clg400-1`. Input has 24 fractional bits; output is signed 32-bit Q24, before the integer shift. The revised RTL passed functional simulation against these Python models. New Q24 resources and timings require a fresh measurement sweep. Previous Q8 measurements are preserved in `fpga_synthesis_results/archive/q8`. See [the FPGA synthesis instructions](../fpga_synthesis_results/README.md) for the complete command, result folders and separate synthesis-resource/routed-timing reporting.

The folder organisation changes presentation only. Saved accuracy statistics remain unchanged.
