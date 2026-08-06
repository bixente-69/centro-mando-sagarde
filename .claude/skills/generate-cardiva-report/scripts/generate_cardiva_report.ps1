[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$TemplatePath,

    [Parameter(Mandatory = $true)]
    [string]$DataPath,

    [Parameter(Mandatory = $true)]
    [string]$OutputDocx,

    [string]$OutputPdf,

    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$wdAlertsNone = 0
$wdCollapseEnd = 0
$wdPageBreak = 7
$wdFormatDocumentDefault = 16
$wdExportFormatPDF = 17
$wdRowHeightExactly = 2
$wdAlignParagraphLeft = 0
$wdAlignParagraphCenter = 1
$wdCellAlignVerticalCenter = 1
$wdColorBlack = 0
$wdColorWhite = 16777215
$wdLineStyleSingle = 1
$wdPreferredWidthPoints = 3

function Resolve-ExistingFile {
    param([string]$Path, [string]$Label)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "$Label no encontrado: $Path"
    }
    return (Resolve-Path -LiteralPath $Path).Path
}

function Resolve-OutputFile {
    param([string]$Path)
    $parent = Split-Path -Parent $Path
    if ([string]::IsNullOrWhiteSpace($parent)) {
        $parent = (Get-Location).Path
    }
    if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    $parentFull = (Resolve-Path -LiteralPath $parent).Path
    return [System.IO.Path]::Combine($parentFull, (Split-Path -Leaf $Path))
}

function Remove-ExistingOutput {
    param([string]$Path)
    if (Test-Path -LiteralPath $Path -PathType Leaf) {
        if (-not $Force) {
            throw "El archivo de salida ya existe. Use -Force para reemplazarlo: $Path"
        }
        Remove-Item -LiteralPath $Path -Force
    }
}

function Get-Items {
    param($Value)
    if ($null -eq $Value) {
        return @()
    }
    return @($Value)
}

function Test-UniqueIds {
    param($Items, [string]$Label)
    $ids = @($Items | ForEach-Object { [string]$_.id })
    $duplicates = @($ids | Group-Object | Where-Object { $_.Count -gt 1 })
    if ($duplicates.Count -gt 0) {
        throw "$Label contiene identificadores duplicados: $($duplicates.Name -join ', ')"
    }
}

function Test-RequiredIds {
    param($Items, [string[]]$Required, [string]$Label)
    $actual = @($Items | ForEach-Object { [string]$_.id })
    $missing = @($Required | Where-Object { $_ -notin $actual })
    if ($missing.Count -gt 0) {
        throw "$Label no contiene: $($missing -join ', ')"
    }
}

function Validate-Data {
    param($Data)

    foreach ($requiredProperty in @(
        'identification', 'battery', 'grounding', 'panels', 'analyzer', 'ups',
        'zones', 'lighting', 'deficiencies', 'materials', 'evidence', 'closure', 'signatures'
    )) {
        if ($Data.PSObject.Properties.Name -notcontains $requiredProperty) {
            throw "Falta la sección obligatoria '$requiredProperty' en el JSON."
        }
    }

    $batteryControls = Get-Items $Data.battery.controls
    $groundElements = Get-Items $Data.grounding.elements
    $zones = Get-Items $Data.zones
    $lighting = Get-Items $Data.lighting
    $deficiencies = Get-Items $Data.deficiencies
    $materials = Get-Items $Data.materials
    $evidence = Get-Items $Data.evidence

    Test-UniqueIds $batteryControls 'battery.controls'
    Test-UniqueIds $groundElements 'grounding.elements'
    Test-UniqueIds $zones 'zones'
    Test-UniqueIds $lighting 'lighting'
    Test-UniqueIds $deficiencies 'deficiencies'
    Test-UniqueIds $materials 'materials'
    Test-UniqueIds $evidence 'evidence'

    Test-RequiredIds $batteryControls @('B-01', 'B-02', 'B-03', 'B-04') 'battery.controls'
    Test-RequiredIds $groundElements @('P-01', 'P-02', 'P-03', 'P-04') 'grounding.elements'
    Test-RequiredIds $zones (1..18 | ForEach-Object { 'Z{0:D2}' -f $_ }) 'zones'
    Test-RequiredIds $lighting (1..22 | ForEach-Object { 'L{0:D2}' -f $_ }) 'lighting'

    if ($evidence.Count -ne $deficiencies.Count) {
        throw "Debe existir exactamente una evidencia/página de fotografía por deficiencia."
    }

    foreach ($deficiency in $deficiencies) {
        if (-not ($evidence | Where-Object { $_.deficiency -eq $deficiency.id })) {
            throw "No existe evidencia vinculada con $($deficiency.id)."
        }
    }
}

