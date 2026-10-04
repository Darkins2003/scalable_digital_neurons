# AXI-Lite integration simulation

From the repository root:

```powershell
./sim/mut/three_neurons_1D/run_axil.ps1
```

The self-checking testbench is the AXI-Lite master. It writes the external
current and run control, waits for completed network updates, stops the
network, and reads all three membrane-voltage snapshots. A second
`three_neurons_1D` instance receives the intended current independently; the
testbench compares its completed-step count and all three voltages with the
values read over AXI-Lite. It also checks reset values, separate AXI address
and data arrival, byte strobes, and a read-only register.

The current register is signed with 8 fractional bits. The test uses `256000`,
representing `1000.0` in that format. Simulation output is generated under
the ignored `build/sim/three_neurons_1D_axil/` directory.

This runner compiles RTL source files directly. The Vivado IP package metadata
has not yet been refreshed for the adapter's new register-bus ports or 5-bit
address width. Refresh it before using the edited adapter as a catalog IP in a
block design. Vivado's original wizard BFM example targets placeholder
registers and does not exercise this integrated design.
