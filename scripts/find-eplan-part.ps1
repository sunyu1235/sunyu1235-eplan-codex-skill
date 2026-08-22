param(
    [Parameter(Mandatory = $true)]
    [string]$Manufacturer,

    [Parameter(Mandatory = $true)]
    [string]$PartNumber,

    [int]$WscadManufacturerId = 0,

    [ValidateSet('IEC','NFPA')]
    [string]$Norm = 'IEC',

    [switch]$OpenBrowser
)

$ErrorActionPreference = 'Stop'

function Normalize-Key([string]$value) {
    return (($value.Trim().ToLowerInvariant()) -replace '[^a-z0-9]', '')
}

$manufacturerKey = Normalize-Key $Manufacturer
$part = $PartNumber.Trim()
if ([string]::IsNullOrWhiteSpace($part)) {
    throw 'PartNumber must not be empty.'
}

# IDs below are explicitly shown in the current WSCADUniverse Actions documentation/examples.
$knownWscadIds = @{
    'abb'               = 1
    'schneider'         = 2
    'schneiderelectric' = 2
    'siemens'           = 77
}

if ($WscadManufacturerId -le 0 -and $knownWscadIds.ContainsKey($manufacturerKey)) {
    $WscadManufacturerId = $knownWscadIds[$manufacturerKey]
}

$results = [System.Collections.Generic.List[object]]::new()

# Manufacturer-owned sources first where we have a stable official entry point.
switch ($manufacturerKey) {
    'phoenixcontact' {
        $results.Add([pscustomobject]@{
            Priority      = 1
            Source        = 'Phoenix Contact EPLAN P8 file generator'
            Url           = 'https://www.phoenixcontact.com/zh-cn/products/eplan-p8-file-generator'
            Mode          = 'interactive-generator'
            ExpectedFile  = 'EDZ'
            RequiresLogin = $false
            Note          = "Paste/order number '$part' into the official generator and download the generated EDZ."
        })
    }
    'siemens' {
        $results.Add([pscustomobject]@{
            Priority      = 1
            Source        = 'Siemens CAx Download Manager'
            Url           = 'https://www.siemens.com/cax'
            Mode          = 'interactive-download'
            ExpectedFile  = 'EPLAN macro / CAx package'
            RequiresLogin = $true
            Note          = "Search MLFB '$part'; select EPLAN Electric P8 macro/CAx data."
        })
    }
}

if ($WscadManufacturerId -gt 0) {
    $encodedPart = [uri]::EscapeDataString($part)
    $wscadUrl = "https://www.wscaduniverse.com/inbom?manufacturerId=$WscadManufacturerId&parts=$encodedPart"
    $results.Add([pscustomobject]@{
        Priority      = 2
        Source        = 'WSCAD Universe'
        Url           = $wscadUrl
        Mode          = 'interactive-download'
        ExpectedFile  = 'EDZ / DWG / STEP'
        RequiresLogin = $true
        Note          = "Pre-filled WSCAD BOM for '$part'. Download only the requested part; do not mirror the catalog."
    })
} else {
    $results.Add([pscustomobject]@{
        Priority      = 2
        Source        = 'WSCAD Universe'
        Url           = 'https://www.wscaduniverse.com/'
        Mode          = 'manufacturer-id-required'
        ExpectedFile  = 'EDZ / DWG / STEP'
        RequiresLogin = $true
        Note          = "Resolve the current WSCAD manufacturer ID for '$Manufacturer' first; do not guess it."
    })
}

$results.Add([pscustomobject]@{
    Priority      = 9
    Source        = 'EPLAN Data Portal'
    Url           = 'https://dataportal.eplan.com/'
    Mode          = 'optional-authorized-source'
    ExpectedFile  = 'EPLAN part data'
    RequiresLogin = $true
    Note          = 'Use only when the account has legitimate access to the required download feature.'
})

$results = $results | Sort-Object Priority

if ($OpenBrowser) {
    $first = $results | Select-Object -First 1
    Start-Process $first.Url
}

[pscustomobject]@{
    Manufacturer        = $Manufacturer
    PartNumber          = $part
    Norm                = $Norm
    WscadManufacturerId = if ($WscadManufacturerId -gt 0) { $WscadManufacturerId } else { $null }
    Policy              = 'on-demand-only; no full catalog mirror'
    Sources             = @($results)
} | ConvertTo-Json -Depth 5