function Get-ById {
    param($Items, [string]$Id)
    return @($Items | Where-Object { [string]$_.id -eq $Id })[0]
}

function Get-Panel {
    param($Items, [string]$Code)
    return @($Items | Where-Object { [string]$_.code -eq $Code })[0]
}

function Get-CellText {
    param($Table, [int]$Row, [int]$Column)
    $text = $Table.Cell($Row, $Column).Range.Text
    return ($text -replace "[`r`a]", '').Trim()
}

function Set-Cell {
    param(
        $Table,
        [int]$Row,
        [int]$Column,
        [AllowNull()][object]$Text,
        [switch]$Center,
        [switch]$Result,
        [double]$FontSize = 0
    )

    $cell = $Table.Cell($Row, $Column)
    $range = $cell.Range.Duplicate
    $range.End = $range.End - 1
    $range.Text = if ($null -eq $Text) { '' } else { [string]$Text }
    $range.Font.Name = 'Arial Narrow'
    $range.Font.NameAscii = 'Arial Narrow'
    $range.Font.Color = $wdColorBlack
    if ($FontSize -gt 0) {
        $range.Font.Size = $FontSize
    }
    $range.ParagraphFormat.Alignment = if ($Center) { $wdAlignParagraphCenter } else { $wdAlignParagraphLeft }
    $range.ParagraphFormat.SpaceBefore = 0
    $range.ParagraphFormat.SpaceAfter = 0
    $range.ParagraphFormat.LineSpacingRule = 0
    $cell.VerticalAlignment = $wdCellAlignVerticalCenter

    if ($Result) {
        $cell.Shading.BackgroundPatternColor = $wdColorWhite
        $range.Font.Color = $wdColorBlack
        $range.Font.Bold = 0
    }
}

