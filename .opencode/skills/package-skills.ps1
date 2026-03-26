#!/usr/bin/env pwsh
# Skills Package Script - 技能打包与迁移工具
# 用法：.\package-skills.ps1 [-Action pack|unpack|verify] [-OutputPath <path>]

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet('pack', 'unpack', 'verify')]
    [string]$Action = 'pack',
    
    [Parameter(Mandatory=$false)]
    [string]$OutputPath = 'skills-package.zip',
    
    [Parameter(Mandatory=$false)]
    [string]$SourcePath = '.',
    
    [Parameter(Mandatory=$false)]
    [string]$DestPath = 'skills'
)

$ErrorActionPreference = 'Stop'

function Write-Header {
    param([string]$Text)
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host " $Text" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Success {
    param([string]$Text)
    Write-Host "✅ $Text" -ForegroundColor Green
}

function Write-Error-Custom {
    param([string]$Text)
    Write-Host "❌ $Text" -ForegroundColor Red
}

function Write-Warning-Custom {
    param([string]$Text)
    Write-Host "⚠️  $Text" -ForegroundColor Yellow
}

function Package-Skills {
    Write-Header "打包技能文件"
    
    $ExcludePatterns = @(
        '*.env',
        '*.pyc',
        '__pycache__',
        'node_modules',
        '*.log',
        '.git',
        '.DS_Store',
        'Thumbs.db',
        '*.zip'
    )
    
    Write-Host "排除文件类型:" -ForegroundColor Yellow
    $ExcludePatterns | ForEach-Object { Write-Host "  - $_" }
    Write-Host ""
    
    # 获取所有文件，排除指定模式
    $AllFiles = Get-ChildItem -Path $SourcePath -Recurse -File | 
        Where-Object { 
            $exclude = $false
            foreach ($pattern in $ExcludePatterns) {
                if ($_.Name -like $pattern.Replace('*', '*') -or $_.FullName -like "*\$pattern\*") {
                    $exclude = $true
                    break
                }
            }
            -not $exclude
        }
    
    Write-Host "找到 $($AllFiles.Count) 个文件待打包" -ForegroundColor Yellow
    
    # 创建压缩包
    if (Test-Path $OutputPath) {
        Write-Warning-Custom "目标文件已存在，将被覆盖：$OutputPath"
        Remove-Item $OutputPath -Force
    }
    
    # 使用 Compress-Archive
    $TempDir = Join-Path $env:TEMP "skills-package-temp"
    if (Test-Path $TempDir) {
        Remove-Item $TempDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $TempDir | Out-Null
    
    # 复制文件到临时目录
    Write-Host "复制文件到临时目录..." -ForegroundColor Yellow
    foreach ($file in $AllFiles) {
        $RelativePath = $file.FullName.Replace((Resolve-Path $SourcePath).Path, '').TrimStart('\')
        $DestFile = Join-Path $TempDir $RelativePath
        $DestDir = Split-Path $DestFile -Parent
        if (-not (Test-Path $DestDir)) {
            New-Item -ItemType Directory -Path $DestDir -Force | Out-Null
        }
        Copy-Item $file.FullName -Destination $DestFile -Force
    }
    
    # 创建压缩包
    Write-Host "创建压缩包..." -ForegroundColor Yellow
    Compress-Archive -Path "$TempDir\*" -DestinationPath $OutputPath -Force
    
    # 清理临时目录
    Remove-Item $TempDir -Recurse -Force
    
    $Size = (Get-Item $OutputPath).Length / 1MB
    Write-Success "打包完成：$OutputPath ($(Math.Round($Size, 2)) MB)"
    
    Write-Host ""
    Write-Host "下一步:" -ForegroundColor Cyan
    Write-Host "  1. 将 $OutputPath 传输到目标机器"
    Write-Host "  2. 在目标机器运行：.\package-skills.ps1 -Action unpack"
    Write-Host ""
}

function Unpack-Skills {
    param(
        [string]$PackagePath = 'skills-package.zip',
        [string]$DestPath = 'skills'
    )
    
    Write-Header "解压技能包"
    
    if (-not (Test-Path $PackagePath)) {
        Write-Error-Custom "找不到技能包：$PackagePath"
        exit 1
    }
    
    if (Test-Path $DestPath) {
        Write-Warning-Custom "目标目录已存在：$DestPath"
        $response = Read-Host "是否覆盖？(y/N)"
        if ($response -ne 'y' -and $response -ne 'Y') {
            Write-Host "取消解压" -ForegroundColor Yellow
            exit 0
        }
        Remove-Item $DestPath -Recurse -Force
    }
    
    Write-Host "解压到：$DestPath" -ForegroundColor Yellow
    Expand-Archive -Path $PackagePath -DestinationPath $DestPath -Force
    
    Write-Success "解压完成"
    
    Write-Host ""
    Write-Host "下一步:" -ForegroundColor Cyan
    Write-Host "  1. 配置环境变量 (.env 文件)"
    Write-Host "  2. 安装依赖 (npm install / uv 自动管理)"
    Write-Host "  3. 验证安装"
    Write-Host ""
    Write-Host "运行以下命令继续:" -ForegroundColor Yellow
    Write-Host "  .\package-skills.ps1 -Action verify -SourcePath $DestPath"
    Write-Host ""
}

function Verify-Skills {
    Write-Header "验证技能安装"
    
    $Checks = @{
        'Python' = { python --version 2>&1 }
        'Node.js' = { node --version 2>&1 }
        'uv' = { uv --version 2>&1 }
        'npm' = { npm --version 2>&1 }
    }
    
    $Results = @{}
    
    foreach ($check in $Checks.GetEnumerator()) {
        try {
            $output = & $check.Value 2>&1 | Out-String
            if ($LASTEXITCODE -eq 0) {
                $Results[$check.Key] = @{ Status = 'OK'; Version = $output.Trim() }
                Write-Success "$($check.Key): $($output.Trim())"
            } else {
                $Results[$check.Key] = @{ Status = 'MISSING'; Version = $null }
                Write-Warning-Custom "$($check.Key): 未安装"
            }
        } catch {
            $Results[$check.Key] = @{ Status = 'ERROR'; Version = $null }
            Write-Error-Custom "$($check.Key): $($_.Exception.Message)"
        }
    }
    
    Write-Host ""
    Write-Host "检查技能目录结构..." -ForegroundColor Cyan
    
    $RequiredSkills = @(
        'search-history-cases-skill',
        'assessment-reasoning-skill',
        'learning-flywheel-skill',
        's4-dialog-intent-detector',
        'parse-requirement-skill',
        'generate-report-skill',
        's7-review-persistence-skill'
    )
    
    $MissingSkills = @()
    foreach ($skill in $RequiredSkills) {
        $SkillPath = Join-Path $SourcePath $skill
        if (Test-Path $SkillPath) {
            Write-Success "$skill: 存在"
        } else {
            Write-Warning-Custom "$skill: 缺失"
            $MissingSkills += $skill
        }
    }
    
    Write-Host ""
    Write-Host "检查 .env.example 文件..." -ForegroundColor Cyan
    
    $MissingEnvExamples = @()
    foreach ($skill in $RequiredSkills) {
        $EnvExamplePath = Join-Path $SourcePath "$skill\.env.example"
        if (Test-Path $EnvExamplePath) {
            Write-Success "$skill\.env.example: 存在"
        } else {
            # 某些技能可能没有 .env.example（如 S5）
            Write-Warning-Custom "$skill\.env.example: 不存在（可能无需配置）"
        }
    }
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host " 验证摘要" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    
    if ($MissingSkills.Count -eq 0) {
        Write-Success "所有技能文件完整"
    } else {
        Write-Warning-Custom "缺失技能：$($MissingSkills -join ', ')"
    }
    
    $MissingTools = ($Results.GetEnumerator() | Where-Object { $_.Value.Status -eq 'MISSING' }).Key
    if ($MissingTools) {
        Write-Warning-Custom "缺失工具：$($MissingTools -join ', ')"
        Write-Host ""
        Write-Host "安装建议:" -ForegroundColor Yellow
        if ($MissingTools -contains 'Python') {
            Write-Host "  Python: https://www.python.org/downloads/"
        }
        if ($MissingTools -contains 'Node.js') {
            Write-Host "  Node.js: https://nodejs.org/"
        }
        if ($MissingTools -contains 'uv') {
            Write-Host "  uv: 运行以下命令安装"
            Write-Host "    powershell -ExecutionPolicy ByPass -c ""irm https://astral.sh/uv/install.ps1 | iex"""
        }
    } else {
        Write-Success "所有必需工具已安装"
    }
    
    Write-Host ""
    Write-Host "配置检查:" -ForegroundColor Cyan
    Write-Host "  1. 为每个技能创建 .env 文件（从 .env.example 复制）"
    Write-Host "  2. 配置数据库连接（PostgreSQL）"
    Write-Host "  3. 配置 Redis 连接（S4/S7）"
    Write-Host "  4. 运行依赖安装命令"
    Write-Host ""
    Write-Host "详细配置指南请参考：MIGRATION_GUIDE.md" -ForegroundColor Yellow
    Write-Host ""
}

# 主程序
switch ($Action) {
    'pack' {
        Package-Skills
    }
    'unpack' {
        Unpack-Skills -PackagePath $OutputPath -DestPath $DestPath
    }
    'verify' {
        Verify-Skills
    }
}
