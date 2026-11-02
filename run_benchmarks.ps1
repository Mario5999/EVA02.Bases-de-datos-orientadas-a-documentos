param(
    [switch]$ConfirmRun,
    [int]$StartIndex = 0,
    [int]$MaxRuns = 108,
    [string]$OutputCsv = ""
)

$ErrorActionPreference = "Stop"

function Invoke-Docker {
    param(
        [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
        [string[]]$DockerArguments
    )

    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & docker @DockerArguments
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
}

if ([string]::IsNullOrWhiteSpace($OutputCsv)) {
    $OutputCsv = Join-Path $PSScriptRoot "mediciones.csv"
}

$python = Join-Path $PSScriptRoot "venv\Scripts\python.exe"
$runner = Join-Path $PSScriptRoot "benchmark_runner\runner.py"
$runStatePath = Join-Path $PSScriptRoot "run_benchmarks.current.json"
$incidentLogPath = Join-Path $PSScriptRoot "mediciones_incidencias.log"
$expectedHeader = "timestamp_epoch,engine,profile,query_id,concurrency,run_number,throughput_qps,latency_p50_ms,latency_p95_ms,latency_p99_ms,cpu_throttled_seconds,max_rss_mb,disk_spill,status"
$profiles = @(
    @{ Name = "PROFILE_A_BASELINE"; CPUs = "4.0"; Memory = "4096M" },
    @{ Name = "PROFILE_B_MEDIUM"; CPUs = "2.0"; Memory = "2048M" },
    @{ Name = "PROFILE_C_SEVERE"; CPUs = "1.0"; Memory = "1024M" }
)
$engines = @(
    @{ Name = "mongodb"; Service = "mongodb"; OtherService = "postgres"; Container = "it2id_mongodb" },
    @{ Name = "postgresql"; Service = "postgres"; OtherService = "mongodb"; Container = "it2id_postgres" }
)
$cases = New-Object System.Collections.Generic.List[object]

foreach ($engine in $engines) {
    foreach ($profile in $profiles) {
        foreach ($concurrency in @(1, 10, 50)) {
            foreach ($query in @("q1", "q2")) {
                if ($query -eq "q1") {
                    $variant = ""
                }
                elseif ($engine.Name -eq "mongodb") {
                    $variant = "allowDiskUse_false"
                }
                else {
                    $variant = "work_mem_4MB"
                }

                foreach ($runNumber in @(1, 2, 3)) {
                    $cases.Add([pscustomobject]@{
                        Engine = $engine
                        Profile = $profile
                        Concurrency = $concurrency
                        Query = $query
                        Variant = $variant
                        RunNumber = $runNumber
                    })
                }
            }
        }
    }
}

if ($cases.Count -ne 108) {
    throw "Internal matrix error: expected 108 runs, got $($cases.Count)."
}

$cellGroups = @($cases | Group-Object {
    "$($_.Engine.Name)|$($_.Profile.Name)|$($_.Query)|$($_.Concurrency)"
})
if ($cellGroups.Count -ne 36) {
    throw "Internal matrix error: expected 36 cells, got $($cellGroups.Count)."
}
if (@($cellGroups | Where-Object { $_.Count -ne 3 }).Count -gt 0) {
    throw "Internal matrix error: every cell must have exactly 3 repetitions."
}

Write-Host "Matriz oficial del playbook: $($cases.Count) corridas en 36 celdas (3 repeticiones por celda)."
Write-Host "Factores: 2 motores x 3 perfiles x Q1/Q2 x 3 concurrencias x 3 repeticiones."
Write-Host "Q2 fija MongoDB allowDiskUse=false y PostgreSQL work_mem=4MB; no se agregan variantes."
Write-Host "Q2_SORT_ALL y las variantes altas de memoria quedan fuera de esta matriz."
Write-Host "Duración mínima estimada: 12 h 36 min (sin contar reinicios ni preparación)."
Write-Host "Salida: $OutputCsv"

if (-not $ConfirmRun) {
    Write-Host "No se ejecutó nada. Agrega -ConfirmRun para iniciar; usa -StartIndex y -MaxRuns para dividir la matriz."
    return
}

if ($StartIndex -lt 0 -or $StartIndex -ge $cases.Count) {
    throw "-StartIndex debe estar entre 0 y $($cases.Count - 1)."
}
if ($MaxRuns -lt 1) {
    throw "-MaxRuns debe ser mayor que cero."
}
if (-not (Test-Path $python)) {
    throw "No se encontró el entorno virtual del proyecto: $python"
}
if (-not (Test-Path $runner)) {
    throw "No se encontró el runner: $runner"
}

$allCases = $cases.ToArray()
$selectedCases = $allCases | Select-Object -Skip $StartIndex -First $MaxRuns
$completed = @{}

function Get-RunKey($row) {
    return "$($row.engine)|$($row.profile)|$($row.query_id)|$($row.concurrency)|$($row.run_number)"
}

function Write-Incident([string]$Message) {
    $entry = "{0} {1}" -f (Get-Date -Format "o"), $Message
    Add-Content -Path $incidentLogPath -Value $entry -Encoding UTF8
    Write-Warning $entry
}

function Write-AbortedCsvRow($Case, [string]$Status) {
    $epoch = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    $row = "$epoch,$($Case.Engine.Name),$($Case.Profile.Name),$($Case.Query),$($Case.Concurrency),$($Case.RunNumber),,,,,,,,$Status"
    Add-Content -Path $OutputCsv -Value $row -Encoding ASCII
}

function Write-AbortedFromMarker($Marker) {
    $parts = $Marker.key -split "\|", 5
    if ($parts.Count -ne 5) {
        throw "Invalid interrupted-run marker key: $($Marker.key)"
    }
    $alreadyRecorded = $false
    if (Test-Path $OutputCsv) {
        $matchingRows = @(Import-Csv -Path $OutputCsv | Where-Object {
            (Get-RunKey $_) -eq $Marker.key
        })
        $alreadyRecorded = $matchingRows.Count -gt 0
    }
    if (-not $alreadyRecorded) {
        $case = [pscustomobject]@{
            Engine = [pscustomobject]@{ Name = $parts[0] }
            Profile = [pscustomobject]@{ Name = $parts[1] }
            Query = $parts[2]
            Concurrency = $parts[3]
            RunNumber = $parts[4]
        }
        Write-AbortedCsvRow $case "ABORTED"
    }
}

if (Test-Path $runStatePath) {
    try {
        $previousRun = Get-Content -Path $runStatePath -Raw | ConvertFrom-Json
        Write-Incident "Detected interrupted run for $($previousRun.key) at stage '$($previousRun.stage)'. It will be retried unless a SUCCESS row exists."
        Write-AbortedFromMarker $previousRun
        Remove-Item -LiteralPath $runStatePath
    }
    catch {
        Write-Incident "Could not parse prior run marker '$runStatePath': $($_.Exception.Message)"
        throw
    }
}

if (Test-Path $OutputCsv) {
    $actualHeader = Get-Content -Path $OutputCsv -TotalCount 1
    if ($actualHeader -ne $expectedHeader) {
        throw "El CSV existente no tiene el encabezado reglamentario. No se modificó: $OutputCsv"
    }
    foreach ($row in (Import-Csv -Path $OutputCsv)) {
        $key = Get-RunKey $row
        if ($row.status -eq "SUCCESS") {
            $completed[$key] = $true
        }
    }
}

$initialRunning = @(Invoke-Docker -DockerArguments @("compose", "ps", "--services", "--filter", "status=running"))
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo consultar el estado de Docker Compose."
}

