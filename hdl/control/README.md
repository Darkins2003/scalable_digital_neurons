# Control hardware

Each network configuration has its own control directory. The current
three-neuron register bank and AXI-Lite integration top are in
`three_neurons_1D/`.

The AXI-Lite adapter in `../../ip_repo/neuron_axil_1_0/hdl/` is shared. A new
configuration can reuse that adapter and add its own register map and thin top
module here. Shared register logic can be extracted when another configuration
needs the same behaviour.
