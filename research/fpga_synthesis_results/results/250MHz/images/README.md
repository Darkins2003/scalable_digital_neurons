# Q24 FPGA plots

00_tables: full results, plus tables grouped by family.
01_resource_usage: synthesis LUTs, registers, DSPs and BRAM.
02_latency: cycles and nanoseconds.
03_accuracy_vs_resources: mean and maximum absolute error versus each resource.
04_accuracy_vs_latency: mean and maximum absolute error versus latency.
05_accuracy_vs_model_size: increasing polynomial degree or ROM entries.
06_routed_timing: path delay and setup slack, kept separate from synthesis resources.

Most categories contain 00_all_models, 01_research, 02_maclaurin, 03_sollya and 04_rom. Accuracy scatter plots have numbered points and full-name keys. Error axes use logarithmic spacing to show small values. Every plot uses matching Q24 measurements. No ideal-resource branch exists because FPGA resources describe fixed-point hardware.
