# Three-neuron C/RTL validation

Run from `scalable_digital_neurons`:

```powershell
python sim/mut/three_neurons_1D/scripts/validate_three_neurons_1D.py --plot
```

The script compiles a trace generator around the original
`EfficientAnalogNeuron-SNNsims/C_fixedpoint/1D_Synfire/Synfire_1D_3neur_fixed.c`,
compiles and runs `tb_three_neurons_1D` with Vivado, and compares signed fixed-point
integer states after every network update. It checks all four neuron states and
both triangle states for each of the three neurons. The same external Q8 current
is applied to neuron 0 at the same numbered step in both models. The default
stimulus reproduces the original C experiment: 190,000 steps with an 80 pA
pulse on steps 60,000 through 140,000, inclusive.

The default C compilation uses 64-bit products, matching the RTL and the
original model when compiled on a platform with 64-bit `long`. Use
`--native-reference` to reproduce the source's native `long` width, which is
32-bit with the Windows GCC used here. `--wide-reference` remains available
as an explicit spelling of the default. Use separate `--output-dir` values
if retaining traces from both modes.

Outputs are `stimulus.txt`, `c_trace.csv`, and `hdl_trace.csv` in
`build/three_neurons_1D_validation/`. GCC and Vivado simulator tools are
required. The script finds Vivado in common Windows installation locations or
accepts `--vivado-bin`. `--input-values` reads one signed Q8 current per line.
With `--plot`, it saves `sim/mut/three_neurons_1D/images/vmem_comparison.png`.
The figure shows C and HDL Vmem for all three neurons plus the input current.
Use `--reference-only` to prepare C data without Vivado, then run the testbench
with the output directory as the simulator working directory and use
`--compare-only` to compare traces.

## RTL review findings

The startup synapse pass now computes the first current correctly. The
testbench checks its `1091` Q8 result, then counts completed neuron steps.
The 100-step strong pulse case passes for all 18 state values per step:

```powershell
python sim/mut/three_neurons_1D/scripts/validate_three_neurons_1D.py --steps 100 --pulse-start 1 --pulse-end 99 --pulse-height-q8 256000 --plot
```

The remaining test infrastructure issue is:

1. The existing `sim/mut/single_neuron/tb_single_neuron.sv` instantiates
   `single_neuron` with `step_ready` and `step_done`, which are no longer ports
   of that module. This is separate from the three-neuron validator and
   prevents the older single-neuron validation from testing current RTL.

The C reference itself also has non-void functions that reach the end without
returning a value. This wrapper uses their output arguments, as the original
program does. That C issue is independent of the RTL findings above.
