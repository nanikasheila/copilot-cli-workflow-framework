<#
.SYNOPSIS
    Gate 条件の機械的評価スクリプト

.DESCRIPTION
    gate-profiles.json の条件定義と Board の artifacts を比較し、
    指定した Gate が通過可能かを評価する。
    PowerShell Core (pwsh) を使用することで Windows / Linux 両環境で動作する。

.PARAMETER BoardPath
    評価対象の Board JSON ファイルパス

.PARAMETER ProfilePath
    gate-profiles.json ファイルパス

.PARAMETER GateName
    評価対象の Gate 名 (analysis / design / plan / implementation / test / review / documentation / submit)

.OUTPUTS
    評価結果を JSON 形式で標準出力に出力する。
    終了コード: 0 = PASS, 1 = FAIL, 2 = SKIP (required: false), 3 = BLOCKED (required: "blocked")

.EXAMPLE
    .\evaluate-gate.ps1 `
        -BoardPath ".copilot/boards/feature-auth/board.json" `
        -ProfilePath ".github/rules/gate-profiles.json" `
        -GateName "test"

.EXAMPLE
    # Linux (pwsh)
    pwsh -File evaluate-gate.ps1 \
        -BoardPath ".copilot/boards/feature-auth/board.json" \
        -ProfilePath ".github/rules/gate-profiles.json" \
        -GateName "test"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, HelpMessage = "Board JSON ファイルパス")]
    [string]$BoardPath,

    [Parameter(Mandatory = $true, HelpMessage = "gate-profiles.json ファイルパス")]
    [string]$ProfilePath,

    [Parameter(Mandatory = $true, HelpMessage = "評価対象 Gate 名 (e.g. test, review)")]
    [ValidateSet('analysis', 'design', 'plan', 'implementation', 'test', 'review', 'documentation', 'submit')]
    [string]$GateName,

    [Parameter(Mandatory = $false, HelpMessage = "settings.json ファイルパス（automated_checks で使用）")]
    [string]$SettingsPath = ""
)

$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# 定数定義
# ---------------------------------------------------------------------------

# Board の Gate 名 → gate-profiles.json キー名のマッピング
$GATE_PROFILE_KEY_MAP = @{
    'analysis'       = 'analysis_gate'
    'design'         = 'design_gate'
    'plan'           = 'plan_gate'
    'implementation' = 'implementation_gate'
    'test'           = 'test_gate'
    'review'         = 'review_gate'
    'documentation'  = 'documentation_gate'
    'submit'         = 'submit_gate'
}

# Gate → 対応する Artifact キーのマッピング（存在チェック用）
$GATE_ARTIFACT_MAP = @{
    'analysis'       = 'impact_analysis'
    'design'         = 'architecture_decision'
    'plan'           = 'execution_plan'
    'implementation' = 'implementation'
    'test'           = 'test_results'
    'review'         = 'review_findings'
    'documentation'  = 'documentation'
    'submit'         = $null   # submit は PR 操作のため artifact チェックなし
}

# ---------------------------------------------------------------------------
# ヘルパー関数
# ---------------------------------------------------------------------------

function ConvertTo-JsonCompact {
    param($Object)
    $json = $Object | ConvertTo-Json -Compress -Depth 10
    [Console]::WriteLine($json)
}

function New-ResultObject {
    param(
        [string]$Gate,
        [string]$Result,      # PASS / FAIL / SKIP / BLOCKED / ON_ESCALATION
        [bool]$Required,
        [string]$Message,
        [array]$Conditions = @()
    )

    return [ordered]@{
        gate       = $Gate
        result     = $Result
        required   = $Required
        message    = $Message
        conditions = $Conditions
        evaluated_at = (Get-Date -Format 'o')
    }
}

function Get-PropertyValue {
    <#
        .SYNOPSIS
        PSCustomObject から dotted path でネストしたプロパティ値を取得する。
        例: Get-PropertyValue $obj "test_results.pass_rate"
    #>
    param(
        [object]$Object,
        [string]$Path
    )

    $parts  = $Path -split '\.'
    $current = $Object
    foreach ($part in $parts) {
        if ($null -eq $current) { return $null }
        $prop = $current.PSObject.Properties | Where-Object { $_.Name -eq $part }
        if ($null -eq $prop) { return $null }
        $current = $prop.Value
    }
    return $current
}

function Test-Evidence {
    <#
        .SYNOPSIS
        gate-profiles.json の evidence_required に基づき、Board の artifacts からエビデンスを検証する。
    #>
    param(
        [Parameter(Mandatory)] [string[]]$RequiredEvidence,
        [Parameter(Mandatory)] [object]$Artifacts,
        [Parameter(Mandatory)] [string]$GateName
    )

    $results  = [System.Collections.Generic.List[object]]::new()
    $failures = [System.Collections.Generic.List[string]]::new()

    foreach ($evidenceType in $RequiredEvidence) {
        switch ($evidenceType) {
            'commit_sha' {
                # artifacts 内のいずれかのフィールドに 40文字 hex の commit SHA が存在するか
                $found = $false
                if ($null -ne $Artifacts) {
                    foreach ($prop in $Artifacts.PSObject.Properties) {
                        $sha = Get-PropertyValue -Object $prop.Value -Path 'commit_sha'
                        if ($null -ne $sha -and "$sha" -match '^[0-9a-fA-F]{40}$') {
                            $found = $true
                            break
                        }
                    }
                }
                $results.Add([ordered]@{
                    evidence = $evidenceType
                    met      = $found
                    detail   = if ($found) { 'Valid 40-char commit SHA found in artifacts' } else { 'No valid 40-char hex SHA found in artifacts' }
                })
                if (-not $found) { $failures.Add("evidence '$evidenceType': no valid commit SHA (40-char hex) found in artifacts") }
            }

            'test_output' {
                $testResults = if ($null -ne $Artifacts) {
                    $Artifacts.PSObject.Properties | Where-Object { $_.Name -eq 'test_results' } |
                        Select-Object -ExpandProperty Value -ErrorAction SilentlyContinue
                } else { $null }
                $met = ($null -ne $testResults)
                $results.Add([ordered]@{
                    evidence = $evidenceType
                    met      = $met
                    detail   = if ($met) { 'artifacts.test_results exists' } else { 'artifacts.test_results is missing' }
                })
                if (-not $met) { $failures.Add("evidence '$evidenceType': artifacts.test_results is missing") }
            }

            'build_success' {
                $buildResult = if ($null -ne $Artifacts) {
                    $Artifacts.PSObject.Properties | Where-Object { $_.Name -eq 'build_result' } |
                        Select-Object -ExpandProperty Value -ErrorAction SilentlyContinue
                } else { $null }
                $success = if ($null -ne $buildResult) { Get-PropertyValue -Object $buildResult -Path 'success' } else { $null }
                $met = ($success -eq $true)
                $results.Add([ordered]@{
                    evidence = $evidenceType
                    met      = $met
                    detail   = if ($met) { 'artifacts.build_result.success is true' } else { "artifacts.build_result.success is not true (actual: $success)" }
                })
                if (-not $met) { $failures.Add("evidence '$evidenceType': artifacts.build_result.success != true (actual: $success)") }
            }

            'lint_pass' {
                $lintResult = if ($null -ne $Artifacts) {
                    $Artifacts.PSObject.Properties | Where-Object { $_.Name -eq 'lint_result' } |
                        Select-Object -ExpandProperty Value -ErrorAction SilentlyContinue
                } else { $null }
                $passed = if ($null -ne $lintResult) { Get-PropertyValue -Object $lintResult -Path 'passed' } else { $null }
                $met = ($passed -eq $true)
                $results.Add([ordered]@{
                    evidence = $evidenceType
                    met      = $met
                    detail   = if ($met) { 'artifacts.lint_result.passed is true' } else { "artifacts.lint_result.passed is not true (actual: $passed)" }
                })
                if (-not $met) { $failures.Add("evidence '$evidenceType': artifacts.lint_result.passed != true (actual: $passed)") }
            }

            'review_verdict' {
                $rfProp = if ($null -ne $Artifacts) {
                    $Artifacts.PSObject.Properties | Where-Object { $_.Name -eq 'review_findings' }
                } else { $null }
                $reviewFindings = if ($null -ne $rfProp) { @($rfProp.Value) } else { $null }
                $lastVerdict = $null
                if ($null -ne $reviewFindings -and $reviewFindings.Count -gt 0) {
                    $lastEntry   = $reviewFindings[$reviewFindings.Count - 1]
                    $lastVerdict = Get-PropertyValue -Object $lastEntry -Path 'verdict'
                }
                $met = ($null -ne $lastVerdict)
                $results.Add([ordered]@{
                    evidence = $evidenceType
                    met      = $met
                    detail   = if ($met) { "review verdict exists: $lastVerdict" } else { 'no verdict found in artifacts.review_findings' }
                })
                if (-not $met) { $failures.Add("evidence '$evidenceType': no verdict found in artifacts.review_findings") }
            }

            'coverage_report' {
                $testResults = if ($null -ne $Artifacts) {
                    $Artifacts.PSObject.Properties | Where-Object { $_.Name -eq 'test_results' } |
                        Select-Object -ExpandProperty Value -ErrorAction SilentlyContinue
                } else { $null }
                $coverage = if ($null -ne $testResults) {
                    $v = Get-PropertyValue -Object $testResults -Path 'coverage'
                    if ($null -eq $v) { $v = Get-PropertyValue -Object $testResults -Path 'coverage_percent' }
                    $v
                } else { $null }
                $met = ($null -ne $coverage)
                $results.Add([ordered]@{
                    evidence = $evidenceType
                    met      = $met
                    detail   = if ($met) { "coverage value exists: $coverage" } else { 'no coverage value found in artifacts.test_results' }
                })
                if (-not $met) { $failures.Add("evidence '$evidenceType': no coverage value found in artifacts.test_results.coverage") }
            }

            default {
                $results.Add([ordered]@{
                    evidence = $evidenceType
                    met      = $false
                    detail   = "Unknown evidence type: $evidenceType"
                })
                $failures.Add("evidence '$evidenceType': unknown evidence type")
            }
        }
    }

    return [ordered]@{
        results  = $results.ToArray()
        failures = $failures.ToArray()
        passed   = ($failures.Count -eq 0)
    }
}

function Invoke-AutomatedCheck {
    <#
        .SYNOPSIS
        gate-profiles.json の automated_checks エントリを実行し、成否を返す。
        settings.json の project セクションからコマンドを解決する。
    #>
    param(
        [Parameter(Mandatory)] [PSObject]$Check,
        [Parameter(Mandatory = $false)] [PSObject]$ProjectSettings
    )

    $checkName = $Check.name
    $checkType = $Check.type
    $isRequired = if ($null -ne $Check.PSObject.Properties['required'] -and $null -ne $Check.required) {
        [bool]$Check.required
    } else { $true }

    # コマンド解決: check.command が明示されていればそれを優先、なければ settings.json から解決
    $command = $Check.PSObject.Properties['command'] | Select-Object -ExpandProperty Value -ErrorAction SilentlyContinue
    if ([string]::IsNullOrEmpty($command) -and $null -ne $ProjectSettings) {
        switch ($checkType) {
            'build' { $command = $ProjectSettings.PSObject.Properties['build'] | Select-Object -ExpandProperty Value -ErrorAction SilentlyContinue }
            'test'  {
                $testSection = $ProjectSettings.PSObject.Properties['test'] | Select-Object -ExpandProperty Value -ErrorAction SilentlyContinue
                if ($null -ne $testSection) {
                    $command = Get-PropertyValue -Object $testSection -Path 'command'
                }
            }
            'lint'  { $command = $ProjectSettings.PSObject.Properties['lint'] | Select-Object -ExpandProperty Value -ErrorAction SilentlyContinue }
        }
    }

    if ([string]::IsNullOrEmpty($command)) {
        return [ordered]@{
            name     = $checkName
            type     = $checkType
            required = $isRequired
            skipped  = $true
            passed   = (-not $isRequired)   # optional check はスキップでも PASS 扱い
            message  = "No command resolved for check '$checkName' (type: $checkType). Skipped."
        }
    }

    try {
        $output   = Invoke-Expression $command 2>&1
        $exitCode = $LASTEXITCODE
        $passed   = ($exitCode -eq 0)
        return [ordered]@{
            name      = $checkName
            type      = $checkType
            required  = $isRequired
            skipped   = $false
            passed    = $passed
            exit_code = $exitCode
            message   = if ($passed) { "Check '$checkName' passed (exit 0)" } else { "Check '$checkName' failed (exit $exitCode)" }
        }
    }
    catch {
        return [ordered]@{
            name     = $checkName
            type     = $checkType
            required = $isRequired
            skipped  = $false
            passed   = $false
            message  = "Check '$checkName' threw an exception: $_"
        }
    }
}

# ---------------------------------------------------------------------------
# ファイル読み込み
# ---------------------------------------------------------------------------

foreach ($filePath in @($BoardPath, $ProfilePath)) {
    if (-not (Test-Path -LiteralPath $filePath)) {
        $err = New-ResultObject -Gate $GateName -Result 'ERROR' -Required $false `
            -Message "File not found: $filePath"
        ConvertTo-JsonCompact $err
        exit 1
    }
}

