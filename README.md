# scalable_digital_neurons
Research and development of scalable Farquhar-Hasler digital neuron models for FPGA implementation

## Generate fixed-point RTL parameters

The floating-point reference values are stored in
`scripts/generate_neuron_params.py`. Generate the SystemVerilog package with:

```powershell
python scripts/generate_neuron_params.py
```

This writes `hdl/neuron_params_generated_pkg.sv`. Do not edit the generated
package by hand. Change the source values in the Python script and regenerate
it instead.

For project-specific parameters, use the hand-written package
`hdl/neuron_params_pkg.sv`. Add new parameters there so they are not
overwritten by the Python generator. Import both packages in a module:

```systemverilog
import neuron_params_generated_pkg::*;
import neuron_params_pkg::*;
```
