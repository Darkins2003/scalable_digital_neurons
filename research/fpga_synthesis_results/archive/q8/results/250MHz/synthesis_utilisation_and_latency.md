# Synthesis utilisation and latency

Target: PYNQ-Z2 FPGA, xc7z020clg400-1. Clock: 250 MHz (4 ns). Input: 24 fractional bits. Output: 8 fractional bits.

Resource counts are from synthesis, before implementation optimisation. Latency is the number of complete clock periods from the input acceptance edge to the corresponding output edge. Every design accepts one input per clock. Nanosecond latency is nominal at 250 MHz; failed timing rows do not meet that clock.

FFs are flip-flops. BRAM is measured in 36 Kbit tiles; 0.5 means one 18 Kbit block. Timing status is from routing of the standalone internal register paths.

| Design | LUTs | FFs | DSPs | BRAM tiles | Latency (cycles) | Latency at 250 MHz (ns) | Meets 250 MHz |
|---|---:|---:|---:|---:|---:|---:|:---:|
| research_linear_logic | 0 | 19 | 0 | 0 | 1 | 4 | Yes |
| research_cubic_lut | 2,315 | 2,667 | 0 | 0 | 17 | 68 | Yes |
| research_cubic_dsp | 73 | 497 | 8 | 0 | 17 | 68 | Yes |
| maclaurin_0_logic | 2 | 3 | 0 | 0 | 1 | 4 | Yes |
| maclaurin_1_lut | 1,237 | 1,282 | 0 | 0 | 9 | 36 | Yes |
| maclaurin_1_dsp | 1 | 197 | 4 | 0 | 9 | 36 | Yes |
| maclaurin_2_lut | 2,390 | 2,603 | 0 | 0 | 17 | 68 | Yes |
| maclaurin_2_dsp | 49 | 433 | 8 | 0 | 17 | 68 | Yes |
| maclaurin_3_lut | 3,548 | 3,923 | 0 | 0 | 25 | 100 | Yes |
| maclaurin_3_dsp | 102 | 668 | 12 | 0 | 25 | 100 | Yes |
| maclaurin_4_lut | 4,698 | 5,243 | 0 | 0 | 33 | 132 | Yes |
| maclaurin_4_dsp | 147 | 903 | 16 | 0 | 33 | 132 | Yes |
| sollya_0_logic | 2 | 3 | 0 | 0 | 1 | 4 | Yes |
| sollya_1_lut | 1,252 | 1,298 | 0 | 0 | 9 | 36 | Yes |
| sollya_1_dsp | 16 | 213 | 4 | 0 | 9 | 36 | Yes |
| sollya_2_lut | 2,395 | 2,619 | 0 | 0 | 17 | 68 | Yes |
| sollya_2_dsp | 54 | 449 | 8 | 0 | 17 | 68 | Yes |
| sollya_3_lut | 3,563 | 3,938 | 0 | 0 | 25 | 100 | Yes |
| sollya_3_dsp | 117 | 683 | 12 | 0 | 25 | 100 | Yes |
| sollya_4_lut | 4,700 | 5,259 | 0 | 0 | 33 | 132 | Yes |
| sollya_4_dsp | 149 | 919 | 16 | 0 | 33 | 132 | Yes |
| rom_16_distributed | 4 | 24 | 0 | 0 | 2 | 8 | Yes |
| rom_16_block | 0 | 7 | 0 | 0.5 | 2 | 8 | Yes |
| rom_32_distributed | 4 | 25 | 0 | 0 | 2 | 8 | Yes |
| rom_32_block | 0 | 8 | 0 | 0.5 | 2 | 8 | Yes |
| rom_64_distributed | 8 | 26 | 0 | 0 | 2 | 8 | Yes |
| rom_64_block | 0 | 9 | 0 | 0.5 | 2 | 8 | Yes |
| rom_128_distributed | 16 | 27 | 0 | 0 | 2 | 8 | Yes |
| rom_128_block | 0 | 10 | 0 | 0.5 | 2 | 8 | Yes |
| rom_256_distributed | 28 | 28 | 0 | 0 | 2 | 8 | Yes |
| rom_256_block | 0 | 11 | 0 | 0.5 | 2 | 8 | Yes |
| rom_512_distributed | 56 | 29 | 0 | 0 | 2 | 8 | Yes |
| rom_512_block | 0 | 12 | 0 | 0.5 | 2 | 8 | Yes |
| rom_1024_distributed | 91 | 30 | 0 | 0 | 2 | 8 | Yes |
| rom_1024_block | 0 | 13 | 0 | 1 | 2 | 8 | Yes |
| rom_2048_distributed | 166 | 31 | 0 | 0 | 2 | 8 | Yes |
| rom_2048_block | 0 | 14 | 0 | 0.5 | 2 | 8 | Yes |
| rom_4096_distributed | 259 | 32 | 0 | 0 | 2 | 8 | No |
| rom_4096_block | 0 | 15 | 0 | 2 | 2 | 8 | Yes |
| rom_8192_distributed | 345 | 39 | 0 | 0 | 2 | 8 | No |
| rom_8192_block | 0 | 16 | 0 | 2.5 | 2 | 8 | Yes |
| rom_16384_distributed | 354 | 34 | 0 | 0 | 2 | 8 | No |
| rom_16384_block | 0 | 17 | 0 | 4.5 | 2 | 8 | Yes |
| rom_32768_distributed | 424 | 41 | 0 | 0 | 2 | 8 | No |
| rom_32768_block | 0 | 18 | 0 | 9 | 2 | 8 | Yes |
| rom_65536_distributed | 476 | 43 | 0 | 0 | 2 | 8 | No |
| rom_65536_block | 0 | 19 | 0 | 18 | 2 | 8 | Yes |
