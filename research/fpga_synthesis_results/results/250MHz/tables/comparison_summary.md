# Q24 FPGA synthesis results at 250 MHz

Completed: 47 of 47 designs. Routed setup and hold timing passes: 40.

Input: 24 fractional bits, 0 <= f < 1. Output: signed 32-bit, 24 fractional bits. No integer shift or Q8 conversion. Resources: post-synthesis. Timing: post-route. Latency: elapsed clock periods from input acceptance to output. All designs accept one input per cycle.

| Model | LUTs | Registers | DSPs | BRAM tiles | Latency cycles | Latency ns | Mean absolute error | Maximum absolute error | Path delay ns | Setup slack ns | Hold slack ns | Routed timing | Mapping |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| Research linear (logic) | 0 | 51 | 0 | 0 | 1 | 4 | 0.057305 | 0.0860713 | 1.353 | 2.443 | 0.073 | PASS | Matches |
| Research cubic (DSP multiplication) | 73 | 529 | 8 | 0 | 17 | 68 | 0.00677579 | 0.013885 | 3.033 | 0.827 | 0.04 | PASS | Matches |
| Research cubic (LUT multiplication) | 2315 | 2699 | 0 | 0 | 17 | 68 | 0.00677579 | 0.013885 | 3.639 | 0.278 | 0.049 | PASS | Matches |
| Maclaurin, degree 0 (logic) | 2 | 3 | 0 | 0 | 1 | 4 | 0.442695 | 1 | 1.116 | 2.802 | 0.136 | PASS | Matches |
| Maclaurin, degree 1 (DSP multiplication) | 1 | 245 | 4 | 0 | 9 | 36 | 0.0961215 | 0.306853 | 2.414 | 1.488 | 0.042 | PASS | Matches |
| Maclaurin, degree 1 (LUT multiplication) | 1237 | 1330 | 0 | 0 | 9 | 36 | 0.0961215 | 0.306853 | 3.039 | 0.863 | 0.054 | PASS | Matches |
| Maclaurin, degree 2 (DSP multiplication) | 49 | 481 | 8 | 0 | 17 | 68 | 0.016046 | 0.0666263 | 3.048 | 0.866 | 0.039 | PASS | Matches |
| Maclaurin, degree 2 (LUT multiplication) | 2390 | 2651 | 0 | 0 | 17 | 68 | 0.016046 | 0.0666263 | 3.554 | 0.276 | 0.04 | PASS | Matches |
| Maclaurin, degree 3 (DSP multiplication) | 102 | 716 | 12 | 0 | 25 | 100 | 0.00216998 | 0.0111223 | 3.235 | 0.646 | 0.034 | PASS | Matches |
| Maclaurin, degree 3 (LUT multiplication) | 3548 | 3971 | 0 | 0 | 25 | 100 | 0.00216998 | 0.0111223 | 3.39 | 0.312 | 0.051 | PASS | Matches |
| Maclaurin, degree 4 (DSP multiplication) | 147 | 951 | 16 | 0 | 33 | 132 | 0.000246368 | 0.00150428 | 3.43 | 0.475 | 0.039 | PASS | Matches |
| Maclaurin, degree 4 (LUT multiplication) | 4698 | 5291 | 0 | 0 | 33 | 132 | 0.000246368 | 0.00150428 | 3.889 | 0.1 | 0.01 | PASS | Matches |
| Sollya, degree 0 (logic) | 2 | 3 | 0 | 0 | 1 | 4 | 0.254888 | 0.5 | 1.116 | 2.802 | 0.136 | PASS | Matches |
| Sollya, degree 1 (DSP multiplication) | 17 | 245 | 4 | 0 | 9 | 36 | 0.0262112 | 0.0430357 | 3.019 | 0.881 | 0.056 | PASS | Matches |
| Sollya, degree 1 (LUT multiplication) | 1253 | 1330 | 0 | 0 | 9 | 36 | 0.0262112 | 0.0430357 | 3.021 | 0.775 | 0.053 | PASS | Matches |
| Sollya, degree 2 (DSP multiplication) | 55 | 481 | 8 | 0 | 17 | 68 | 0.0015475 | 0.00247614 | 3.09 | 0.828 | 0.047 | PASS | Matches |
| Sollya, degree 2 (LUT multiplication) | 2396 | 2651 | 0 | 0 | 17 | 68 | 0.0015475 | 0.00247614 | 3.668 | 0.254 | 0.023 | PASS | Matches |
| Sollya, degree 3 (DSP multiplication) | 117 | 716 | 12 | 0 | 25 | 100 | 0.0000674416 | 0.000107148 | 3.289 | 0.574 | 0.043 | PASS | Matches |
| Sollya, degree 3 (LUT multiplication) | 3563 | 3971 | 0 | 0 | 25 | 100 | 0.0000674416 | 0.000107148 | 3.54 | 0.33 | 0.046 | PASS | Matches |
| Sollya, degree 4 (DSP multiplication) | 149 | 951 | 16 | 0 | 33 | 132 | 0.00000234213 | 0.00000386421 | 3.237 | 0.464 | 0.048 | PASS | Matches |
| Sollya, degree 4 (LUT multiplication) | 4700 | 5291 | 0 | 0 | 33 | 132 | 0.00000234213 | 0.00000386421 | 3.718 | -0.026 | 0.044 | FAIL | Matches |
| ROM, 16 entries (BRAM) | 0 | 7 | 0 | 0.5 | 2 | 8 | 0.0310243 | 0.0847934 | 1.166 | 2.151 | 0.035 | PASS | Matches |
| ROM, 16 entries (LUT memory) | 12 | 56 | 0 | 0 | 2 | 8 | 0.0310243 | 0.0847934 | 1.703 | 2.218 | 0.066 | PASS | Matches |
| ROM, 32 entries (BRAM) | 0 | 8 | 0 | 0.5 | 2 | 8 | 0.0155686 | 0.0428558 | 1.166 | 2.151 | 0.035 | PASS | Matches |
| ROM, 32 entries (LUT memory) | 12 | 57 | 0 | 0 | 2 | 8 | 0.0155686 | 0.0428558 | 1.704 | 2.13 | 0.058 | PASS | Matches |
| ROM, 64 entries (BRAM) | 0 | 9 | 0 | 0.5 | 2 | 8 | 0.00779837 | 0.0215439 | 1.166 | 2.151 | 0.035 | PASS | Matches |
| ROM, 64 entries (LUT memory) | 24 | 58 | 0 | 0 | 2 | 8 | 0.00779837 | 0.0215439 | 2.335 | 1.585 | 0.065 | PASS | Matches |
| ROM, 128 entries (BRAM) | 0 | 10 | 0 | 0.5 | 2 | 8 | 0.00390269 | 0.0108011 | 1.24 | 2.08 | 0.035 | PASS | Matches |
| ROM, 128 entries (LUT memory) | 48 | 59 | 0 | 0 | 2 | 8 | 0.00390269 | 0.0108011 | 2.156 | 1.678 | 0.055 | PASS | Matches |
| ROM, 256 entries (BRAM) | 0 | 11 | 0 | 0.5 | 2 | 8 | 0.00195221 | 0.00540779 | 1.778 | 1.54 | 0.022 | PASS | Matches |
| ROM, 256 entries (LUT memory) | 92 | 60 | 0 | 0 | 2 | 8 | 0.00195221 | 0.00540779 | 2.713 | 1.122 | 0.048 | PASS | Matches |
| ROM, 512 entries (BRAM) | 0 | 12 | 0 | 0.5 | 2 | 8 | 0.000976312 | 0.00270567 | 1.778 | 1.54 | 0.022 | PASS | Matches |
| ROM, 512 entries (LUT memory) | 200 | 61 | 0 | 0 | 2 | 8 | 0.000976312 | 0.00270567 | 3.412 | 0.452 | 0.057 | PASS | Matches |
| ROM, 1,024 entries (BRAM) | 0 | 13 | 0 | 1 | 2 | 8 | 0.000488196 | 0.00135324 | 1.668 | 1.648 | 0.031 | PASS | Matches |
| ROM, 1,024 entries (LUT memory) | 364 | 74 | 0 | 0 | 2 | 8 | 0.000488196 | 0.00135324 | 3.543 | 0.29 | 0.056 | PASS | Matches |
| ROM, 2,048 entries (BRAM) | 0 | 14 | 0 | 1.5 | 2 | 8 | 0.000244096 | 0.000676728 | 1.851 | 1.463 | 0.024 | PASS | Matches |
| ROM, 2,048 entries (LUT memory) | 712 | 89 | 0 | 0 | 2 | 8 | 0.000244096 | 0.000676728 | 3.976 | -0.145 | 0.064 | FAIL | Matches |
| ROM, 4,096 entries (BRAM) | 0 | 15 | 0 | 3 | 2 | 8 | 0.000122037 | 0.000338353 | 2.144 | 1.173 | 0.034 | PASS | Matches |
| ROM, 4,096 entries (LUT memory) | 1357 | 145 | 0 | 0 | 2 | 8 | 0.000122037 | 0.000338353 | 4.169 | -0.254 | 0.073 | FAIL | Matches |
| ROM, 8,192 entries (BRAM) | 0 | 16 | 0 | 6.5 | 2 | 8 | 0.0000610046 | 0.000169135 | 1.758 | 1.445 | 0.069 | PASS | Matches |
| ROM, 8,192 entries (LUT memory) | 2681 | 187 | 0 | 0 | 2 | 8 | 0.0000610046 | 0.000169135 | 4.864 | -0.991 | 0.053 | FAIL | Matches |
| ROM, 16,384 entries (BRAM) | 0 | 17 | 0 | 12.5 | 2 | 8 | 0.0000304874 | 0.000084556 | 2.92 | 0.266 | 0.094 | PASS | Matches |
| ROM, 16,384 entries (LUT memory) | 5276 | 318 | 0 | 0 | 2 | 8 | 0.0000304874 | 0.000084556 | 5.318 | -1.356 | 0.063 | FAIL | Matches |
| ROM, 32,768 entries (BRAM) | 0 | 18 | 0 | 25 | 2 | 8 | 0.0000152289 | 0.0000422501 | 2.855 | 0.385 | 0.095 | PASS | Matches |
| ROM, 32,768 entries (LUT memory) | 10177 | 154 | 0 | 0 | 2 | 8 | 0.0000152289 | 0.0000422501 | 5.782 | -1.941 | 0.065 | FAIL | Matches |
| ROM, 65,536 entries (BRAM) | 0 | 51 | 0 | 50 | 2 | 8 | 0.00000759957 | 0.0000210975 | 2.927 | 0.219 | 0.09 | PASS | Matches |
| ROM, 65,536 entries (LUT memory) | 18917 | 120 | 0 | 0 | 2 | 8 | 0.00000759957 | 0.0000210975 | 6.502 | -2.796 | 0.069 | FAIL | Matches |

Accuracy means use the uniform Q24 population; maxima include directed boundaries. Errors compare the output against unquantised 2^f. LUT/DSP and distributed/BRAM variants share accuracy only after bit-exact RTL validation. The research cubic retains its Q24 linear term.

The achievable frequency has not been established by passing this clock. Compare routed path delays and repeat measurements with tighter constraints. Slack-derived frequency is an estimate, not a verified maximum. These are standalone cores, not integrated system timing.
