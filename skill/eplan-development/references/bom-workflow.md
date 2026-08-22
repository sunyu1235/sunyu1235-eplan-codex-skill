# BOM-driven EPLAN parts workflow

Use this workflow when the user provides a BOM/parts list and wants Codex to resolve models, retrieve EPLAN data on demand, import missing parts, and assign them to devices.

## Goal

Turn a BOM into verified EPLAN part assignments without maintaining a full local parts mirror.

Pipeline:

1. Parse BOM rows.
2. Normalize manufacturer + exact part number.
3. Deduplicate identical manufacturer/part combinations for retrieval.
4. Check the local on-demand cache and current EPLAN parts database.
5. Resolve/download only missing requested parts from manufacturer sources or WSCAD Universe.
6. Import missing `.edz` data with `partsmanagementapi`.
7. Match BOM rows to existing EPLAN devices by exact device tag / full DT when present.
8. Add the verified part reference to the matched Function.
9. Verify the assigned part after each batch and produce a result table.

## BOM columns

The parser accepts CSV and XLSX and tries to auto-detect common English/Chinese column names.

Preferred fields:

- Manufacturer: `manufacturer`, `vendor`, `brand`, `厂家`, `制造商`, `品牌`
- Part number/model: `part_number`, `part number`, `model`, `type`, `型号`, `订货号`, `物料号`, `零件号`
- Quantity: `qty`, `quantity`, `count`, `数量`
- Device tag / DT: `device_tag`, `dt`, `tag`, `device`, `设备代号`, `设备标识`, `位号`
- Variant: `variant`, `变体`
- Page: `page`, `页`, `页号`
- Function location: `function_location`, `location`, `安装位置`, `功能位置`
- Description: `description`, `name`, `名称`, `描述`

Manufacturer + part number are the minimum for automatic retrieval. Device tag is required for safe automatic assignment to an existing device.

## Safety/matching rules

- Exact model numbers win. Never silently replace with a similar or successor model.
- Exact full device tag wins. Do not assign a part when several Functions match the same ambiguous tag.
- If a BOM row has no device tag, import/cache the part but leave assignment status as `unassigned` unless the user explicitly asks to create/place new devices.
- Do not create graphical symbols merely because a BOM row exists. A BOM is usually a material list, not placement geometry.
- Only place a new graphical device/macro automatically when the BOM or a companion placement table provides enough unambiguous placement data (page + coordinates/macro/representation or another verified placement rule).
- For duplicate BOM rows targeting the same DT, preserve row order and quantities; report conflicts rather than overwriting silently.
- Default EDZ import mode is append-only (`MODE:0`).

## EPLAN part assignment

EPLAN's supported API model is to add an ArticleReference to a Function after the part already exists in the system/project parts database.

Verified API pattern:

```csharp
ArticleReference ar = function.AddArticleReference(partNumber, variant, quantity);
```

For the common default variant/count:

```csharp
ArticleReference ar = function.AddArticleReference(partNumber);
```

The part must already exist in the system or project database. Therefore retrieval/import happens before assignment.

When using a script or API extension to assign BOM rows:

1. Resolve the exact target Function by full DT using the installed EPLAN version's supported finder/search API; verify signatures with `eplan_rag` before coding.
2. Reject zero matches and multiple matches.
3. Verify the part number exists in parts management.
4. Add the ArticleReference with the BOM variant/count.
5. Re-read `function.ArticleReferences` after writing and verify part number/count.

If the device is fixed or the function category cannot accept another article reference, report the EPLAN exception instead of forcing it.

## Batch behavior

Process in two phases so a network/download failure cannot leave half of the BOM silently assigned:

### Phase A — resolve/import

Build one unique part queue from all rows and resolve/import each unique part once.

Recommended row states:

- `already_available`
- `downloaded_imported`
- `needs_login`
- `not_found`
- `invalid_model`
- `import_failed`

### Phase B — assign

Only rows whose required part is verified available enter assignment.

Recommended assignment states:

- `assigned`
- `unassigned_no_dt`
- `device_not_found`
- `device_ambiguous`
- `already_assigned`
- `conflict_existing_part`
- `assignment_failed`

Before mass assignment, test one representative row and re-read it successfully. Then continue sequentially; never write to one EPLAN instance in parallel.

## Input preparation helper

Use:

```powershell
python .\scripts\parse-bom.py "C:\path\BOM.xlsx" --out "C:\temp\eplan-bom.json"
```

For CSV:

```powershell
python .\scripts\parse-bom.py "C:\path\BOM.csv" --out "C:\temp\eplan-bom.json"
```

The output contains normalized rows plus a deduplicated `parts` queue. XLSX parsing requires `openpyxl`; install it normally if missing:

```powershell
python -m pip install openpyxl
```

## Result report

At the end, report at least:

| Row | DT | Manufacturer | Part number | Retrieval | Import | Assignment | Note |
|---:|---|---|---|---|---|---|---|

Never claim a BOM row is complete until the part is verified in EPLAN and, when a DT was supplied, the Function's ArticleReferences verifies the assignment.
