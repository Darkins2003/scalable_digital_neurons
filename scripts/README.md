# Parameter generation

`generate_neuron_params.py` converts the floating-point constants from the
original research team's `C_fixedpoint/Single_Neuron/neuron_fixed.c` into the
fixed-point integer values used by RTL.

## Source and attribution

The parameter values, fractional-bit formats, truncation behaviour, and
floating-to-fixed conversion method are reproduced from the supplied reference
implementation for:

> S. Bhattacharyya, P. R. Ayyappan and J. O. Hasler, "Towards Scalable Digital
> Modeling of Networks of Biorealistic Silicon Neurons," IEEE JETCAS, 2023.
> DOI: `10.1109/JETCAS.2023.3330069`

The Python file automates their existing conversion method so the generated
SystemVerilog constants are repeatable. It does not introduce a new fixed-point
conversion method.

Run it from the repository root:

```powershell
python scripts/generate_neuron_params.py
```

It writes:

```text
hdl/neuron_params_generated_pkg.sv
```

The conversion matches the C expression:

```c
(int)(value * (1 << fractional_bits))
```

The formats copied from the reference C model are:

| Values | Fractional bits |
|---|---:|
| Initial neuron states | 24 |
| Model constants and timestep | 24 |
| Matrix coefficients | 23 |
| Input current | 8 |

The script first reproduces the 32-bit C `float` values and then truncates
toward zero. This matches the behaviour of the reference C conversion for these
values and formats.

To check that the generated package has not become stale, run:

```powershell
python scripts/generate_neuron_params.py --check
```

Keep the floating-point source values in the Python script for traceability.
Use only the generated integer constants in synthesizable RTL.