$board = $null
$profiles = $null
try {
    $board    = Get-Content -LiteralPath $BoardPath   -Raw -Encoding UTF8 | ConvertFrom-Json
    $profiles = Get-Content -LiteralPath $ProfilePath -Raw -Encoding UTF8 | ConvertFrom-Json
}
catch {
    $err = New-ResultObject -Gate $GateName -Result 'ERROR' -Required $false `
        -Message "JSON parse error: $_"
    ConvertTo-JsonCompact $err
    exit 1
}

# ---------------------------------------------------------------------------
# Gate プロファイル取得
# ---------------------------------------------------------------------------

$gateProfile = $board.gate_profile
if ($null -eq $gateProfile) {
    $err = New-ResultObject -Gate $GateName -Result 'ERROR' -Required $false `
        -Message "Board field 'gate_profile' is missing or null"
    ConvertTo-JsonCompact $err
    exit 1
}

$profileObj = $profiles.profiles.PSObject.Properties |
              Where-Object { $_.Name -eq $gateProfile } |
              Select-Object -ExpandProperty Value -ErrorAction SilentlyContinue

if ($null -eq $profileObj) {
    $err = New-ResultObject -Gate $GateName -Result 'ERROR' -Required $false `
        -Message "Gate profile '$gateProfile' not found in $ProfilePath"
    ConvertTo-JsonCompact $err
    exit 1
}

$profileKey = $GATE_PROFILE_KEY_MAP[$GateName]
$gateConfig = $profileObj.PSObject.Properties |
              Where-Object { $_.Name -eq $profileKey } |
              Select-Object -ExpandProperty Value -ErrorAction SilentlyContinue

if ($null -eq $gateConfig) {
    $err = New-ResultObject -Gate $GateName -Result 'ERROR' -Required $false `
        -Message "Gate config key '$profileKey' not found in profile '$gateProfile'"
    ConvertTo-JsonCompact $err
    exit 1
}

