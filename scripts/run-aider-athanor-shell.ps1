param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$AiderArgs
)

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
  throw "python command not found on PATH."
}

$runtimeEnvScript = Join-Path $PSScriptRoot "runtime_env.py"
$resolvedJson = & $pythonCommand.Source $runtimeEnvScript --resolve ATHANOR_LITELLM_API_KEY ATHANOR_LITELLM_URL OPENAI_API_KEY OPENAI_API_BASE --format json
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

if (-not $env:AIDER_OPENAI_API_KEY) {
  $env:AIDER_OPENAI_API_KEY = $env:OPENAI_API_KEY
}

if (-not $env:AIDER_OPENAI_API_BASE) {
  $env:AIDER_OPENAI_API_BASE = $env:OPENAI_API_BASE
}

if (-not $env:AIDER_MODEL) {
  $env:AIDER_MODEL = "openai/gpt-codex-sub"
}

$aiderCommand = Get-Command aider -ErrorAction SilentlyContinue
$launchCommand = @()

if ($aiderCommand) {
  & $aiderCommand.Source --version *> $null
  if ($LASTEXITCODE -eq 0) {
    $launchCommand = @($aiderCommand.Source)
  }
}

if ($launchCommand.Count -eq 0) {
  $uvCommand = Get-Command uv -ErrorAction SilentlyContinue
  if (-not $uvCommand) {
    throw "aider is not healthy on PATH and uv is unavailable for fallback."
  }
  $launchCommand = @($uvCommand.Source, "tool", "run", "--from", "aider-chat", "aider")
}

$launchArgs = @()
if ($launchCommand.Count -gt 1) {
  $launchArgs += $launchCommand[1..($launchCommand.Count - 1)]
}
if ($AiderArgs) {
  $launchArgs += $AiderArgs
}

& $launchCommand[0] @launchArgs
exit $LASTEXITCODE