try {
    Invoke-Docker -DockerArguments @("compose", "pull")
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudieron descargar las imágenes Compose."
    }
    Invoke-Docker -DockerArguments @("pull", "alpine:latest")
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo descargar alpine:latest para limpiar la caché."
    }

    $env:CPUS_LIMIT = "4.0"
    $env:MEM_LIMIT = "4096M"
    Invoke-Docker -DockerArguments @("compose", "up", "-d", "prometheus", "cadvisor", "node-exporter", "mongodb", "postgres")
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo iniciar el entorno Docker."
    }
    & $python (Join-Path $PSScriptRoot "scripts\audit_databases.py")
    if ($LASTEXITCODE -ne 0) {
        throw "La auditoría inicial de bases falló; no se iniciaron benchmarks."
    }

    $targetsReady = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            $targets = Invoke-RestMethod "http://localhost:9090/api/v1/targets" -TimeoutSec 5
            $active = @($targets.data.activeTargets | Where-Object { $_.health -ne "up" })
            if ($targets.data.activeTargets.Count -ge 3 -and $active.Count -eq 0) {
                $targetsReady = $true
                break
            }
        }
        catch {
            Start-Sleep -Seconds 2
        }
        Start-Sleep -Seconds 2
    }
    if (-not $targetsReady) {
        throw "Prometheus no tiene los tres objetivos de scraping en estado up."
    }

    if (-not (Test-Path $OutputCsv)) {
        Set-Content -Path $OutputCsv -Value $expectedHeader -Encoding ASCII
    }

    $runCount = 0
    foreach ($case in $selectedCases) {
        $key = "$($case.Engine.Name)|$($case.Profile.Name)|$($case.Query)|$($case.Concurrency)|$($case.RunNumber)"
        if ($completed.ContainsKey($key)) {
            Write-Host "Omitiendo corrida ya registrada: $key"
            continue
        }

        @{
            key = $key
            stage = "preparing"
            started_at = (Get-Date).ToString("o")
        } | ConvertTo-Json | Set-Content -Path $runStatePath -Encoding UTF8

        $env:CPUS_LIMIT = $case.Profile.CPUs
        $env:MEM_LIMIT = $case.Profile.Memory
        Invoke-Docker -DockerArguments @("compose", "stop", $case.Engine.OtherService)
        if ($LASTEXITCODE -ne 0) {
            throw "No se pudo detener el motor que no participa: $($case.Engine.OtherService)"
        }
        Invoke-Docker -DockerArguments @("compose", "up", "-d", "--force-recreate", $case.Engine.Service)
        if ($LASTEXITCODE -ne 0) {
            throw "No se pudo aplicar el perfil $($case.Profile.Name) a $($case.Engine.Name)."
        }

        $ready = $false
        for ($attempt = 0; $attempt -lt 60; $attempt++) {
            if ($case.Engine.Name -eq "mongodb") {
                $count = Invoke-Docker -DockerArguments @("exec", $case.Engine.Container, "mongosh", "--quiet", "benchmark_db", "--eval", "db.orders.countDocuments()")
            }
            else {
                $count = Invoke-Docker -DockerArguments @("exec", $case.Engine.Container, "psql", "-U", "benchmark", "-d", "benchmark_db", "-Atc", "SELECT COUNT(*) FROM orders;")
            }
            if ($LASTEXITCODE -eq 0 -and "$count".Trim() -eq "500000") {
                $ready = $true
                break
            }
            Start-Sleep -Seconds 2
        }
        if (-not $ready) {
            Write-Incident "ABORTED ${key}: engine did not become ready with 500000 records."
            Write-AbortedCsvRow $case "ABORTED"
            Remove-Item -LiteralPath $runStatePath -ErrorAction SilentlyContinue
            throw "$($case.Engine.Name) no quedó listo con 500,000 registros."
        }

        $metricReady = $false
        $metricQuery = "container_cpu_cfs_throttled_seconds_total{name=~`".*$($case.Engine.Container).*`"}"
        for ($attempt = 0; $attempt -lt 30; $attempt++) {
            try {
                $metricResult = Invoke-RestMethod (
                    "http://localhost:9090/api/v1/query?query=" +
                    [uri]::EscapeDataString($metricQuery)
                ) -TimeoutSec 5
                if ($metricResult.status -eq "success" -and $metricResult.data.result.Count -gt 0) {
                    $metricReady = $true
                    break
                }
            }
            catch {
                Start-Sleep -Seconds 2
            }
            Start-Sleep -Seconds 2
        }
        if (-not $metricReady) {
            Write-Incident "ABORTED ${key}: Prometheus cgroup metric was unavailable."
            Write-AbortedCsvRow $case "ABORTED"
            Remove-Item -LiteralPath $runStatePath -ErrorAction SilentlyContinue
            throw "Prometheus no publicó métricas cgroups para $($case.Engine.Container)."
        }

        Write-Host "[$($runCount + 1)] $key variante=$($case.Variant)"
        Invoke-Docker -DockerArguments @("run", "--rm", "--privileged", "alpine:latest", "sh", "-c", "sync; echo 3 > /proc/sys/vm/drop_caches")
        if ($LASTEXITCODE -ne 0) {
            Write-Incident "ABORTED ${key}: cache flush failed."
            Write-AbortedCsvRow $case "ABORTED"
            Remove-Item -LiteralPath $runStatePath -ErrorAction SilentlyContinue
            throw "Falló la limpieza de caché. No se continuará con resultados no comparables."
        }

        @{
            key = $key
            stage = "runner"
            started_at = (Get-Date).ToString("o")
        } | ConvertTo-Json | Set-Content -Path $runStatePath -Encoding UTF8

        $runnerExitCode = 0
        $runnerArguments = @(
            "--engine", $case.Engine.Name,
            "--query", $case.Query,
            "--concurrency", [string]$case.Concurrency,
            "--duration", "300",
            "--warmup", "60",
            "--profile", $case.Profile.Name,
            "--run-number", [string]$case.RunNumber,
            "--output-csv", $OutputCsv
        )
        if (-not [string]::IsNullOrWhiteSpace($case.Variant)) {
            $runnerArguments += @("--variant", $case.Variant)
        }
        $runnerErrorPath = Join-Path $env:TEMP ("benchmark-runner-{0}.stderr.log" -f [guid]::NewGuid())
        $previousErrorActionPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = "Continue"
            & $python $runner @runnerArguments 2> $runnerErrorPath
            $runnerExitCode = $LASTEXITCODE
        }
        finally {
            $ErrorActionPreference = $previousErrorActionPreference
            Start-Sleep -Seconds 60
        }
        if ((Test-Path $runnerErrorPath) -and (Get-Item $runnerErrorPath).Length -gt 0) {
            $runnerErrors = @(Get-Content -Path $runnerErrorPath)
            Write-Incident "Runner stderr for ${key}: $($runnerErrors -join ' | ')"
            Write-Host "Runner stderr:"
            $runnerErrors | ForEach-Object { Write-Host $_ }
        }
        Remove-Item -LiteralPath $runnerErrorPath -ErrorAction SilentlyContinue
        $matchingRows = @(Import-Csv -Path $OutputCsv | Where-Object {
            (Get-RunKey $_) -eq $key
        } | Sort-Object { [long]$_.timestamp_epoch })
        $latestRow = if ($matchingRows.Count -gt 0) { $matchingRows[-1] } else { $null }

        if ($null -eq $latestRow) {
            Write-Incident "ABORTED ${key}: runner exited $runnerExitCode without writing a CSV result."
            Write-AbortedCsvRow $case "ABORTED"
            Remove-Item -LiteralPath $runStatePath -ErrorAction SilentlyContinue
            continue
        }
        if ($runnerExitCode -ne 0 -or $latestRow.status -ne "SUCCESS") {
            Write-Incident "FAILED ${key}: runner_exit=$runnerExitCode, status=$($latestRow.status). The row remains retryable on resume."
            Remove-Item -LiteralPath $runStatePath -ErrorAction SilentlyContinue
            continue
        }

        $completed[$key] = $true
        $runCount++
        Remove-Item -LiteralPath $runStatePath -ErrorAction SilentlyContinue
    }

    Write-Host "Corridas nuevas completadas en esta ejecución: $runCount."
    Write-Host "Resultados guardados en: $OutputCsv"
}
finally {
    if (Test-Path $runStatePath) {
        try {
            $interruptedRun = Get-Content -Path $runStatePath -Raw | ConvertFrom-Json
            Write-Incident "ABORTED $($interruptedRun.key): orchestration stopped during stage '$($interruptedRun.stage)'."
            Write-AbortedFromMarker $interruptedRun
            Remove-Item -LiteralPath $runStatePath
        }
        catch {
            Write-Incident "Could not finalize interrupted-run marker: $($_.Exception.Message)"
        }
    }
    Invoke-Docker -DockerArguments @("compose", "stop", "mongodb", "postgres") | Out-Null
    $env:CPUS_LIMIT = "4.0"
    $env:MEM_LIMIT = "4096M"
    foreach ($service in @("mongodb", "postgres")) {
        if ($initialRunning -contains $service) {
            Invoke-Docker -DockerArguments @("compose", "up", "-d", $service) | Out-Null
        }
    }
    Remove-Item Env:CPUS_LIMIT -ErrorAction SilentlyContinue
    Remove-Item Env:MEM_LIMIT -ErrorAction SilentlyContinue
}