function Find-RowByPrefix {
    param($Table, [string]$Prefix)
    for ($row = 2; $row -le $Table.Rows.Count; $row++) {
        if ((Get-CellText $Table $row 1).StartsWith($Prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $row
        }
    }
    throw "No se encontró la fila '$Prefix' en la tabla."
}

function Resize-DataTable {
    param($Table, [int]$DataRowCount)
    $targetRows = 1 + [Math]::Max(1, $DataRowCount)
    while ($Table.Rows.Count -gt $targetRows) {
        $Table.Rows.Item($Table.Rows.Count).Delete()
    }
    while ($Table.Rows.Count -lt $targetRows) {
        $null = $Table.Rows.Add()
    }
}

function Compact-BeforePlan {
    param($Document)

    if ($Document.Shapes.Count -lt 1 -or $Document.Tables.Count -lt 25) {
        return
    }

    $tableEnd = $Document.Tables.Item(25).Range.End
    $shapeAnchor = $Document.Shapes.Item(1).Anchor.Start
    if ($shapeAnchor -le $tableEnd) {
        return
    }

    $gap = $Document.Range($tableEnd, $shapeAnchor)
    $visible = $gap.Text -replace "[\s`r`n`t`f`v]", ''
    if ($visible.Length -eq 0) {
        $gap.Delete() | Out-Null
        $pageBreak = $Document.Range($tableEnd, $tableEnd)
        $pageBreak.InsertBreak($wdPageBreak)
    }
}

function Set-AnnexTableFormatting {
    param($Table)

    $Table.AllowAutoFit = $false
    $Table.PreferredWidthType = $wdPreferredWidthPoints
    $Table.PreferredWidth = 515.9
    $Table.Rows.Item(1).HeightRule = $wdRowHeightExactly
    $Table.Rows.Item(1).Height = 25.5
    $Table.Rows.Item(2).HeightRule = $wdRowHeightExactly
    $Table.Rows.Item(2).Height = 456.4
    $Table.Rows.Item(3).HeightRule = $wdRowHeightExactly
    $Table.Rows.Item(3).Height = 119.1

    foreach ($border in @(-1, -2, -3, -4, -5, -6)) {
        $Table.Borders.Item($border).LineStyle = $wdLineStyleSingle
        $Table.Borders.Item($border).Color = 5780762
        $Table.Borders.Item($border).LineWidth = 8
    }

    $Table.Cell(1, 1).Shading.BackgroundPatternColor = 5780762
    $Table.Cell(2, 1).Shading.BackgroundPatternColor = $wdColorWhite
    $Table.Cell(3, 1).Shading.BackgroundPatternColor = $wdColorWhite
}

function Add-PhotoAnnex {
    param($Document, $Evidence, [int]$Number, [int]$Total)

    $endRange = $Document.Range($Document.Content.End - 1, $Document.Content.End - 1)
    if ($Number -gt 1) {
        $endRange.InsertBreak($wdPageBreak)
        $endRange.Collapse($wdCollapseEnd)
    }

    $table = $Document.Tables.Add($endRange, 3, 1)
    Set-AnnexTableFormatting $table

    Set-Cell $table 1 1 ("ANEXO FOTOGRÁFICO {0}/{1} · {2} · {3}" -f $Number, $Total, $Evidence.id, $Evidence.deficiency) -Center -FontSize 11
    $titleRange = $table.Cell(1, 1).Range.Duplicate
    $titleRange.End = $titleRange.End - 1
    $titleRange.Font.Color = $wdColorWhite
    $titleRange.Font.Bold = 1

    Set-Cell $table 2 1 ("ESPACIO PARA FOTOGRAFÍA`r`r{0}`r{1}" -f $Evidence.location, $Evidence.file) -Center -FontSize 14
    $photoRange = $table.Cell(2, 1).Range.Duplicate
    $photoRange.End = $photoRange.End - 1
    $photoRange.Font.Color = $wdColorBlack

    Set-Cell $table 3 1 ("OBSERVACIONES`r{0}`r`rFecha / actuación: __________________________________________________________" -f $Evidence.caption) -FontSize 10
    $obsRange = $table.Cell(3, 1).Range.Duplicate
    $obsRange.End = $obsRange.End - 1
    $obsRange.Font.Color = $wdColorBlack

    $table.Rows.Item(1).Range.ParagraphFormat.KeepWithNext = -1
    $table.Rows.Item(2).Range.ParagraphFormat.KeepWithNext = -1
}

function Lock-TotalPageFields {
    param($Document, [int]$PageCount)

    foreach ($section in $Document.Sections) {
        foreach ($footer in $section.Footers) {
            for ($fieldIndex = $footer.Range.Fields.Count; $fieldIndex -ge 1; $fieldIndex--) {
                $field = $footer.Range.Fields.Item($fieldIndex)
                if ($field.Type -eq 26) {
                    $field.Locked = $false
                    $field.Result.Text = [string]$PageCount
                    $field.Unlink()
                }
            }
        }
    }
}

$templateFull = Resolve-ExistingFile $TemplatePath 'Plantilla'
$dataFull = Resolve-ExistingFile $DataPath 'Datos'
$docxFull = Resolve-OutputFile $OutputDocx
$pdfFull = if ([string]::IsNullOrWhiteSpace($OutputPdf)) {
    [System.IO.Path]::ChangeExtension($docxFull, '.pdf')
} else {
    Resolve-OutputFile $OutputPdf
}

Remove-ExistingOutput $docxFull
Remove-ExistingOutput $pdfFull

$data = Get-Content -LiteralPath $dataFull -Raw -Encoding UTF8 | ConvertFrom-Json
Validate-Data $data

$word = $null
$document = $null

try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = $wdAlertsNone
    $document = $word.Documents.Open($templateFull, $false, $true)

    if ($document.Tables.Count -lt 25) {
        throw "La plantilla no contiene las 25 tablas esperadas."
    }

    $document.Content.Font.Name = 'Arial Narrow'
    $document.Content.Font.NameAscii = 'Arial Narrow'

    # 00. Identificación
    $table = $document.Tables.Item(1)
    Set-Cell $table 2 2 $data.identification.sagarde_code
    Set-Cell $table 2 4 $data.identification.work_order
    Set-Cell $table 3 2 $data.identification.client
    Set-Cell $table 3 4 $data.identification.site
    Set-Cell $table 4 2 $data.identification.date
    Set-Cell $table 4 4 $data.identification.period
    Set-Cell $table 5 2 $data.identification.entry_time
    Set-Cell $table 5 4 $data.identification.exit_time
    Set-Cell $table 6 2 $data.identification.technicians
    Set-Cell $table 6 4 $data.identification.cardiva_contact

    Set-Cell $document.Tables.Item(2) 1 1 'Uso SAGARDE. Estados: OK = correcto; DEF = deficiencia; N/R = no registrado; N/A = no aplica; PEND = pendiente. Toda marca DEF debe vincularse con un registro D-xx y una página F-xx.'

    # 01. Batería de condensadores
    $table = $document.Tables.Item(3)
    foreach ($item in (Get-Items $data.battery.controls)) {
        $row = Find-RowByPrefix $table $item.id
        Set-Cell $table $row 3 $item.status -Center -Result
        Set-Cell $table $row 4 $item.observation
    }

    $readings = $data.battery.readings
    $table = $document.Tables.Item(4)
    $readingValues = @(
        $readings.voltage, $readings.current, $readings.wpf,
        $readings.capacitor_current, $readings.temperature, $readings.kvar,
        $readings.ind, $readings.thdi, $readings.thdv
    )
    for ($column = 1; $column -le 9; $column++) {
        Set-Cell $table 2 $column $readingValues[$column - 1] -Center -Result
    }

    $table = $document.Tables.Item(5)
    foreach ($item in (Get-Items $data.battery.steps)) {
        $row = Find-RowByPrefix $table $item.id
        Set-Cell $table $row 2 $item.nominal -Center
        Set-Cell $table $row 3 $item.measured -Center
        Set-Cell $table $row 4 $item.status -Center -Result
        Set-Cell $table $row 5 $item.observation
    }

    # 02. Pararrayos y puesta a tierra
    $table = $document.Tables.Item(6)
    foreach ($item in (Get-Items $data.grounding.elements)) {
        $row = Find-RowByPrefix $table $item.id
        Set-Cell $table $row 3 $item.status -Center -Result
        $observation = [string]$item.observation
        if ($item.id -eq 'P-04' -and -not [string]::IsNullOrWhiteSpace([string]$data.grounding.observation)) {
            $observation = "$observation Medición: $($data.grounding.observation)"
        }
        Set-Cell $table $row 4 $observation -FontSize 7
    }

    $table = $document.Tables.Item(7)
    Set-Cell $table 2 1 $data.grounding.meter -Center
    Set-Cell $table 2 2 $data.grounding.serial -Center
    Set-Cell $table 2 3 $data.grounding.calibration -Center
    Set-Cell $table 2 4 $data.grounding.limit -Center
    Set-Cell $table 2 5 $data.grounding.result -Center -Result
    Set-Cell $table 2 6 $data.grounding.status -Center -Result

    # 03. Cuadros, analizador de redes y SAI
    $panelCodes = @('QG', 'QPB-C', 'QP1-R', 'QP2-I', 'QP2-C', 'QPB-V')
    $table = $document.Tables.Item(8)
    foreach ($code in $panelCodes) {
        $panel = Get-Panel $data.panels $code
        if ($null -eq $panel) {
            throw "No se encontraron datos para el cuadro $code."
        }
        $row = Find-RowByPrefix $table $code
        $values = @(
            $panel.controls.cleaning,
            $panel.controls.terminals,
            $panel.controls.identification,
            $panel.controls.ground,
            $panel.controls.differential,
            $panel.controls.temperature
        )
        for ($column = 2; $column -le 7; $column++) {
            Set-Cell $table $row $column $values[$column - 2] -Center -Result
        }
        Set-Cell $table $row 8 $panel.observation -FontSize 7
    }

    $table = $document.Tables.Item(10)
    foreach ($code in $panelCodes) {
        $panel = Get-Panel $data.panels $code
        $row = Find-RowByPrefix $table $code
        $values = @(
            $panel.measurements.v12,
            $panel.measurements.v23,
            $panel.measurements.v31,
            $panel.measurements.v1n,
            $panel.measurements.v2n,
            $panel.measurements.v3n,
            $panel.measurements.ground_ohm
        )
        for ($column = 2; $column -le 8; $column++) {
            Set-Cell $table $row $column $values[$column - 2] -Center -Result
        }
    }

    $table = $document.Tables.Item(11)
    $analyzerValues = @(
        $data.analyzer.v12,
        $data.analyzer.v23,
        $data.analyzer.v31,
        $data.analyzer.pf_l1,
        $data.analyzer.pf_l2,
        $data.analyzer.pf_l3,
        $data.analyzer.i_l1,
        $data.analyzer.i_l2,
        $data.analyzer.i_l3,
        $data.analyzer.kwh,
        $data.analyzer.status
    )
    for ($column = 1; $column -le 11; $column++) {
        Set-Cell $table 2 $column $analyzerValues[$column - 1] -Center -Result
    }

    $table = $document.Tables.Item(12)
    $upsValues = @(
        $data.ups.model,
        $data.ups.v_out,
        $data.ups.v_in,
        $data.ups.battery,
        $data.ups.autonomy,
        $data.ups.status,
        $data.ups.observation
    )
    for ($column = 1; $column -le 7; $column++) {
        Set-Cell $table 2 $column $upsValues[$column - 1] -Center -Result
    }
    Set-Cell $document.Tables.Item(13) 1 1 ("Observación general: {0}" -f $data.general_observation)

    # 04. Zonas
    $table = $document.Tables.Item(15)
    foreach ($item in (Get-Items $data.zones)) {
        $row = Find-RowByPrefix $table $item.id
        Set-Cell $table $row 2 $item.sockets -Center -Result
        Set-Cell $table $row 3 $item.voltage -Center -Result
        Set-Cell $table $row 4 $item.ground -Center -Result
        Set-Cell $table $row 5 $item.automation -Center -Result
        Set-Cell $table $row 6 $item.observation -FontSize 7
    }

    # 05 y 06. Alumbrado
    $table = $document.Tables.Item(18)
    foreach ($item in (Get-Items $data.lighting)) {
        $row = Find-RowByPrefix $table $item.id
        Set-Cell $table $row 3 $item.status -Center -Result
        Set-Cell $table $row 4 $item.units -Center -Result
        Set-Cell $table $row 5 $item.model -FontSize 7
        Set-Cell $table $row 6 $item.observation -FontSize 7
    }

    # 07. Deficiencias
    $deficiencies = Get-Items $data.deficiencies
    $table = $document.Tables.Item(20)
    Resize-DataTable $table $deficiencies.Count
    if ($deficiencies.Count -eq 0) {
        Set-Cell $table 2 1 '—' -Center
        Set-Cell $table 2 2 'Sin deficiencias'
        for ($column = 3; $column -le 7; $column++) {
            Set-Cell $table 2 $column '' -Result
        }
    } else {
        for ($index = 0; $index -lt $deficiencies.Count; $index++) {
            $item = $deficiencies[$index]
            $row = $index + 2
            Set-Cell $table $row 1 $item.id -Center
            Set-Cell $table $row 2 $item.location -FontSize 7
            Set-Cell $table $row 3 $item.description -FontSize 7
            Set-Cell $table $row 4 $item.criticality -Center -Result
            Set-Cell $table $row 5 $item.action -FontSize 7
            Set-Cell $table $row 6 $item.date -Center -Result
            Set-Cell $table $row 7 $item.status -Center -Result
        }
    }

    # 08. Materiales y evidencias
    $materials = Get-Items $data.materials
    $table = $document.Tables.Item(22)
    Resize-DataTable $table $materials.Count
    if ($materials.Count -eq 0) {
        Set-Cell $table 2 1 '—' -Center
        Set-Cell $table 2 2 'Sin material pendiente'
        for ($column = 3; $column -le 5; $column++) {
            Set-Cell $table 2 $column '' -Result
        }
    } else {
        for ($index = 0; $index -lt $materials.Count; $index++) {
            $item = $materials[$index]
            $row = $index + 2
            Set-Cell $table $row 1 $item.id -Center
            Set-Cell $table $row 2 $item.material -FontSize 7
            Set-Cell $table $row 3 $item.quantity -Center -Result
            Set-Cell $table $row 4 $item.destination -Center
            Set-Cell $table $row 5 $item.status -Center -Result
        }
    }

    $evidence = Get-Items $data.evidence
    $table = $document.Tables.Item(23)
    Resize-DataTable $table $evidence.Count
    if ($evidence.Count -eq 0) {
        Set-Cell $table 2 1 '—' -Center
        Set-Cell $table 2 2 'Sin evidencias pendientes'
        Set-Cell $table 2 3 ''
        Set-Cell $table 2 4 ''
    } else {
        for ($index = 0; $index -lt $evidence.Count; $index++) {
            $item = $evidence[$index]
            $row = $index + 2
            Set-Cell $table $row 1 $item.id -Center -FontSize 7
            Set-Cell $table $row 2 $item.file -FontSize 7
            Set-Cell $table $row 3 $item.location -FontSize 7
            Set-Cell $table $row 4 $item.deficiency -Center -FontSize 7
        }
    }

    # 09. Cierre
    $table = $document.Tables.Item(24)
    Set-Cell $table 2 2 $data.closure.general_result -Result -FontSize 8
    Set-Cell $table 3 2 $data.closure.report_status -Result -FontSize 8
    Set-Cell $table 4 2 $data.closure.technical_summary -FontSize 7
    Set-Cell $table 5 2 $data.closure.related_reports -FontSize 7
    Set-Cell $table 6 2 $data.closure.next_action -FontSize 7

    $table = $document.Tables.Item(25)
    Set-Cell $table 1 1 ("TÉCNICO SAGARDE`r{0}" -f $data.signatures.technician) -FontSize 8
    Set-Cell $table 1 2 ("SELLO`r{0}" -f $data.signatures.seal) -FontSize 8
    if ($table.Rows.Count -lt 2) {
        $null = $table.Rows.Add()
    }
    if ($table.Rows.Item(2).Cells.Count -gt 1) {
        $table.Cell(2, 1).Merge($table.Cell(2, 2))
    }
    Set-Cell $table 2 1 ("OBSERVACIONES / CONFORMIDAD CARDIVA`r`r")
    $table.Cell(2, 1).VerticalAlignment = 0
    $table.Rows.Item(2).HeightRule = $wdRowHeightExactly
    $table.Rows.Item(2).Height = 455

    Compact-BeforePlan $document

    # Una página completa y vacía para fotografía por cada deficiencia.
    for ($index = 0; $index -lt $evidence.Count; $index++) {
        Add-PhotoAnnex $document $evidence[$index] ($index + 1) $evidence.Count
    }

    $document.Repaginate()
    $document.Fields.Update() | Out-Null

    foreach ($section in $document.Sections) {
        foreach ($header in $section.Headers) {
            $header.Range.Font.Name = 'Arial Narrow'
        }
        foreach ($footer in $section.Footers) {
            $footer.Range.Font.Name = 'Arial Narrow'
            $footer.Range.Fields.Update() | Out-Null
        }
    }

    $document.Repaginate()
    foreach ($section in $document.Sections) {
        foreach ($footer in $section.Footers) {
            $footer.Range.Fields.Update() | Out-Null
        }
    }
    $pageCount = $document.ComputeStatistics(2)
    Lock-TotalPageFields $document $pageCount
    $document.SaveAs2($docxFull, $wdFormatDocumentDefault)
    $document.ExportAsFixedFormat($pdfFull, $wdExportFormatPDF)

    Write-Output "DOCX=$docxFull"
    Write-Output "PDF=$pdfFull"
    Write-Output "PAGES=$pageCount"
    Write-Output "DEFICIENCIES=$($deficiencies.Count)"
    Write-Output "PHOTO_PAGES=$($evidence.Count)"
}
finally {
    if ($null -ne $document) {
        $document.Close(0)
        [Runtime.InteropServices.Marshal]::ReleaseComObject($document) | Out-Null
    }
    if ($null -ne $word) {
        $word.Quit()
        [Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
