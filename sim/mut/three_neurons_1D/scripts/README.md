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
