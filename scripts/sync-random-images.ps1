param(
    [string]$SourceDir = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot

if (-not $SourceDir) {
    $envFile = Join-Path $projectRoot ".env"
    if (Test-Path -LiteralPath $envFile) {
        $setting = Get-Content -LiteralPath $envFile |
            Where-Object { $_ -match '^RANDOM_IMAGE_HOST_DIR=' } |
            Select-Object -Last 1
        if ($setting) {
            $SourceDir = ($setting -split '=', 2)[1].Trim().Replace('/', '\')
        }
    }
}

if (-not $SourceDir) {
    throw "请通过 -SourceDir 指定图片目录，或在 .env 设置 RANDOM_IMAGE_HOST_DIR。"
}

$resolvedSource = (Resolve-Path -LiteralPath $SourceDir).Path
if (-not (Test-Path -LiteralPath $resolvedSource -PathType Container)) {
    throw "图片目录不存在：$resolvedSource"
}

$supported = @('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')
$imageCount = (Get-ChildItem -LiteralPath $resolvedSource -File -Recurse |
    Where-Object { $supported -contains $_.Extension.ToLowerInvariant() } |
    Measure-Object).Count
if ($imageCount -eq 0) {
    throw "目录中没有支持的图片。"
}

Push-Location $projectRoot
try {
    docker compose --env-file .env up -d --no-deps astrbot napcat
    if ($LASTEXITCODE -ne 0) {
        throw "无法启动 AstrBot/NapCat。"
    }

    $helperName = "qq-ai-random-image-import-$([Guid]::NewGuid().ToString('N'))"
    docker create --name $helperName --mount "source=qq-ai-bot_random_image_data,target=/images" alpine:latest sh -c "sleep 3600" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "无法创建图库导入容器。"
    }

    try {
        docker start $helperName | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "无法启动图库导入容器。"
        }
        docker cp "$resolvedSource\." "${helperName}:/images/"
        if ($LASTEXITCODE -ne 0) {
            throw "复制图库失败。"
        }
    }
    finally {
        docker rm -f $helperName | Out-Null
    }

    Write-Host "图库同步完成：$imageCount 张支持格式的图片。"
}
finally {
    Pop-Location
}
