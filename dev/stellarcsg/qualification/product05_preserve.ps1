$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$starting = Get-Content -Raw -LiteralPath (Join-Path $root 'dev/stellarcsg/reports/recovery04/starting-refs.txt')
$checks = @()
foreach ($block in [regex]::Split($starting, '\r?\n\r?\n')) {
    $head = [regex]::Match($block, '(?m)^HEAD ([a-f0-9]+)\r?$')
    $branch = [regex]::Match($block, '(?m)^branch (.+?)\r?$')
    if ($head.Success -and $branch.Success) {
        $ref = $branch.Groups[1].Value
        if ($ref -in @('refs/heads/JS/stellarcsg-fast-recovery-20260913-04', 'refs/heads/JS/stellarcsg-recovery-bank-20260913-04')) { continue }
        $actual = git -C $root rev-parse $ref
        if ($LASTEXITCODE -ne 0) { throw "Cannot inspect $ref" }
        $checks += @{ref=$ref; expected=$head.Groups[1].Value; actual=$actual; unchanged=($actual -eq $head.Groups[1].Value)}
    }
}
$ref = 'refs/heads/JS/stellarcsg-fast-recovery-20260913-04'
$actual = git -C $root rev-parse $ref
$checks += @{ref=$ref; expected='57cb1fbf75a54a0fa75e70386922ad9cfecf06b1'; actual=$actual; unchanged=($actual -eq '57cb1fbf75a54a0fa75e70386922ad9cfecf06b1')}
$ref = 'refs/heads/JS/stellarcsg-recovery-bank-20260913-04'
$actual = git -C $root rev-parse $ref
$checks += @{ref=$ref; expected='fe3392b9f563bd66f67b31ca51385ffb100f3780'; actual=$actual; unchanged=($actual -eq 'fe3392b9f563bd66f67b31ca51385ffb100f3780')}
$extra = @{
 'refs/heads/archive/stellarcsg-qualified-c67b68fd-20260831'='c67b68fdaf7be2049308db7da449f14a25123847'
 'refs/heads/develop'='9a62e431d3101799e6179a6d0cf3b37440062e23'
 'refs/remotes/origin/master'='55b52b7ef3c9415ce045712132bf31c2a013d8c8'
}
foreach ($ref in $extra.Keys) {
    $actual = git -C $root rev-parse $ref
    $checks += @{ref=$ref; expected=$extra[$ref]; actual=$actual; unchanged=($actual -eq $extra[$ref])}
}
$receipt = @{checks=$checks; changed_count=@($checks | Where-Object {-not $_.unchanged}).Count; push_performed=$false; dependency_acquisition_bytes=0; production_kernel_modified=$false}
$receipt | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $root 'dev/stellarcsg/reports/product05/preservation.json')
if ($receipt.changed_count -ne 0) { throw 'Protected reference changed' }
Write-Output "$($checks.Count) reference checks unchanged"
