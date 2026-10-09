param([Parameter(Mandatory=$true)][string]$InputDocx, [Parameter(Mandatory=$true)][string]$OutputPdf)
$ErrorActionPreference = 'Stop'
$reviewWord = $null
$reviewDocument = $null
try {
    $reviewWord = New-Object -ComObject Word.Application
    $reviewWord.Visible = $false
    $reviewWord.DisplayAlerts = 0
    $reviewDocument = $reviewWord.Documents.Open($InputDocx, $false, $true)
    $reviewDocument.ExportAsFixedFormat($OutputPdf, 17)
    Write-Output $OutputPdf
} finally {
    if ($reviewDocument) { $reviewDocument.Close(0) }
    if ($reviewWord) { $reviewWord.Quit() }
}
