param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet('base_two_exp', 'single_neuron', 'three_neurons_1D')]
    [string]$Mut,

    [string]$VivadoBin = 'C:/AMDDesignTools/2026.1/Vivado/bin'
)

$ErrorActionPreference = 'Stop'
$testcaseDirectory = Join-Path $PSScriptRoot "mut/$Mut/testcases"
$testcases = @(Get-ChildItem -LiteralPath $testcaseDirectory -Filter 'tc_*.svh' -File | Sort-Object Name)
if ($testcases.Count -eq 0) {
    throw "No testcases found for $Mut in $testcaseDirectory"
}

$passed = [System.Collections.Generic.List[string]]::new()
$failed = [System.Collections.Generic.List[string]]::new()
$runner = Join-Path $PSScriptRoot 'run_testcase.ps1'

foreach ($testcase in $testcases) {
    Write-Host "Running $Mut/$($testcase.BaseName)"
    try {
        & $runner $testcase.FullName -VivadoBin $VivadoBin
        if ($LASTEXITCODE -ne 0) {
            throw "Runner exited with code $LASTEXITCODE"
        }
        $passed.Add($testcase.BaseName)
    } catch {
        $failed.Add($testcase.BaseName)
        Write-Host "FAIL: $($testcase.BaseName): $($_.Exception.Message)"
    }
}

Write-Host "Regression ${Mut}: $($passed.Count) passed, $($failed.Count) failed"
if ($failed.Count -gt 0) {
    Write-Host "Failed testcases: $($failed -join ', ')"
    exit 1
}

exit 0
