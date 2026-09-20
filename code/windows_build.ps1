<#
Build, check, and package the Windows x64 release inside a Windows guest.

Run from any shell as the build user; the script sets up the MSVC x64
environment itself, installs the VC++ redistributable if missing, sets up the
project-local Rust toolchain, builds the native bundle from the shared model in
released/macos-arm64, runs the relocation check, and packages the Python wheel
and Node tarball. Results and logs are copied to the -Share folder (the Docker
guest's \\host.lan\Data by default). The Java classifier JAR is packaged on
the Mac with `java/build.py --classifier windows-x64 --package-only` and then
checked here with `java/check_bundle.py --classifier windows-x64`.

Start it detached so it survives an SSH disconnect, for example:

  schtasks /create /tn DGBuild /sc once /st 00:00 /f /tr "powershell -NoProfile -ExecutionPolicy Bypass -File C:\DecisionGate-build\code\windows_build.ps1 -Root C:\DecisionGate-build"
  schtasks /run /tn DGBuild

Processes started directly from an SSH session are killed when it closes.
#>
param(
    [Parameter(Mandatory=$true)][string]$Root,
    [string]$Share = '\\host.lan\Data',
    [string]$UpdateArchive = '',
    [switch]$RebuildNative
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
Set-Location $Root
New-Item -ItemType Directory -Force tools,reports | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$transcript = Join-Path $Root "reports\windows-resume-$stamp.log"
Start-Transcript -Path $transcript -Force

function Invoke-NativeLogged {
    param([string]$Executable, [string[]]$Arguments, [string]$Log, [int[]]$SuccessCodes = @(0))
    Get-Command $Executable -ErrorAction Stop | Out-Null
    New-Item -ItemType File -Force -Path $Log | Out-Null
    Write-Host "Running: $Executable $($Arguments -join ' ')"
    # Windows PowerShell 5.1 wraps redirected native stderr in ErrorRecords.
    # Cargo/uv use stderr for normal progress. Allow that stream here, while
    # retaining terminating PowerShell errors everywhere else in this script.
    $previous = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $global:LASTEXITCODE = 0
        & $Executable @Arguments *> $Log
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previous
    }
    if ($SuccessCodes -notcontains $exitCode) {
        Get-Content $Log -Tail 80 | ForEach-Object { Write-Host $_ }
        throw "Native command failed with exit code ${exitCode}: $Executable (log: $Log)"
    }
    Write-Host "Passed: $Executable (log: $Log)"
}

function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' +
        [Environment]::GetEnvironmentVariable('Path','User') +
        ";$Root\tools\rustup-launcher\bin;$env:USERPROFILE\.cargo\bin"
}

