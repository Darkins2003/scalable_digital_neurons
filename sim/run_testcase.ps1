param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$MutOrPath,

    [Parameter(Position = 1)]
    [string]$Testcase,

    [string]$VivadoBin = 'C:/AMDDesignTools/2026.1/Vivado/bin'
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if ($Testcase) {
    $Mut = $MutOrPath
} else {
    $casePath = (Resolve-Path -LiteralPath $MutOrPath -ErrorAction Stop).Path
    $caseDirectory = Split-Path -Parent $casePath
    if ((Split-Path -Leaf $caseDirectory) -ne 'testcases' -or
        [IO.Path]::GetExtension($casePath) -ne '.svh') {
        throw 'Pass a testcase .svh file under sim/mut/<mut>/testcases.'
    }
    $Mut = Split-Path -Leaf (Split-Path -Parent $caseDirectory)
    $Testcase = [IO.Path]::GetFileNameWithoutExtension($casePath)
}
if ($Mut -notin @('base_two_exp', 'single_neuron', 'three_neurons_1D')) {
    throw "Unknown MUT: $Mut"
}
$mutDir = Join-Path $PSScriptRoot "mut/$Mut"
$caseFile = Join-Path $mutDir "testcases/$Testcase.svh"
if (-not (Test-Path -LiteralPath $caseFile -PathType Leaf)) {
    throw "Unknown testcase: $Mut/$Testcase. Choose a file in $mutDir/testcases."
}

$commonSources = @(
    'hdl/packages/neuron_params_generated_pkg.sv',
    'hdl/packages/neuron_params_pkg.sv',
    'hdl/packages/fixed_point_package.sv',
    'hdl/math/base_two_exponential_pipe_linear.sv',
    'hdl/math/base_two_exponential_pipe_cubic.sv'
)

switch ($Mut) {
    'base_two_exp' {
        $sourceNames = $commonSources + @('sim/mut/base_two_exp/tb_base_two_exp.sv')
    }
    'single_neuron' {
        $sourceNames = $commonSources + @(
            'hdl/math/compute_current_vector.sv',
            'hdl/math/matrix_mul_and_euler_update.sv',
            'hdl/neuron/single_neuron.sv',
            'sim/mut/single_neuron/tb_single_neuron.sv'
        )
    }
    'three_neurons_1D' {
        $sourceNames = @('hdl/packages/neuron_params_generated_pkg.sv',
                         'hdl/control/three_neurons_1D/three_neuron_regs_pkg.sv') +
                       $commonSources[1..($commonSources.Count - 1)] + @(
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
            'hdl/control/three_neurons_1D/three_neuron_registers.sv',
            'hdl/control/three_neurons_1D/three_neuron_control_top.sv',
            'sim/mut/three_neurons_1D/tb_three_neurons_1D.sv'
        )
    }
}

$sources = $sourceNames | ForEach-Object { Join-Path $repoRoot $_ }
$simDir = Join-Path $repoRoot "build/sim/$Mut/$Testcase"
New-Item -ItemType Directory -Path $simDir -Force | Out-Null
$top = "tb_$Mut"
$snapshot = "${top}_sim"

Push-Location $simDir
try {
    if ($Testcase -like '*c_reference_trace') {
        switch ($Mut) {
            'single_neuron' {
                & gcc -std=c11 -O2 -Wall -Wextra -fwrapv -DWIDE_MUL=1 `
                    (Join-Path $mutDir 'scripts/single_neuron_reference.c') `
                    -o (Join-Path $simDir 'single_neuron_reference.exe')
            }
            'three_neurons_1D' {
                & gcc -std=c11 -O0 -w -fwrapv -DWIDE_MUL `
                    (Join-Path $mutDir 'scripts/three_neurons_reference.c') -lm `
                    -o (Join-Path $simDir 'three_neurons_reference.exe')
            }
        }
        if ($LASTEXITCODE -ne 0) { throw 'C reference compilation failed' }
    }

    & (Join-Path $VivadoBin 'xvlog.bat') -sv --relax `
        -i (Join-Path $repoRoot 'sim/common') `
        -i (Join-Path $mutDir 'testcases') @sources
    if ($LASTEXITCODE -ne 0) { throw 'xvlog failed' }

    & (Join-Path $VivadoBin 'xelab.bat') $top -s $snapshot
    if ($LASTEXITCODE -ne 0) { throw 'xelab failed' }

    $simOutput = & (Join-Path $VivadoBin 'xsim.bat') $snapshot -runall -testplusarg $Testcase 2>&1
    $simExitCode = $LASTEXITCODE
    $simOutput | Write-Output
    if ($simExitCode -ne 0 -or ($simOutput -join "`n") -notmatch [regex]::Escape("PASS: $Testcase")) {
        throw "Testcase failed: $Mut/$Testcase"
    }
} finally {
    Pop-Location
}