$requiredValue = $gateConfig.required

# ---------------------------------------------------------------------------
# required フィールドによる早期分岐
# ---------------------------------------------------------------------------

# required: false → SKIP
if ($requiredValue -is [bool] -and $requiredValue -eq $false) {
    $result = New-ResultObject -Gate $GateName -Result 'SKIP' -Required $false `
        -Message "Gate '$GateName' is not required for profile '$gateProfile'. Skipped." `
        -Conditions @()
    ConvertTo-JsonCompact $result
    exit 2
}

# required: "blocked" → BLOCKED
if ($requiredValue -is [string] -and $requiredValue -eq 'blocked') {
    $result = New-ResultObject -Gate $GateName -Result 'BLOCKED' -Required $true `
        -Message "Gate '$GateName' is blocked in profile '$gateProfile'. Transition is structurally prohibited." `
        -Conditions @()
    ConvertTo-JsonCompact $result
    exit 3
}

# required: "on_escalation" → 評価条件を返す（LLM が最終判断）
if ($requiredValue -is [string] -and $requiredValue -eq 'on_escalation') {
    $escalationCond = $gateConfig.escalation_condition
    $impactAnalysis = $board.artifacts.PSObject.Properties |
                      Where-Object { $_.Name -eq 'impact_analysis' } |
                      Select-Object -ExpandProperty Value -ErrorAction SilentlyContinue

    # スクリプトで評価可能な条件: escalation.required フィールドの存在チェック
    $escalationRequired = $false
    $affectedFilesCount  = 0
    $conditionsMet       = @()

    if ($null -ne $impactAnalysis) {
        # artifacts.impact_analysis.escalation.required
        $escReq = Get-PropertyValue -Object $impactAnalysis -Path 'escalation.required'
        if ($null -ne $escReq -and $escReq -eq $true) {
            $escalationRequired = $true
        }

        # artifacts.impact_analysis.affected_files の件数
        $affectedFiles = $impactAnalysis.PSObject.Properties |
                         Where-Object { $_.Name -eq 'affected_files' } |
                         Select-Object -ExpandProperty Value -ErrorAction SilentlyContinue
        if ($null -ne $affectedFiles -and $affectedFiles -is [System.Array]) {
            $affectedFilesCount = $affectedFiles.Count
        }
    }

    $conditionsMet += [ordered]@{
        check    = 'escalation.required'
        value    = $escalationRequired
        met      = $escalationRequired
    }

    if ($gateProfile -eq 'stable') {
        $affectedMet = ($affectedFilesCount -ge 2)
        $conditionsMet += [ordered]@{
            check    = 'affected_files_count >= 2'
            actual   = $affectedFilesCount
            met      = $affectedMet
        }
    }

    # いずれかの条件が合致すれば "escalation required"
    $anyMet = $conditionsMet | Where-Object { $_.met -eq $true }

    if ($anyMet) {
        $result = New-ResultObject -Gate $GateName -Result 'ON_ESCALATION' -Required $true `
            -Message "Escalation condition met. Gate '$GateName' is now required. Invoke architect agent." `
            -Conditions $conditionsMet
        ConvertTo-JsonCompact $result
        exit 0
    }
    else {
        $result = New-ResultObject -Gate $GateName -Result 'SKIP' -Required $false `
            -Message "Escalation condition not met for profile '$gateProfile'. Gate '$GateName' skipped." `
            -Conditions $conditionsMet
        ConvertTo-JsonCompact $result
        exit 2
    }
}