try {
    Refresh-Path
    $uv = (Get-Command uv -ErrorAction Stop).Source
    if (!(Test-Path code\Cargo.toml)) { throw "Missing source checkout at $Root" }
    if ($UpdateArchive) {
        Invoke-NativeLogged -Executable 'tar.exe' -Arguments @('-xzf',$UpdateArchive,'-C',$Root) -Log "$Root\reports\windows-update.log"
    }
    $vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    if (!(Test-Path $vswhere)) { throw 'Install Visual Studio Build Tools with C++ workload and Windows SDK first.' }
    $vs = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
    if (!$vs) { throw 'No installed MSVC x64 C++ tools found; wait for setup to complete.' }
    $vs = $vs.Trim()
    $devcmd = Join-Path $vs 'Common7\Tools\VsDevCmd.bat'
    $environmentScript = Join-Path $Root 'tools\windows-msvc-environment.cmd'
    @('@echo off',"call `"$devcmd`" -arch=x64 -host_arch=x64 >nul",'if errorlevel 1 exit /b 1','set') |
        Set-Content -Encoding ASCII $environmentScript
    # Environment variables can contain credentials. Keep this transient file
    # outside exported reports and delete it immediately after importing.
    $environmentLog = Join-Path $Root 'tools\windows-msvc-environment.txt'
    Invoke-NativeLogged -Executable $env:ComSpec -Arguments @('/d','/c',$environmentScript) -Log $environmentLog
    try {
        Get-Content $environmentLog | ForEach-Object {
            if ($_ -match '^([^=]+)=(.*)$') {
                [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
            }
        }
    } finally {
        Remove-Item $environmentLog -Force -ErrorAction SilentlyContinue
    }
    Get-Command cl.exe,dumpbin.exe,uv,node -ErrorAction Stop | Select-Object Name,Source
    if (!$env:WindowsSdkDir -or !(Test-Path $env:WindowsSdkDir)) { throw 'MSVC environment has no Windows SDK.' }
    # ONNX Runtime uses the VC++ runtime. Do not assume the compiler's own copy
    # establishes deployable System32 dependencies for the clean-PATH test.
    $system32 = Join-Path $env:SystemRoot 'System32'
    $runtimeMissing = @('vcruntime140.dll','vcruntime140_1.dll','msvcp140.dll') |
        Where-Object { !(Test-Path (Join-Path $system32 $_)) }
    if ($runtimeMissing.Count -gt 0) {
        $winget = (Get-Command winget -ErrorAction Stop).Source
        Invoke-NativeLogged -Executable $winget -Arguments @('install','--id','Microsoft.VCRedist.2015+.x64','--exact','--source','winget','--silent','--accept-source-agreements','--accept-package-agreements','--disable-interactivity') -Log "$Root\reports\windows-vcredist.log" -SuccessCodes @(0,3010,-1978335189)
        foreach ($name in $runtimeMissing) {
            if (!(Test-Path (Join-Path $system32 $name))) { throw "VC++ runtime still missing after installation: $name" }
        }
    }
    if (!(Test-Path tools\rust\bin\cargo.exe)) {
        Get-Command rustup -ErrorAction Stop | Out-Null
        Invoke-NativeLogged -Executable $uv -Arguments @('run','--python','3.12','code/setup.py') -Log "$Root\reports\windows-rust-setup.log"
    }
    $bundle = Join-Path $Root 'released\windows-x64'
    $alreadyBuilt = $false
    if (Test-Path "$bundle\build-checks.json") {
        $alreadyBuilt = (Get-Content "$bundle\build-checks.json" -Raw | ConvertFrom-Json).status -eq 'passed'
    }
    if ($RebuildNative -or !$alreadyBuilt) {
        if (Test-Path $bundle) {
            $backup = Join-Path $Root "tools\windows-native-before-$stamp-$([Guid]::NewGuid().ToString('N').Substring(0,8))"
            Move-Item $bundle $backup
            Write-Host "Preserved previous/incomplete bundle: $backup"
        }
        Invoke-NativeLogged -Executable $uv -Arguments @('run','--python','3.12','--with','onnxruntime==1.22.1','code/build.py','--model','released/macos-arm64','--output','released/windows-x64') -Log "$Root\reports\windows-build.log"
    } else {
        Write-Host 'Reusing previously tested native bundle; pass -RebuildNative to rebuild.'
    }
    Invoke-NativeLogged -Executable $uv -Arguments @('run','--python','3.12','tests/package_check.py','--bundle','released/windows-x64','--output','reports/windows-package.json') -Log "$Root\reports\windows-package.log"
    # Ensure the browser files copied into npm packages contain the model.
    if ((Test-Path released\web) -and !(Test-Path released\web\model.onnx)) {
        Copy-Item released\macos-arm64\model.onnx released\web\model.onnx
    }
    Invoke-NativeLogged -Executable $uv -Arguments @('run','--python','3.12','code/remote_packages.py') -Log "$Root\reports\windows-packages.log"
    $results = Join-Path $Share "windows-results-$stamp"
    New-Item -ItemType Directory -Force $results | Out-Null
    foreach ($path in @('released\windows-x64','released\python','released\node','reports')) {
        Copy-Item $path $results -Recurse -Force
    }
    "passed; results=$results" | Set-Content (Join-Path $Share 'windows-status.txt')
    Write-Host "All Windows build/package checks passed. Results: $results"
} catch {
    $_ | Format-List * -Force
    $failure = $_.ToString()
    try {
        $failure | Set-Content (Join-Path $Share 'windows-status.txt')
        Copy-Item reports (Join-Path $Share "windows-failure-$stamp") -Recurse -Force
    } catch {
        Write-Warning "Could not copy failure logs to share; local logs remain in $Root\reports"
    }
    throw
} finally {
    Stop-Transcript
    try { Copy-Item $transcript (Join-Path $Share "windows-resume-$stamp.log") -Force } catch { }
}
