# Three-neuron 1D control registers

`three_neuron_registers.sv` is the shared register model for simulation and
hardware. `three_neuron_control_top.sv` joins it to the AXI-Lite adapter and
the existing `three_neurons_1D` network. All blocks use the same clock.

| Offset | Name | Access | Meaning |
|---|---|---|---|
| `0x00` | CONTROL | R/W | Bit 0 runs the network. Writing zero holds the network in reset; writing one starts it from its initial state. |
| `0x04` | CURRENT | R/W | Signed 32-bit current applied to neuron 0, with 8 fractional bits. For example, `25600` represents `100.0`. Byte writes are supported. |
| `0x08` | STATUS | R | Bit 0 is running; bit 1 indicates at least one completed network step. |
| `0x0C` | STEP_COUNT | R | Number of completed network steps since the last start. The startup synapse pass is excluded. |
| `0x10` | VMEM_0 | R | Neuron 0 membrane voltage snapshot from the last completed step. |
| `0x14` | VMEM_1 | R | Neuron 1 membrane voltage snapshot from the last completed step. |
| `0x18` | VMEM_2 | R | Neuron 2 membrane voltage snapshot from the last completed step. |

VMEM values have 24 fractional bits. Reset clears the current and step count,
and sets each VMEM snapshot to the initial membrane state. Stop retains the last
captured results for readback. The register offset range requires a 5-bit local
AXI-Lite address, covering 32 bytes.