# ---------------------------------------------------------------------------
# required: true → Gate ごとの通過条件を評価
# ---------------------------------------------------------------------------

$conditions  = [System.Collections.Generic.List[object]]::new()
$failReasons = [System.Collections.Generic.List[string]]::new()
$artifacts   = $board.artifacts

# --- test_gate: pass_rate / coverage_min / regression_required ---
if ($GateName -eq 'test') {
    $testResults = if ($null -ne $artifacts) {
        $artifacts.PSObject.Properties |
        Where-Object { $_.Name -eq 'test_results' } |
        Select-Object -ExpandProperty Value -ErrorAction SilentlyContinue
    } else { $null }

    # pass_rate チェック
    $requiredPassRate = $gateConfig.pass_rate
    if ($null -ne $requiredPassRate) {
        $actualPassRate = if ($null -ne $testResults) {
            Get-PropertyValue -Object $testResults -Path 'pass_rate'
        } else { $null }

        $met = ($null -ne $actualPassRate) -and ([double]$actualPassRate -ge [double]$requiredPassRate)
        $conditions.Add([ordered]@{
            check    = 'pass_rate'
            required = $requiredPassRate
            actual   = $actualPassRate
            met      = $met
        })
        if (-not $met) {
            $display = if ($null -eq $actualPassRate) { 'null' } else { $actualPassRate.ToString() }
            $failReasons.Add("pass_rate: required $requiredPassRate%, actual $display%")
        }
    }

    # coverage_min チェック
    $requiredCoverage = $gateConfig.coverage_min
    if ($null -ne $requiredCoverage) {
        $actualCoverage = if ($null -ne $testResults) {
            # coverage または coverage_percent を許容
            $v = Get-PropertyValue -Object $testResults -Path 'coverage'
            if ($null -eq $v) { $v = Get-PropertyValue -Object $testResults -Path 'coverage_percent' }
            $v
        } else { $null }

        $met = ($null -ne $actualCoverage) -and ([double]$actualCoverage -ge [double]$requiredCoverage)
        $conditions.Add([ordered]@{
            check    = 'coverage_min'
            required = $requiredCoverage
            actual   = $actualCoverage
            met      = $met
        })
        if (-not $met) {
            $display = if ($null -eq $actualCoverage) { 'null' } else { $actualCoverage.ToString() }
            $failReasons.Add("coverage_min: required $requiredCoverage%, actual $display%")
        }
    }

    # regression_required チェック
    $regressionRequired = $gateConfig.regression_required
    if ($null -ne $regressionRequired -and $regressionRequired -eq $true) {
        $regressionExecuted = if ($null -ne $testResults) {
            Get-PropertyValue -Object $testResults -Path 'regression.executed'
        } else { $null }
        $regressionPassed = if ($null -ne $testResults) {
            Get-PropertyValue -Object $testResults -Path 'regression.passed'
        } else { $null }

        $met = ($regressionExecuted -eq $true) -and ($regressionPassed -eq $true)
        $conditions.Add([ordered]@{
            check               = 'regression_required'
            regression_executed = $regressionExecuted
            regression_passed   = $regressionPassed
            met                 = $met
        })
        if (-not $met) {
            $failReasons.Add("regression_required: regression.executed=$regressionExecuted, regression.passed=$regressionPassed (both must be true)")
        }
    }

    # test_results artifact 自体の存在チェック
    if ($null -eq $testResults) {
        $conditions.Add([ordered]@{
            check = 'artifact_exists'
            name  = 'test_results'
            met   = $false
        })
        $failReasons.Add("artifact 'test_results' is null — test has not been executed yet")
    }
}

