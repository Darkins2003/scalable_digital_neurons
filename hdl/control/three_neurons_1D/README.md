# Three-neuron 1D control registers

`three_neuron_regs_pkg.sv` defines each register's offset, reset value, and
access type. Each field contains its parent register descriptor, bit position,
width, and access type. The access types are RO, WO, RW, and W1T.

`three_neuron_registers.sv` implements the register bank for simulation and
hardware. `three_neuron_control_top.sv` joins it to the shared AXI-Lite adapter
and the `three_neurons_1D` network. All blocks use the same clock.

| Offset | Name | Access | Meaning |
|---|---|---|---|
| `0x00` | CONTROL | WO | START at bit 0 is a write-one-to-trigger command. Writing zero does nothing; reads return zero. Bit 1 is unused. |
| `0x04` | CURRENT | R/W | Signed 32-bit current applied to neuron 0, with 8 fractional bits. For example, `25600` represents `100.0`. Byte writes are supported. |
| `0x08` | STATUS | R | Bit 0 (`START_REQUESTED`) records whether START has been requested since reset; bit 1 indicates at least one reported network step. |
| `0x0C` | STEP_COUNT | R | Number of `step_valid` events since reset. |
| `0x10` | VMEM_0 | R | Neuron 0 membrane voltage snapshot from the last completed step. |
| `0x14` | VMEM_1 | R | Neuron 1 membrane voltage snapshot from the last completed step. |
| `0x18` | VMEM_2 | R | Neuron 2 membrane voltage snapshot from the last completed step. |

VMEM values have 24 fractional bits. Reset clears the current and step count,
and sets each VMEM snapshot to the initial membrane state. An accepted START
write generates a one-clock `ctrl_start` pulse. The wrapper connects it to
`three_neurons_1D`. After every reset, the network waits for START before
processing steps. Further START writes have no effect until the next reset.
The register offset range requires a 5-bit
local AXI-Lite address, covering 32 bytes.
