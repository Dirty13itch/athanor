param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$GooseArgs
)

$gooseCommand = Get-Command goose -ErrorAction SilentlyContinue
if (-not $gooseCommand) {
  throw "goose command not found on PATH."
}

if (-not $env:OPENAI_API_KEY) {
  if (-not $env:LITELLM_API_KEY) {
    throw "LITELLM_API_KEY is required when OPENAI_API_KEY is not already set."
  }
  $env:OPENAI_API_KEY = $env:LITELLM_API_KEY
}

if (-not $env:OPENAI_HOST) {
  $env:OPENAI_HOST = "http://192.168.1.203:4000"
}

if (-not $env:OPENAI_BASE_PATH) {
  $env:OPENAI_BASE_PATH = "v1/chat/completions"
}

$finalArgs = @()
if ($GooseArgs) {
  $finalArgs += $GooseArgs
}

$hasProvider = $finalArgs -contains "--provider"
$hasModel = $finalArgs -contains "--model"

if ($finalArgs.Count -gt 0 -and $finalArgs[0] -eq "run") {
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
else {
  if (-not $hasProvider) {
    $finalArgs = @("--provider", "openai") + $finalArgs
  }
  if (-not $hasModel) {
    $finalArgs = @("--model", "deepseek") + $finalArgs
  }
}

& $gooseCommand.Source @finalArgs
exit $LASTEXITCODE