# --- review_gate: 最新の verdict が "lgtm" ---
elseif ($GateName -eq 'review') {
    # PSObject.Properties 経由で配列を取得。
    # PowerShell のパイプライン展開による配列アンロールを防ぐため @() で明示ラップする。
    $reviewFindings = $null
    if ($null -ne $artifacts) {
        $rfProp = $artifacts.PSObject.Properties | Where-Object { $_.Name -eq 'review_findings' }
        if ($null -ne $rfProp) {
            # @() で強制配列化 — 単一要素が PSCustomObject に unroll されるのを防ぐ
            $reviewFindings = @($rfProp.Value)
        }
    }

    $lastVerdict = $null
    if ($null -ne $reviewFindings -and $reviewFindings.Count -gt 0) {
        $lastEntry   = $reviewFindings[$reviewFindings.Count - 1]
        $lastVerdict = Get-PropertyValue -Object $lastEntry -Path 'verdict'
    }

    $met = ($lastVerdict -eq 'lgtm')
    $conditions.Add([ordered]@{
        check        = 'verdict'
        required     = 'lgtm'
        actual       = $lastVerdict
        entry_count  = if ($null -ne $reviewFindings) { $reviewFindings.Count } else { 0 }
        met          = $met
    })
    if (-not $met) {
        $display = if ($null -eq $lastVerdict) { 'null' } else { $lastVerdict }
        $failReasons.Add("review verdict: required 'lgtm', actual '$display'")
    }
}

