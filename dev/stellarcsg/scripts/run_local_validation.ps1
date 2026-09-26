param(
    [switch]$OpenMCAdapter
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$ValidationRoot = Join-Path $RepoRoot "build\stellarcsg-local-validation"
$CppBuild = Join-Path $ValidationRoot "cpp"
$DemoOutput = Join-Path $ValidationRoot "demo"
New-Item -ItemType Directory -Force -Path $ValidationRoot | Out-Null

cmake -S (Join-Path $RepoRoot "dev\stellarcsg") -B $CppBuild `
    -DCMAKE_BUILD_TYPE=Release `
    -DSTELLARCSG_ENABLE_HDF5=ON `
    -DSTELLARCSG_BUILD_TESTS=ON `
    -DSTELLARCSG_BUILD_BENCHMARKS=ON `
    -DSTELLARCSG_BUILD_TOOLS=ON
cmake --build $CppBuild --parallel
ctest --test-dir $CppBuild --output-on-failure
& (Join-Path $CppBuild "Release\stellarcsg_surface_benchmark.exe") |
    Tee-Object -FilePath (Join-Path $ValidationRoot "geometry_benchmark.json")

$PythonSource = Join-Path $RepoRoot "dev\stellarcsg\python"
if ($env:PYTHONPATH) {
    $env:PYTHONPATH = "$PythonSource;$env:PYTHONPATH"
} else {
    $env:PYTHONPATH = $PythonSource
}
python -m pytest -q (Join-Path $RepoRoot "dev\stellarcsg\python\tests")
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $DemoOutput
python -m stellarcsg.cli demo --output-dir $DemoOutput |
    Out-File -Encoding utf8 (Join-Path $ValidationRoot "demo_stdout.json")
$Inspector = Join-Path $CppBuild "stellarcsg_inspect_surface.exe"
if (-not (Test-Path $Inspector)) {
    $Inspector = Join-Path $CppBuild "Release\stellarcsg_inspect_surface.exe"
}
& $Inspector (Join-Path $DemoOutput "compiled_geometry.h5") `
    "/surfaces/plasma" 600 0 0 |
    Out-File -Encoding utf8 (Join-Path $ValidationRoot "python_to_cpp_surface_probe.json")

if ($OpenMCAdapter) {
    $OpenMCBuild = Join-Path $ValidationRoot "openmc-adapter"
    $Injector = Join-Path $RepoRoot "dev\stellarcsg\openmc_adapter\enable.cmake"
    cmake -S $RepoRoot -B $OpenMCBuild `
        -DCMAKE_BUILD_TYPE=Release `
        -DOPENMC_BUILD_TESTS=OFF `
        -DOPENMC_USE_OPENMP=ON `
        -DSTELLARCSG_BUILD_OPENMC_ADAPTER_TESTS=ON `
        "-DCMAKE_PROJECT_INCLUDE=$Injector"
    cmake --build $OpenMCBuild --target stellarcsg_openmc_adapter_tests --parallel
    ctest --test-dir $OpenMCBuild `
        -R stellarcsg_openmc_adapter_tests --output-on-failure
}

Write-Output "StellarCSG validation complete: $ValidationRoot"
