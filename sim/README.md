# Running MUT testcases

From the repository root, run one `.svh` testcase with one command:

```powershell
./sim/run_testcase.ps1 ./sim/mut/three_neurons_1D/testcases/tc_001_reset_access.svh
```

Run every `tc_*.svh` testcase for one MUT with:

```powershell
./sim/run_mut_regression.ps1 three_neurons_1D
```

The regression continues after a failure, reports the passed and failed counts,
and exits with a nonzero code if any testcase fails. The three-neuron regression
includes the full 190,000-step `tc_010_c_reference_trace` run.

Available cases:

| MUT | Testcase | Purpose |
| --- | --- | --- |
| `three_neurons_1D` | `tc_001_reset_access` | Reset values, CURRENT bit and byte writes, read-only registers |
| `three_neurons_1D` | `tc_002_axil_integration` | AXI and network integration |
| `three_neurons_1D` | `tc_003_commands` | START pulse, ignored writes, and status |
| `three_neurons_1D` | `tc_004_hardware_updates` | Step count, voltage snapshots, and reset |
| `three_neurons_1D` | `tc_010_c_reference_trace` | Three-neuron RTL against C |
| `single_neuron` | `tc_001_c_reference_trace` | Single-neuron RTL against C |
| `base_two_exp` | `tc_001_basic_exponents` | Cubic exponential pipeline stimuli |

Each MUT has one `tb_<mut>.sv` testbench. Each `tc_*.svh` file defines a named task
selected by the runner. The runner compiles the sources and invokes XSim with
the testcase name. C comparison testcases call their Python helper from inside
the `.svh` task before and after the HDL activity. The runner compiles the C
reference executables before XSim because GCC cannot complete when launched
from XSim's `$system` process in this setup. Results stay under
`build/sim/<mut>/<testcase>/`.

AXI-Lite testbenches can include `sim/common/axi_lite_manager.svh` for read and
write transactions, then `sim/common/axi_lite_register_methods.svh` for register
checks. The common runner adds `sim/common/` to every MUT's include path.
