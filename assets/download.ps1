# download z-code files from a source.
#https://www.ifarchive.org/if-archive/games/zcode/zork_285.z5


param(
    [string]$Name # optional: download only one game
)

$src = Join-Path $PSScriptRoot 'sources.json'
if (-not (Test-Path $src)) {
    Write-Error "sources.json not found at $src"; exit 1
}

try {
    $data = Get-Content $src -Raw | ConvertFrom-Json
} catch {
    Write-Error "Failed to parse JSON: $_"; exit 1
}

$games = $data.games
if (-not $games) { Write-Error 'No "games" key in sources.json'; exit 1 }

function Download-Game($title, $url) {
    $safe = ($title -replace '[^A-Za-z0-9_-]', '_')
    $outFile = Join-Path $PSScriptRoot ("$safe.z5")
    Write-Host "Downloading $title → $outFile" -ForegroundColor Cyan
    Invoke-WebRequest -Uri $url -OutFile $outFile -UseBasicParsing
}

if ($Name) {
    if ($games.$Name) {
        Download-Game $Name $games.$Name
    } else {
        Write-Error "Game '$Name' not found in sources.json"; exit 1
    }
} else {
    foreach ($prop in $games.PSObject.Properties) {
        Download-Game $prop.Name $prop.Value
    }
}