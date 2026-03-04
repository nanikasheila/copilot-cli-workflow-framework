<#
.SYNOPSIS
    Board JSON のバリデーションスクリプト

.DESCRIPTION
    Board JSON ファイルの必須フィールド、有効値、構造を検証する。
    PowerShell Core (pwsh) を使用することで Windows / Linux 両環境で動作する。

.PARAMETER BoardPath
    検証対象の Board JSON ファイルパス

.OUTPUTS
    バリデーション結果を標準出力に出力する。
    終了コード: 0 = PASS, 1 = FAIL

.EXAMPLE
    .\validate-board.ps1 -BoardPath ".copilot/boards/feature-auth/board.json"

.EXAMPLE
    # Linux (pwsh)
    pwsh -File validate-board.ps1 -BoardPath ".copilot/boards/feature-auth/board.json"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, HelpMessage = "Board JSON ファイルパス")]
    [string]$BoardPath
)

$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# 定数定義
# ---------------------------------------------------------------------------
$VALID_MATURITY = @(
    'experimental', 'development', 'stable', 'release-ready', 'sandbox', 'abandoned'
)

# board.schema.json の flow_state enum に基づく有効値
$VALID_FLOW_STATE = @(
    'initialized', 'analyzing', 'designing', 'planned',
    'implementing', 'testing', 'reviewing', 'approved',
    'documenting', 'submitting', 'completed'
)

# board.schema.json の gate_status enum に基づく有効値
$VALID_GATE_STATUS = @(
    'not_reached', 'pending', 'passed', 'failed', 'skipped', 'blocked'
)

# Board スキーマで定義された全 Gate 名
$REQUIRED_GATES = @(
    'analysis', 'design', 'plan', 'implementation',
    'test', 'review', 'documentation', 'submit'
)

# Board スキーマで定義された全 Artifact キー
$REQUIRED_ARTIFACT_KEYS = @(
    'requirements', 'impact_analysis', 'architecture_decision', 'execution_plan',
    'implementation', 'test_design', 'test_results', 'test_verification',
    'review_findings', 'documentation'
)

# ---------------------------------------------------------------------------
# ヘルパー関数
# ---------------------------------------------------------------------------
function Write-ValidationResult {
    param(
        [string[]]$Errors,
        [string[]]$Warnings
    )

    if ($Errors.Count -eq 0) {
        [Console]::WriteLine("PASS: Board validation passed")
        foreach ($w in $Warnings) {
            [Console]::WriteLine("  WARN: $w")
        }
        return $true
    }
    else {
        [Console]::WriteLine("FAIL: Board validation failed ($($Errors.Count) error(s))")
        foreach ($e in $Errors) {
            [Console]::WriteLine("  ERROR: $e")
        }
        foreach ($w in $Warnings) {
            [Console]::WriteLine("  WARN: $w")
        }
        return $false
    }
}

# ---------------------------------------------------------------------------
# メイン処理
# ---------------------------------------------------------------------------
$validationErrors   = [System.Collections.Generic.List[string]]::new()
$validationWarnings = [System.Collections.Generic.List[string]]::new()

# 1. ファイル存在チェック
if (-not (Test-Path -LiteralPath $BoardPath)) {
    [Console]::WriteLine("FAIL: Board file not found: $BoardPath")
    exit 1
}

# 2. JSON パース
$board = $null
try {
    $rawJson = Get-Content -LiteralPath $BoardPath -Raw -Encoding UTF8
    $board   = $rawJson | ConvertFrom-Json
}
catch {
    [Console]::WriteLine("FAIL: JSON parse error: $_")
    exit 1
}

# ---------------------------------------------------------------------------
# プロパティ安全アクセスのヘルパー
# ---------------------------------------------------------------------------
function Get-SafeProperty {
    param([object]$Object, [string]$Name)
    if ($null -eq $Object) { return $null }
    $prop = $Object.PSObject.Properties | Where-Object { $_.Name -eq $Name }
    if ($null -eq $prop) { return $null }
    return $prop.Value
}

