$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

if ($env:VERSION) {
    $Version = $env:VERSION
} else {
    $Version = python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])"
}

if ($env:ARCH) {
    $Arch = $env:ARCH
} else {
    $Arch = "x86_64"
}

if ($Arch -notin @("x86_64", "arm64")) {
    throw "Unsupported Windows architecture: $Arch"
}

$DistDir = if ($env:DIST_DIR) { $env:DIST_DIR } else { "dist/windows-release" }
$BuildDir = if ($env:BUILD_DIR) { $env:BUILD_DIR } else { "build/windows-release/$Arch" }

Remove-Item -Recurse -Force $BuildDir -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
New-Item -ItemType Directory -Force -Path $DistDir | Out-Null

python -m pip install --upgrade pip
python -m pip install ".[release]"

$PyInstallerExcludes = @(
    "--exclude-module", "astroid",
    "--exclude-module", "black",
    "--exclude-module", "docutils",
    "--exclude-module", "IPython",
    "--exclude-module", "ipykernel",
    "--exclude-module", "jedi",
    "--exclude-module", "jupyter_client",
    "--exclude-module", "matplotlib",
    "--exclude-module", "nbformat",
    "--exclude-module", "notebook",
    "--exclude-module", "numpy",
    "--exclude-module", "PIL",
    "--exclude-module", "PyQt5",
    "--exclude-module", "pytest",
    "--exclude-module", "sphinx",
    "--exclude-module", "tkinter",
    "--exclude-module", "zmq"
)

python -m PyInstaller `
    --clean `
    --noconfirm `
    --onefile `
    --console `
    --name google-finance-mcp `
    --distpath "$BuildDir/bin" `
    --workpath "$BuildDir/pyinstaller-work" `
    --specpath "$BuildDir/spec" `
    --copy-metadata mcp `
    --copy-metadata httpx `
    --copy-metadata anyio `
    $PyInstallerExcludes `
    packaging/pyinstaller/entrypoint.py

$Zip = "$DistDir/google-finance-mcp-$Version-windows-$Arch.zip"
Compress-Archive -Path "$BuildDir/bin/google-finance-mcp.exe" -DestinationPath $Zip -Force

$Hash = Get-FileHash $Zip -Algorithm SHA256
$Checksum = "$($Hash.Hash.ToLower())  $(Split-Path -Leaf $Zip)"
$Checksum | Set-Content "$DistDir/google-finance-mcp-$Version-windows-$Arch.sha256" -NoNewline

Write-Output "Built release artifacts:"
Write-Output "  $Zip"
Write-Output "  $DistDir/google-finance-mcp-$Version-windows-$Arch.sha256"
