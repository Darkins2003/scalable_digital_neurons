# Three-neuron testcases

Run a testcase from the repository root by passing its `.svh` file to the
common runner:

```powershell
./sim/run_testcase.ps1 ./sim/mut/three_neurons_1D/testcases/tc_001_reset_access.svh
./sim/run_testcase.ps1 ./sim/mut/three_neurons_1D/testcases/tc_002_axil_integration.svh
./sim/run_testcase.ps1 ./sim/mut/three_neurons_1D/testcases/tc_003_commands.svh
./sim/run_testcase.ps1 ./sim/mut/three_neurons_1D/testcases/tc_004_hardware_updates.svh
./sim/run_testcase.ps1 ./sim/mut/three_neurons_1D/testcases/tc_010_c_reference_trace.svh
```

`tb_three_neurons_1D.sv` is the single shared testbench. It provides the clock,
reset, AXI signals, and pulse checks. The AXI-Lite manager and register access
tasks are included from `sim/common/`. `tc_001`, `tc_003`, and `tc_004` test the
register bank directly with controlled inputs. `tc_002` checks that AXI-Lite
writes reach the network and its outputs appear in the readback registers.
`tc_010` calls the Python C reference script from its `.svh` task, records the
RTL trace, then calls the script again to compare the traces. The runner
compiles the C reference executable before starting XSim.

The network waits for a START write after every reset. The tests confirm that
the register's START pulse reaches the network and that no steps occur before
it. STATUS bit 0 records whether START has been requested since reset. The
programmed current `256000` represents `1000.0` with eight
fractional bits.

To add a case, create `testcases/tc_###_description.svh` containing a task,
include it in the shared testbench, and add it to the testbench's selection
block. The common runner selects the case named by the file path and writes
outputs under `build/sim/three_neurons_1D/<testcase>/`.

The runner compiles RTL source files directly. Vivado IP package metadata
still needs refreshing before the edited AXI adapter is used as a catalog IP
in a block design.