# 3. 必須フィールドの存在チェック
$requiredTopFields = @('feature_id', 'maturity', 'flow_state', 'gates', 'artifacts', 'history')
foreach ($field in $requiredTopFields) {
    # PSObject.Properties で null との区別なくキー存在を確認
    $hasKey = $board.PSObject.Properties.Name -contains $field
    if (-not $hasKey) {
        $validationErrors.Add("Missing required field: '$field'")
    }
    elseif ($null -eq $board.$field -and $field -in @('feature_id', 'maturity', 'flow_state', 'gates', 'history')) {
        $validationErrors.Add("Required field '$field' must not be null")
    }
}

# 4. maturity 有効値チェック
if ($null -ne $board.maturity) {
    if ($VALID_MATURITY -notcontains $board.maturity) {
        $validationErrors.Add(
            "Invalid maturity: '$($board.maturity)'. Valid values: $($VALID_MATURITY -join ', ')"
        )
    }
}

# 5. flow_state 有効値チェック
if ($null -ne $board.flow_state) {
    if ($VALID_FLOW_STATE -notcontains $board.flow_state) {
        $validationErrors.Add(
            "Invalid flow_state: '$($board.flow_state)'. Valid values: $($VALID_FLOW_STATE -join ', ')"
        )
    }
}

# 6. gates 各ステータスチェック
if ($null -ne $board.gates) {
    foreach ($gateName in $REQUIRED_GATES) {
        $gateObj = $board.gates.PSObject.Properties |
                   Where-Object { $_.Name -eq $gateName } |
                   Select-Object -ExpandProperty Value -ErrorAction SilentlyContinue

        if ($null -eq $gateObj) {
            $validationWarnings.Add("Gate '$gateName' is missing from 'gates' object")
        }
        else {
            $statusProp = $gateObj.PSObject.Properties |
                          Where-Object { $_.Name -eq 'status' } |
                          Select-Object -ExpandProperty Value -ErrorAction SilentlyContinue

            if ($null -eq $statusProp) {
                $validationErrors.Add("Gate '$gateName' is missing required field 'status'")
            }
            elseif ($VALID_GATE_STATUS -notcontains $statusProp) {
                $validationErrors.Add(
                    "Gate '$gateName' has invalid status: '$statusProp'. Valid values: $($VALID_GATE_STATUS -join ', ')"
                )
            }
        }
    }
}

# 7. artifacts キー存在チェック（値は null でも可）
if ($null -ne $board.artifacts) {
    foreach ($artifactKey in $REQUIRED_ARTIFACT_KEYS) {
        $hasKey = $board.artifacts.PSObject.Properties.Name -contains $artifactKey
        if (-not $hasKey) {
            $validationWarnings.Add("Artifact key '$artifactKey' is missing from 'artifacts' object")
        }
    }
}

# 8. history が配列かチェック
if ($null -ne $board.history) {
    # ConvertFrom-Json では配列は Object[] または PSCustomObject[] になる
    if ($board.history -isnot [System.Array] -and $board.history -isnot [System.Collections.IEnumerable]) {
        $validationErrors.Add("Field 'history' must be an array")
    }
}

# 9. gate_profile と maturity の一致チェック
if ($null -ne $board.maturity -and $null -ne $board.gate_profile) {
    if ($board.maturity -ne $board.gate_profile) {
        $validationWarnings.Add(
            "maturity ('$($board.maturity)') and gate_profile ('$($board.gate_profile)') are different. " +
            "Manual override may be intended, but verify this is correct."
        )
    }
}

# 10. updated_at フィールドの存在チェック（任意だが推奨）
if (-not ($board.PSObject.Properties.Name -contains 'updated_at')) {
    $validationWarnings.Add("Field 'updated_at' is missing (recommended)")
}

# ---------------------------------------------------------------------------
# 結果出力
# ---------------------------------------------------------------------------
$passed = Write-ValidationResult -Errors $validationErrors -Warnings $validationWarnings

if ($passed) { exit 0 } else { exit 1 }
