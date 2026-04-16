param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$GooseArgs
)

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
  throw "python command not found on PATH."
}

$gooseCommand = Get-Command goose -ErrorAction SilentlyContinue
if (-not $gooseCommand) {
  throw "goose command not found on PATH."
}

$runtimeEnvScript = Join-Path $PSScriptRoot "runtime_env.py"
$resolvedJson = & $pythonCommand.Source $runtimeEnvScript --resolve ATHANOR_LITELLM_API_KEY ATHANOR_LITELLM_URL OPENAI_API_KEY OPENAI_API_BASE OPENAI_HOST OPENAI_BASE_PATH --format json
if ($LASTEXITCODE -ne 0) {
  throw "Managed DESK LiteLLM gateway contract is unavailable. Populate ~/.athanor/runtime.env or ATHANOR_RUNTIME_ENV_FILE."
}

$resolved = $resolvedJson | ConvertFrom-Json
foreach ($property in $resolved.PSObject.Properties) {
  $key = $property.Name
  $value = [string]$property.Value
  $currentValue = [System.Environment]::GetEnvironmentVariable($key, "Process")
  if (-not $currentValue) {
    Set-Item -Path "Env:$key" -Value $value
  }
}

if (-not $env:ATHANOR_LITELLM_API_KEY) {
  throw "ATHANOR_LITELLM_API_KEY could not be resolved from the managed runtime env surface."
}

$finalArgs = @($GooseArgs)
if ($finalArgs.Count -eq 0) {
  $finalArgs = @("session")
}

$subcommand = ""
if ($finalArgs.Count -gt 0 -and -not $finalArgs[0].StartsWith("-")) {
  $subcommand = $finalArgs[0]
}

if (@("run", "session", "s", "term") -contains $subcommand) {
  $hasProvider = $finalArgs -contains "--provider"
  $hasModel = $finalArgs -contains "--model"
  $prefix = @($finalArgs[0])
  $suffix = @()
  if ($finalArgs.Count -gt 1) {
    $suffix = $finalArgs[1..($finalArgs.Count - 1)]
  }
  if (-not $hasProvider) {
    $suffix = @("--provider", "openai") + $suffix
  }
  if (-not $hasModel) {
    $suffix = @("--model", "deepseek") + $suffix
  }
  $finalArgs = $prefix + $suffix
}

& $gooseCommand.Source @finalArgs
exit $LASTEXITCODE
