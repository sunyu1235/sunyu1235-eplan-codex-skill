---
name: eplan-development
description: Develop and automate EPLAN Electric P8 with Codex. Use for EPLAN C# scripts, EPLAN API extensions, parts/project/page data access, Remote Client apps, debugging automation, operating a running EPLAN instance through the local eplan MCP server, or resolving and importing EPLAN parts/macros on demand. Covers EPLAN 2022–2027.
---

# EPLAN Electric P8 Development for Codex

Use this skill for EPLAN Electric P8 scripting, API development, Remote Client automation, MCP-driven operations, and on-demand parts data retrieval.

## Choose the execution path first

1. **Operate a running EPLAN instance**: use the local `eplan` MCP server when available. Inspect the current project/state before mutating it.
2. **Find a part/macro by manufacturer + part number**: read `references/parts-sources.md`. Resolve/download only the requested part; never mirror a complete catalog.
3. **Verify EPLAN actions, parameters, or API signatures**: prefer the `eplan_rag` MCP dependency when available. If it is unavailable, query `https://rag2026.covaga.xyz/search` instead of guessing.
4. **Write code only**: read the matching reference file below, then generate the smallest correct EPLAN script/API/Remote Client implementation.
5. **Destructive project changes**: only perform them when the user requested the change. Prefer a project backup/export first when practical, and report exactly what was changed.

## The three development models

| Model | Runs | License | Use for |
|---|---|---|---|
| **Scripting** | Inside EPLAN (compiled on load, C# subset) | None extra | Automating actions, UI additions, event hooks, file exports |
| **API extension** | Inside EPLAN (compiled DLL) or offline app | API license | Deep data access: parts DB, project object model, pages, properties |
| **Remote Client** | External process driving a running EPLAN | RemoteClient DLLs | Orchestration, unattended pipelines, Cogineer generation |

Scripts can use some API namespaces such as `Eplan.EplApi.MasterData` from `[Start]`; see `references/api-data-access.md`.

## Reference files

Read only the references relevant to the task:

- `references/script-basics.md` — script structure, entry-point attributes, deployment, scripting limits.
- `references/actions-reference.md` — `CommandLineInterpreter`, `ActionCallingContext`, common actions and parameters.
- `references/core-classes.md` — `Progress`, `Decider`, `PathMap`, `Settings`, `MultiLangString`, ribbons, `QuietModeStep`, system messages.
- `references/api-data-access.md` — parts DB, properties, user properties, multilanguage strings, path resolution, DataModel/HEServices caveats.
- `references/e3d-installation-spaces.md` — runtime-reflection approach for 3D installation spaces and version-dependent assemblies.
- `references/remoting.md` — `EplanRemoteClient`, server discovery, dynamic ports, headless launch, version differences, Cogineer.
- `references/pitfalls.md` — blocking/message-loop failures, disposal, sequencing, error handling.
- `references/integration-patterns.md` — HTTP/SignalR/external-service integration patterns.
- `references/parts-sources.md` — WSCAD Universe, manufacturer sources, on-demand cache policy, and EDZ import workflow.

## On-demand parts workflow

When the user asks for an EPLAN part, macro, or EDZ for a model number:

1. Require/derive an exact manufacturer and part number. Do not substitute a similar model without telling the user.
2. Check only the local on-demand cache for that exact model; do not sync a complete manufacturer catalog.
3. Prefer an official manufacturer source when a stable generator/download service exists.
4. Use WSCAD Universe as the broad multi-manufacturer fallback. Its public integration interface can construct pre-filled BOM URLs from manufacturer ID + part number.
5. Treat browser login/download controls normally. Do not scrape around authentication or licensing. If a click/login is required, open the exact pre-filled page and continue from the downloaded artifact.
6. Validate the downloaded artifact and requested model before import.
7. For `.edz`, use EPLAN `partsmanagementapi` with `FORMAT:IXPartsImportExportEdz`; default to `MODE:0` (append new records only).
8. After import, search/re-read the part to verify it exists in parts management.

The included helper can generate the currently known source links:

```powershell
.\scripts\find-eplan-part.ps1 -Manufacturer Siemens -PartNumber '6ES7214-1AG40-0XB0'
```

Add `-OpenBrowser` to open the highest-priority source. For WSCAD manufacturers not in the helper's small known-ID map, resolve the current manufacturer ID instead of guessing it.

If EDZ import reports that the converter/module is unavailable, report that limitation. Do not bypass EPLAN license/module checks.

## MCP operating rules

When `eplan` tools are available:

- Connect/read first; do not assume which project is active.
- Execute EPLAN operations sequentially against one instance; never parallelize actions.
- For batch edits, inspect a representative sample before applying to the whole project.
- Prefer quiet/no-dialog execution only when the intended action is already verified.
- After a write, re-read or run the relevant EPLAN check/export to verify the result.
- If a tool/action name is uncertain, query `eplan_rag` or the REST RAG before invoking it.

If the local `eplan` MCP is missing, do not invent equivalent shell/UI automation. Tell the user to run the included `scripts/setup-eplan-mcp.ps1`, or continue with code-generation/source-resolution work if that still satisfies the request.

## Documentation lookup

The upstream project exposes a semantic EPLAN P8 documentation service:

```bash
curl -X POST https://rag2026.covaga.xyz/search \
  -H "Content-Type: application/json" \
  -d '{"query":"export project to PDF parameters","topK":5}'
```

Use narrow English queries. Verify undocumented/case-sensitive action names and parameter names before using them.

## Golden rules

1. EPLAN actions are pseudo-asynchronous. External or long-running automation can block without the correct message-loop pattern; read `references/pitfalls.md` before multi-step automation.
2. Dispose `ActionCallingContext`, `EplanRemoteClient`, temp clients, and other disposable EPLAN objects with `using` or `finally`.
3. Operations against one EPLAN instance are sequential. Never fire EPLAN actions in parallel.
4. Never use empty `catch {}`. Log/report errors explicitly.
5. EPLAN 2025+ remoting requires **Remote Client Access / Allow remote access** enabled in EPLAN settings.
6. For EPLAN 2025 API/RemoteClient work, target .NET Framework 4.8.1 unless the installed EPLAN version's SDK says otherwise. Resolve EPLAN DLLs from the installed Platform `Bin` directory.
7. Verify action names/parameters with the EPLAN RAG before guessing.
8. Do not directly `using Eplan.EplApi.DataModel;` or `...HEServices;` in EPLAN scripts where the script compiler cannot resolve them. Use the runtime-reflection pattern in `references/e3d-installation-spaces.md`.
9. Do not `RegisterScript` a one-shot `[Start]` script. Execute it directly; registration is for persistent declared actions/events/register hooks.
10. Never mirror proprietary parts portals or bypass their authentication/subscription controls. Retrieve requested parts on demand through normal source access.
