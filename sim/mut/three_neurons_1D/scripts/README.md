# Three-neuron C/RTL validation

Run `tc_010` from the repository root:

```powershell
./sim/run_testcase.ps1 ./sim/mut/three_neurons_1D/testcases/tc_010_c_reference_trace.svh
```

Override the length and pulse without editing the testbench:

```powershell
./sim/run_testcase.ps1 three_neurons_1D tc_010_c_reference_trace -PlusArgs 'steps=12','pulse_start=2','pulse_end=7','pulse_height_q8=20480'
```

The defaults match the original C model: 190,000 steps, an inclusive pulse
from step 60,000 through 140,000, and a height of `20480` Q8 (`80.0`).
The shared engine is checked at startup, then each trace row is captured on
`step_valid`. State storage is indexed by state first, then neuron ID.
Input current is supplied ahead of the update that consumes it, since the
previous synapse pass prepares the next neuron input.

The testcase calls `validate_three_neurons_1D.py` to prepare `stimulus.txt` and
`c_trace.csv`. After recording `hdl_trace.csv`, it calls the script again to
compare all four neuron states and both triangle states for each neuron. The
Python script is a helper; `sim/run_testcase.ps1` is the simulation entry point.
The runner compiles the C reference and Vivado simulation. Results go to
`build/sim/three_neurons_1D/tc_010_c_reference_trace/`.

## MATLAB golden reference

Run the golden-reference testcase through the same simulation entry point:

```powershell
./sim/run_testcase.ps1 three_neurons_1D tc_011_golden_reference_trace
```

It runs the C/RTL checks above. After XSim exits, the runner uses
`compare_golden_reference.py` to compare the freshly generated RTL trace with
the saved MATLAB golden trace. It uses the same Python interpreter as preflight,
outside XSim's modified Python environment. The saved
MATLAB model and trace remain in `EfficientAnalogNeuron-SNNsims/MATLAB/Golden_reference`.
MATLAB does not need to be running.

For a shorter run with the original stimulus, append `-PlusArgs 'steps=70000'`.
The helper compares the first 70000 golden samples and labels the JSON as a
prefix comparison. Input still begins at step 60000; do not move the pulse
without generating a matching MATLAB reference.

Plots, trace files, state errors, spike metrics and source hashes are written to
`build/sim/three_neurons_1D/tc_011_golden_reference_trace/`. See `sim/README.md`
for the output list and the interpretation of PASS. The testcase measures the
fixed-point implementation's error; equality with the mathematical model is
not required.
