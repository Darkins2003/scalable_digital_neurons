# FPGA comparison at 250.0 MHz

Completed designs: 47. Passing routed setup and hold timing: 42.

Resource utilisation is post-synthesis, before implementation optimisation. Setup/hold slack and timing status are post-route. Latency comes from the validated RTL pipeline. All designs use 24 fractional input bits, 8 fractional output bits, and accept one input per cycle. LUT, DSP and BRAM costs are separate resources, not interchangeable area units.

| Design | LUTs | Registers | DSPs | BRAM tiles | Latency cycles | Setup slack ns | Hold slack ns | Timing | Mapping |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| research_linear_logic | 0 | 19 | 0 | 0 | 1 | 2.728 | 0.081 | PASS | Matches |
| research_cubic_lut | 2315 | 2667 | 0 | 0 | 17 | 0.328 | 0.040 | PASS | Matches |
| research_cubic_dsp | 73 | 497 | 8 | 0 | 17 | 0.682 | 0.044 | PASS | Matches |
| maclaurin_0_logic | 2 | 3 | 0 | 0 | 1 | 2.802 | 0.136 | PASS | Matches |
| maclaurin_1_lut | 1237 | 1282 | 0 | 0 | 9 | 0.717 | 0.030 | PASS | Matches |
| maclaurin_1_dsp | 1 | 197 | 4 | 0 | 9 | 1.616 | 0.059 | PASS | Matches |
| maclaurin_2_lut | 2390 | 2603 | 0 | 0 | 17 | 0.244 | 0.034 | PASS | Matches |
| maclaurin_2_dsp | 49 | 433 | 8 | 0 | 17 | 0.704 | 0.045 | PASS | Matches |
| maclaurin_3_lut | 3548 | 3923 | 0 | 0 | 25 | 0.161 | 0.028 | PASS | Matches |
| maclaurin_3_dsp | 102 | 668 | 12 | 0 | 25 | 0.730 | 0.019 | PASS | Matches |
| maclaurin_4_lut | 4698 | 5243 | 0 | 0 | 33 | 0.278 | 0.034 | PASS | Matches |
| maclaurin_4_dsp | 147 | 903 | 16 | 0 | 33 | 0.657 | 0.027 | PASS | Matches |
| sollya_0_logic | 2 | 3 | 0 | 0 | 1 | 2.802 | 0.136 | PASS | Matches |
| sollya_1_lut | 1252 | 1298 | 0 | 0 | 9 | 0.867 | 0.054 | PASS | Matches |
| sollya_1_dsp | 16 | 213 | 4 | 0 | 9 | 0.931 | 0.058 | PASS | Matches |
| sollya_2_lut | 2395 | 2619 | 0 | 0 | 17 | 0.318 | 0.033 | PASS | Matches |
| sollya_2_dsp | 54 | 449 | 8 | 0 | 17 | 0.786 | 0.025 | PASS | Matches |
| sollya_3_lut | 3563 | 3938 | 0 | 0 | 25 | 0.152 | 0.037 | PASS | Matches |
| sollya_3_dsp | 117 | 683 | 12 | 0 | 25 | 0.846 | 0.019 | PASS | Matches |
| sollya_4_lut | 4700 | 5259 | 0 | 0 | 33 | 0.294 | 0.032 | PASS | Matches |
| sollya_4_dsp | 149 | 919 | 16 | 0 | 33 | 0.328 | 0.028 | PASS | Matches |
| rom_16_distributed | 4 | 24 | 0 | 0 | 2 | 2.412 | 0.059 | PASS | Matches |
| rom_16_block | 0 | 7 | 0 | 0.5 | 2 | 2.151 | 0.035 | PASS | Matches |
| rom_32_distributed | 4 | 25 | 0 | 0 | 2 | 2.181 | 0.052 | PASS | Matches |
| rom_32_block | 0 | 8 | 0 | 0.5 | 2 | 2.151 | 0.035 | PASS | Matches |
| rom_64_distributed | 8 | 26 | 0 | 0 | 2 | 2.384 | 0.076 | PASS | Matches |
| rom_64_block | 0 | 9 | 0 | 0.5 | 2 | 2.151 | 0.035 | PASS | Matches |
| rom_128_distributed | 16 | 27 | 0 | 0 | 2 | 1.978 | 0.063 | PASS | Matches |
| rom_128_block | 0 | 10 | 0 | 0.5 | 2 | 2.080 | 0.035 | PASS | Matches |
| rom_256_distributed | 28 | 28 | 0 | 0 | 2 | 1.062 | 0.067 | PASS | Matches |
| rom_256_block | 0 | 11 | 0 | 0.5 | 2 | 1.540 | 0.022 | PASS | Matches |
| rom_512_distributed | 56 | 29 | 0 | 0 | 2 | 0.812 | 0.073 | PASS | Matches |
| rom_512_block | 0 | 12 | 0 | 0.5 | 2 | 1.540 | 0.022 | PASS | Matches |
| rom_1024_distributed | 91 | 30 | 0 | 0 | 2 | 0.413 | 0.056 | PASS | Matches |
| rom_1024_block | 0 | 13 | 0 | 1 | 2 | 1.648 | 0.031 | PASS | Matches |
| rom_2048_distributed | 166 | 31 | 0 | 0 | 2 | 0.024 | 0.056 | PASS | Matches |
| rom_2048_block | 0 | 14 | 0 | 0.5 | 2 | 1.587 | 0.010 | PASS | Matches |
| rom_4096_distributed | 259 | 32 | 0 | 0 | 2 | -0.202 | 0.073 | FAIL | Matches |
| rom_4096_block | 0 | 15 | 0 | 2 | 2 | 1.474 | 0.040 | PASS | Matches |
| rom_8192_distributed | 345 | 39 | 0 | 0 | 2 | -0.704 | 0.066 | FAIL | Matches |
| rom_8192_block | 0 | 16 | 0 | 2.5 | 2 | 1.372 | 0.031 | PASS | Matches |
| rom_16384_distributed | 354 | 34 | 0 | 0 | 2 | -0.947 | 0.073 | FAIL | Matches |
| rom_16384_block | 0 | 17 | 0 | 4.5 | 2 | 1.499 | 0.069 | PASS | Matches |
| rom_32768_distributed | 424 | 41 | 0 | 0 | 2 | -1.522 | 0.071 | FAIL | Matches |
| rom_32768_block | 0 | 18 | 0 | 9 | 2 | 0.697 | 0.096 | PASS | Matches |
| rom_65536_distributed | 476 | 43 | 0 | 0 | 2 | -1.299 | 0.073 | FAIL | Matches |
| rom_65536_block | 0 | 19 | 0 | 18 | 2 | 0.249 | 0.061 | PASS | Matches |

The individual synthesis utilisation reports are authoritative for resource counts. Routed timing reports and checkpoints provide the timing results. Slack-derived frequency estimates are not verified maximum clock frequencies. These are standalone out-of-context core implementations, not full-system timing results.
