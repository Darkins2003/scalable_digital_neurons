# Accuracy plot folders

The two main folders are 01_ideal and 02_fixed_point. Each contains:

- 01_signed_error: individual-input signed error. Positive means overestimate; negative means underestimate.
- 02_absolute_error: individual-input error magnitude.
- 03_mean_absolute_error: mean error magnitude per display bin.
- 04_maximum_absolute_error: maximum error magnitude per display bin.
- 05_accuracy_vs_model_size: whole-test error versus ROM entry count or polynomial degree, with separate mean and maximum panels. Each comparison has a linear-scale and a log-scale image.
- 06_accuracy_tables: whole-test percentage-error and absolute-error tables.

Each error category has 00_comparisons, 01_research, 02_maclaurin, 03_sollya and 04_rom subfolders. Individual plots are grouped by model family; 00_comparisons contains 00_all_models_comparison.png. ROM individual-input plots include a zoom of the first four address intervals. These use a display subset of 262144 uniform inputs plus ROM boundaries and neighbours; they do not replace the complete accuracy sweep.

The model-size folder also groups images into 00_comparisons, 02_maclaurin, 03_sollya and 04_rom, keeping linear and log-scale views together. The accuracy-table folder has 01_absolute_error and 02_percentage_error subfolders. Formula folders have no further nesting.

The model-size comparisons use the saved whole-test statistics, not display bins. ROM entries and polynomial degree use separate horizontal axes. Research models appear as individual points at degrees 1 and 3.

00_formulas contains the full formula table in both branches. The fixed-point branch also includes the stored Sollya coefficient table. The formula table describes the polynomials before intermediate/output truncation. Full data and run settings remain at the results root. The Q24 research cubic is a modified version retaining its linear term at Q24; previous Q8 FPGA measurements are separate.
