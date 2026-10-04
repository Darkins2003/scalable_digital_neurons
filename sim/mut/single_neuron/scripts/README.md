# Single-neuron C/HDL validation

These scripts validate the single-neuron RTL against the fixed-point C reference. Run commands below from the `scalable_digital_neurons` project root.

`sim/mut/single_neuron/scripts/validate_single_neuron.py` creates a step-indexed input file, compiles `single_neuron_reference.c`, runs the testbench with Vivado's `xvlog`, `xelab`, and `xsim`, and compares the four updated state integers after every `valid_out` completion. The testbench pulses `valid_in` once per step and checks `vmem_out_previous` against the prior step. GCC must be on `PATH`. The script searches for Vivado tools on `PATH` and in common Windows install locations. Pass `--vivado-bin` if Vivado is installed elsewhere.

Run the original C model's 100,000-step input pulse:

```powershell
python sim/mut/single_neuron/scripts/validate_single_neuron.py
```

For a shorter run that crosses the pulse boundary:

```powershell
python sim/mut/single_neuron/scripts/validate_single_neuron.py --steps 100 --pulse-start 20 --plot
```

By default, the script writes `stimulus.txt`, `c_trace.csv`, and `hdl_trace.csv` under `build/single_neuron_validation/`. The CSV files contain signed fixed-point integers for `Vmem`, `VK`, `Vg`, and `VNa` after each Euler step. With `--plot`, it saves `vmem_comparison.png` in `sim/mut/single_neuron/images/`. The comparison reports the first differing step and state value, then exits with a failure code.

For custom stimulus, provide a text file with one signed Q8 input current per line, without a header. The number of lines determines the number of steps:

```powershell
python sim/mut/single_neuron/scripts/validate_single_neuron.py --input-values my_currents.txt
```

If simulator commands are unavailable from the shell, generate the input and C trace first:

```powershell
python sim/mut/single_neuron/scripts/validate_single_neuron.py --reference-only
```

Run `tb_single_neuron` with `build/single_neuron_validation/` as its working directory so it reads `stimulus.txt` and writes `hdl_trace.csv`. Then compare:

```powershell
python sim/mut/single_neuron/scripts/validate_single_neuron.py --compare-only
```

The original C model multiplies with `long`. Its width is 32 bits on Windows and usually 64 bits on Linux. The reference trace generator preserves this platform-dependent behaviour and prints the width used. The HDL uses a 64-bit product, so a Windows C trace reveals a model difference. To compare against 64-bit multiplication behaviour, run:

```powershell
python sim/mut/single_neuron/scripts/validate_single_neuron.py --wide-reference --steps 100 --pulse-start 20
```

The default comparison uses the supplied C model as compiled on the current platform. Use a separate `--output-dir` to keep native and 64-bit reference traces side by side.
