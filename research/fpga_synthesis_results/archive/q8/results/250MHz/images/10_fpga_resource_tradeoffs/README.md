# FPGA resource, accuracy and latency comparisons

All 47 measured implementations are represented in the general plots. DSP plots select the nine DSP implementations; the block RAM plot selects the 13 block RAM ROMs. All resource counts come from synthesis utilisation reports, before implementation optimisation. Routed results are used only for timing status. There is no new Vivado run.

01: Mean absolute error versus LUTs, including DSP and BRAM counts beside points.
02: Maximum absolute error versus LUTs, including DSP and BRAM counts beside points.
03: Mean absolute error versus DSPs, DSP implementations only.
04: Mean absolute error versus BRAM, block RAM ROMs only.
05: Mean absolute error versus latency.
06: Latency versus LUTs, including DSP and BRAM counts beside points.
07: Mean absolute error versus flip-flops.

Overview panels include the whole selected population. Detail panels show only points within the stated error range. Each axis uses six equally spaced ticks and decimal labels. Detail panels use point numbers linked to the adjacent resource key. Coincident points share one label; more than three are labelled shared. Overview panels omit point labels to avoid crowding. The different implementations can have identical numerical accuracy and latency.

Tables use full model names, polynomial degrees, ROM entry counts and implementation types. Colours identify approximation families. Hollow points with red crosses failed routed setup timing at 250 MHz. Five LUT ROMs failed: 4096, 8192, 16384, 32768 and 65536 entries. Other designs passed setup and hold. This is standalone internal register timing, not an integrated board timing measurement or a maximum frequency search.

Latency is measured in full periods from the acceptance edge to the corresponding output edge. A three-register ROM pipeline has two elapsed periods under this convention. Every design accepts one input each clock when operated at a clock it meets.

Mean absolute error comes from the uniform hardware-fractional population in accuracy_summary.csv. Maximum absolute error is the largest reported error across its hardware-fractional populations. The accuracy configuration records exhaustive Q24 uniform coverage over 0 <= f < 1 (16777216 inputs), plus directed samples. These are errors of the Q8 output against exact 2^f, not errors against a rounded Q8 reference. Maximum error is across inputs, not a maximum per plotting bin. Scatter plots do not use bins. The numerically equivalent LUT and DSP variants share the same accuracy data; the RTL validation checked their agreement with the Python models.

Source: research/fpga_synthesis_results/results/250MHz/resource_comparison.csv
Regenerate from the project root: python research/fpga_synthesis_results/plot_resource_tradeoffs.py
