# On-demand EPLAN parts data sources

Use this guide when a user gives a manufacturer + part number and wants EPLAN parts/macros without maintaining a full local parts mirror.

## Core policy

- **Do not mirror or bulk-download a whole catalog.** Resolve only the requested part numbers.
- Prefer manufacturer-supplied ECAD data, then WSCAD Universe, then EPLAN Data Portal only when the user has legitimate access.
- Cache only files that were actually downloaded/used. A suggested cache root is `%USERPROFILE%\.codex\eplan-parts-cache\<manufacturer>\<part-number>\`.
- Never bypass login, subscription, license, or download controls. If a source requires browser login, open the exact/prefilled page and let the user complete the normal download.
- Verify the downloaded filename/part number before importing it into EPLAN.

## Source order

### 1. WSCAD Universe — broad fallback

WSCAD Universe currently advertises more than 2.2 million parts from 457 manufacturers and supports EDZ, WSCAD, DWG and STEP. Registration/use is free.

The public WSCADUniverse Actions interface is designed to build pre-filled BOM URLs from manufacturer IDs and part numbers. It is useful for sending Codex directly to a requested part without copying the catalog.

Single-manufacturer URL pattern:

```text
https://www.wscaduniverse.com/inbom?manufacturerId=<ID>&parts=<URL-ENCODED-PART-NUMBER>
```

Known IDs documented by WSCAD examples:

- ABB = `1`
- Schneider Electric = `2`
- Siemens = `77`

If the manufacturer ID is unknown, resolve it from WSCAD's current manufacturer list/documentation instead of guessing.

Important: the public Actions API documents BOM/deep-link generation, not a general unauthenticated EDZ download endpoint. WSCAD download can require a signed-in browser session. Treat it as **on-demand interactive download**, not as a license-bypass/headless scraper.

### 2. Manufacturer sources

#### Phoenix Contact

Official EPLAN P8 file generator:

```text
https://www.phoenixcontact.com/zh-cn/products/eplan-p8-file-generator
```

It accepts one or more order numbers and generates an EPLAN EDZ file containing product data. Prefer this source for Phoenix Contact parts.

#### Siemens

Official CAx Download Manager entry:

```text
https://www.siemens.com/cax
```

Siemens documents EPLAN Electric P8 macros among the CAx download types. Login/interactive selection may be required. Prefer it for Siemens parts when WSCAD data is missing or stale.

### 3. EPLAN Data Portal — optional

Use only when the user's EPLAN/EPLAN Cloud account has legitimate access to the required download functions. Do not attempt to bypass subscription or license checks.

## Runtime workflow

Given `manufacturer + part number`:

1. Normalize manufacturer and part number. Preserve punctuation in the real part number.
2. Check the local on-demand cache for an exact prior download.
3. If not cached, prefer an official manufacturer generator/download page when known.
4. Also construct a WSCAD Universe deep link when its manufacturer ID is known.
5. If a source exposes a normal direct file download, download only that requested artifact.
6. If login/UI is required, open the exact source page and instruct the user to complete the normal download; then continue from the downloaded file.
7. Validate that the artifact is an `.edz` (or supported manufacturer macro/archive) and matches the requested part.
8. Before importing, back up the parts database/project when a bulk or update operation could overwrite records.
9. Import EDZ through EPLAN, append-only by default.

## EPLAN EDZ import

Current EPLAN Platform documentation exposes the `partsmanagementapi` action and the `IXPartsImportExportEdz` converter.

Append new records only:

```text
partsmanagementapi /TYPE:IMPORT /MODE:0 /FORMAT:IXPartsImportExportEdz /IMPORTFILE:C:\path\part.edz
```

Update existing records only:

```text
partsmanagementapi /TYPE:IMPORT /MODE:1 /FORMAT:IXPartsImportExportEdz /IMPORTFILE:C:\path\part.edz
```

Update existing records and append new records:

```text
partsmanagementapi /TYPE:IMPORT /MODE:2 /FORMAT:IXPartsImportExportEdz /IMPORTFILE:C:\path\part.edz
```

Default to `MODE:0` unless the user explicitly wants existing parts updated.

EDZ availability/import can depend on the installed EPLAN module/package. If EPLAN reports the EDZ converter/module is unavailable, report that limitation. Do not work around EPLAN licensing.

## Codex behavior

When the local `eplan` MCP is available:

- Use it to inspect parts management first if needed.
- Import the downloaded EDZ with the verified `partsmanagementapi` action.
- Re-read/search the part after import to verify it exists.
- Never invoke several EPLAN import actions in parallel.

When no EPLAN MCP is available, provide/open the on-demand source and leave the downloaded EDZ ready for manual import.
