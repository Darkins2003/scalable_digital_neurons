param(
    [string]$VivadoBin = 'C:/AMDDesignTools/2026.1/Vivado/bin'
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$simDir = Join-Path $repoRoot 'build/sim/three_neurons_1D_axil'
New-Item -ItemType Directory -Path $simDir -Force | Out-Null

$sources = @(
    'hdl/packages/neuron_params_generated_pkg.sv',
    'hdl/packages/neuron_params_pkg.sv',
    'hdl/packages/fixed_point_package.sv',
    'hdl/math/base_two_exponential_pipe_linear.sv',
    'hdl/math/base_two_exponential_pipe_cubic.sv',
    'hdl/math/compute_current_vector.sv',
    'hdl/math/matrix_mul_and_euler_update.sv',
    'hdl/neuron/single_neuron.sv',
    'hdl/neuron/synaptic_triangular_generator.sv',
    'hdl/neuron/synaptic_pulse_generator.sv',
    'hdl/neuron/neuron_with_pulse_generator.sv',
    'hdl/network/synapse.sv',
    'hdl/network/three_neurons_1D.sv',
    'ip_repo/neuron_axil_1_0/hdl/neuron_axil_slave_lite_v1_0_S00_AXI.v',
    'ip_repo/neuron_axil_1_0/hdl/neuron_axil.v',
    'hdl/control/three_neuron_registers.sv',
    'hdl/control/three_neuron_control_top.sv',
    'sim/mut/three_neurons_1D/tb_three_neurons_1D_axil.sv'
) | ForEach-Object { Join-Path $repoRoot $_ }

Push-Location $simDir
try {
    & (Join-Path $VivadoBin 'xvlog.bat') -sv --relax @sources
    if ($LASTEXITCODE -ne 0) { throw 'xvlog failed' }
    & (Join-Path $VivadoBin 'xelab.bat') tb_three_neurons_1D_axil -s tb_three_neurons_1D_axil_sim
    if ($LASTEXITCODE -ne 0) { throw 'xelab failed' }
    & (Join-Path $VivadoBin 'xsim.bat') tb_three_neurons_1D_axil_sim -runall
    if ($LASTEXITCODE -ne 0) { throw 'xsim failed' }
} finally {
    Pop-Location
}
