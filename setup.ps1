# Athanor - Legacy Claude Code Bootstrap / Recovery Script
# Recovery/bootstrap helper for older Windows Claude Code setup flows; do not treat this script as current operator truth.
# Current setup truth lives in AGENTS.md, STATUS.md, and docs/operations/SESSION-RESTART-RUNBOOK.md.

Write-Host "=== Athanor - Claude Code Environment Setup ===" -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

$nodeVersion = & node --version 2>$null
if (-not $nodeVersion) {
    Write-Host "ERROR: Node.js is not installed. Install from https://nodejs.org/" -ForegroundColor Red
    exit 1
}
Write-Host "  Node.js: $nodeVersion" -ForegroundColor Green

$claudeVersion = & claude --version 2>$null
if (-not $claudeVersion) {
    Write-Host "ERROR: Claude Code is not installed. Install with: npm install -g @anthropic-ai/claude-code" -ForegroundColor Red
    exit 1
}
Write-Host "  Claude Code: $claudeVersion" -ForegroundColor Green

Write-Host ""
Write-Host "=== Installing User-Scoped MCP Servers ===" -ForegroundColor Cyan
Write-Host "These are user-scoped installs and may affect other Claude Code projects on this machine." -ForegroundColor Gray
Write-Host ""

# GitHub MCP
Write-Host "Installing GitHub MCP..." -ForegroundColor Yellow
$ghToken = Read-Host "Enter your GitHub Personal Access Token (or press Enter to skip)"
if ($ghToken) {
    & claude mcp add github -s user -e GITHUB_PERSONAL_ACCESS_TOKEN=$ghToken -- npx -y @modelcontextprotocol/server-github
    Write-Host "  GitHub MCP installed." -ForegroundColor Green
} else {
    Write-Host "  Skipped GitHub MCP (no token provided)." -ForegroundColor Gray
    Write-Host "  To add later: claude mcp add github -s user -e GITHUB_PERSONAL_ACCESS_TOKEN=<token> -- npx -y @modelcontextprotocol/server-github" -ForegroundColor Gray
}

Write-Host ""

# Brave Search MCP
Write-Host "Installing Brave Search MCP..." -ForegroundColor Yellow
$braveKey = Read-Host "Enter your Brave Search API Key (free at https://brave.com/search/api/ - or press Enter to skip)"
if ($braveKey) {
    & claude mcp add brave-search -s user -e BRAVE_API_KEY=$braveKey -- npx -y @modelcontextprotocol/server-brave-search
    Write-Host "  Brave Search MCP installed." -ForegroundColor Green
} else {
    Write-Host "  Skipped Brave Search MCP (no key provided)." -ForegroundColor Gray
    Write-Host "  To add later: claude mcp add brave-search -s user -e BRAVE_API_KEY=<key> -- npx -y @modelcontextprotocol/server-brave-search" -ForegroundColor Gray
}

Write-Host ""

# Desktop Commander MCP
Write-Host "Installing Desktop Commander MCP..." -ForegroundColor Yellow
& claude mcp add desktop-commander -s user -- npx -y @wonderwhy-er/desktop-commander
Write-Host "  Desktop Commander MCP installed." -ForegroundColor Green

Write-Host ""

# Memory MCP
Write-Host "Installing Memory MCP..." -ForegroundColor Yellow
& claude mcp add memory -s user -- npx -y @modelcontextprotocol/server-memory
Write-Host "  Memory MCP installed." -ForegroundColor Green

Write-Host ""

# Enable Agent Teams
Write-Host "=== Enabling Experimental Features ===" -ForegroundColor Cyan
Write-Host "Enabling Agent Teams (multi-agent orchestration)..." -ForegroundColor Yellow
[Environment]::SetEnvironmentVariable("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS", "1", "User")
Write-Host "  Agent Teams enabled (takes effect on next Claude Code launch)." -ForegroundColor Green

Write-Host ""

# Git bash path for Claude Code (Windows)
$gitBashPath = "C:\Program Files\Git\bin\bash.exe"
if (Test-Path $gitBashPath) {
    [Environment]::SetEnvironmentVariable("CLAUDE_CODE_GIT_BASH_PATH", $gitBashPath, "User")
    Write-Host "  Git bash path set for Claude Code." -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "User-scoped MCP servers installed:" -ForegroundColor Green
Write-Host "  - github (if token provided)" -ForegroundColor White
Write-Host "  - brave-search (if key provided)" -ForegroundColor White
Write-Host "  - desktop-commander" -ForegroundColor White
Write-Host "  - memory" -ForegroundColor White
Write-Host ""
Write-Host "Project-scoped MCP servers (from .mcp.json):" -ForegroundColor Green
Write-Host "  - sequential-thinking" -ForegroundColor White
Write-Host "  - context7" -ForegroundColor White
Write-Host "  - playwright" -ForegroundColor White
Write-Host "  - filesystem" -ForegroundColor White
Write-Host ""
Write-Host "Environment variables set:" -ForegroundColor Green
Write-Host "  - CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1" -ForegroundColor White
Write-Host "  - CLAUDE_CODE_GIT_BASH_PATH (if Git found)" -ForegroundColor White
Write-Host ""
Write-Host "Legacy bootstrap next steps (verify current docs before following):" -ForegroundColor Yellow
Write-Host "  1. Close and reopen your terminal (for env vars to take effect)" -ForegroundColor White
Write-Host "  2. Open the current repo and verify AGENTS.md / STATUS.md / SESSION-RESTART-RUNBOOK.md" -ForegroundColor White
Write-Host "  3. Run: claude (only if you are intentionally bootstrapping the older Claude Code flow)" -ForegroundColor White
Write-Host "  4. Use current repo startup/orientation guidance instead of legacy git-init instructions" -ForegroundColor White
Write-Host ""
Write-Host "The furnace is ready to light." -ForegroundColor Cyan