# --- その他の Gate: 対応する Artifact が null でないことを確認 ---
else {
    $artifactKey = $GATE_ARTIFACT_MAP[$GateName]

    if ($null -ne $artifactKey) {
        $artifactValue = if ($null -ne $artifacts) {
            $artifacts.PSObject.Properties |
            Where-Object { $_.Name -eq $artifactKey } |
            Select-Object -ExpandProperty Value -ErrorAction SilentlyContinue
        } else { $null }

        $met = ($null -ne $artifactValue)
        $conditions.Add([ordered]@{
            check = 'artifact_exists'
            name  = $artifactKey
            met   = $met
        })
        if (-not $met) {
            $failReasons.Add("artifact '$artifactKey' is null — corresponding agent has not produced output yet")
        }
    }
    else {
        # submit_gate など artifact チェックが不要な Gate
        $conditions.Add([ordered]@{
            check   = 'artifact_exists'
            name    = 'n/a'
            note    = "No artifact check required for '$GateName' gate"
            met     = $true
        })
    }
}

# ---------------------------------------------------------------------------
# エビデンス検証
# ---------------------------------------------------------------------------
# gate-profiles.json の evidence_required が定義されている場合のみ実行（後方互換）

$evidenceStatus = $null

$evProp = $gateConfig.PSObject.Properties | Where-Object { $_.Name -eq 'evidence_required' }
if ($null -ne $evProp -and $null -ne $evProp.Value) {
    $evidenceRequired = @($evProp.Value)
    if ($evidenceRequired.Count -gt 0) {
        $evResult      = Test-Evidence -RequiredEvidence $evidenceRequired -Artifacts $artifacts -GateName $GateName
        $evidenceStatus = $evResult
        foreach ($evFail in $evResult.failures) {
            $failReasons.Add("evidence_check: $evFail")
        }
    }
}

# ---------------------------------------------------------------------------
# 自動品質チェック
# ---------------------------------------------------------------------------
# gate-profiles.json の automated_checks が定義されている場合のみ実行（後方互換）

$automatedCheckResults = $null

$acProp = $gateConfig.PSObject.Properties | Where-Object { $_.Name -eq 'automated_checks' }
if ($null -ne $acProp -and $null -ne $acProp.Value) {
    $automatedChecks = @($acProp.Value)
    if ($automatedChecks.Count -gt 0) {
        # settings.json の project セクションを読み込む
        $projectSettings = $null
        if (-not [string]::IsNullOrEmpty($SettingsPath) -and (Test-Path -LiteralPath $SettingsPath)) {
            try {
                $settingsObj     = Get-Content -LiteralPath $SettingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
                $projectSettings = $settingsObj.PSObject.Properties['project'] |
                                   Select-Object -ExpandProperty Value -ErrorAction SilentlyContinue
            }
            catch {
                Write-Warning "evaluate-gate: failed to load settings.json from '$SettingsPath': $_"
            }
        }

        $checkResultsList = [System.Collections.Generic.List[object]]::new()
        foreach ($check in $automatedChecks) {
            $checkResult = Invoke-AutomatedCheck -Check $check -ProjectSettings $projectSettings
            $checkResultsList.Add($checkResult)

            # required かつ失敗（スキップでない）の場合は FAIL 理由に追加
            if ($checkResult.required -eq $true -and $checkResult.passed -eq $false -and $checkResult.skipped -ne $true) {
                $failReasons.Add("automated_check '$($checkResult.name)': $($checkResult.message)")
            }
        }
        $automatedCheckResults = $checkResultsList.ToArray()
    }
}

# ---------------------------------------------------------------------------
# 最終判定
# ---------------------------------------------------------------------------

$overallPass = ($failReasons.Count -eq 0)
$resultStr   = if ($overallPass) { 'PASS' } else { 'FAIL' }
$message     = if ($overallPass) {
    "Gate '$GateName' passed all conditions for profile '$gateProfile'"
} else {
    "Gate '$GateName' failed: $($failReasons -join '; ')"
}

$result = New-ResultObject `
    -Gate       $GateName `
    -Result     $resultStr `
    -Required   $true `
    -Message    $message `
    -Conditions $conditions.ToArray()

$result['gate_profile'] = $gateProfile

if ($null -ne $evidenceStatus) {
    $result['evidence_status'] = $evidenceStatus
}
if ($null -ne $automatedCheckResults) {
    $result['automated_check_results'] = $automatedCheckResults
}

ConvertTo-JsonCompact $result
exit $(if ($overallPass) { 0 } else { 1 })
