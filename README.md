# EPLAN Development for Codex

这是把 `covagashi/eplan-rag-mcp` 中的 `eplan-development` Claude Code Skill 迁移到 Codex 的 Windows 安装包，并增加按型号实时查找/导入 EPLAN 部件数据以及 BOM 驱动部件分配的能力。

## 迁移内容

- Codex 原生 `SKILL.md`，支持 Codex CLI / IDE 扩展 / Codex app 的 Skill 发现机制。
- `agents/openai.yaml`，声明 EPLAN 文档 RAG 的 MCP 依赖。
- 保留上游 8 个 EPLAN reference 文件；安装时从上游仓库拉取最新版本，避免复制后长期过期。
- 新增 `references/parts-sources.md`：WSCAD Universe + 厂商官网 + 可选 EPLAN Data Portal 的按需部件策略。
- 新增 `references/bom-workflow.md`：BOM 列识别、型号去重下载、EDZ 导入、DT 精确匹配和部件分配规则。
- 新增 `scripts/find-eplan-part.ps1`：按“厂家 + 型号”生成实时部件来源入口。
- 新增 `scripts/parse-bom.py`：自动解析 CSV/XLSX BOM，生成标准化 BOM 行和唯一部件队列。
- `setup-eplan-mcp.ps1`：安装/更新上游本地 EPLAN MCP，并注册到 Codex。
- `verify.ps1`：检查 Skill、reference、BOM/部件解析器、EPLAN 安装目录和 Codex MCP 状态。

## 一键安装（推荐）

PowerShell 在本目录运行：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install.ps1 -Scope Global -SetupMcp
```

它会：

1. 把 Skill 安装到 `%USERPROFILE%\.codex\skills\eplan-development`。
2. 下载最新 8 个上游 reference 文件，同时保留本仓库自己的 `parts-sources.md` 与 `bom-workflow.md`。
3. 克隆/更新 `covagashi/eplan-rag-mcp` 到 `%USERPROFILE%\.codex\eplan-tools\eplan-rag-mcp`。
4. 安装 Python 依赖。
5. 注册本地 `eplan` MCP。
6. 注册远程 `eplan_rag` MCP。

只装 Skill、不连接 EPLAN：

```powershell
.\install.ps1 -Scope Global
```

安装为某个工程专用 Skill：

```powershell
.\install.ps1 -Scope Project -ProjectRoot 'C:\your\project'
```

## BOM → 自动找型号 → 导入 → 分配到设备

目标用法不是让你一个个告诉 Codex 型号，而是直接给它 BOM：

```text
读取这个 BOM，把里面缺失的 EPLAN 部件按需下载并导入，然后按设备代号分配到当前工程。先做 1 行验证，确认无误后再批量执行。
```

工作流：

1. 读取 CSV/XLSX/XLSM BOM。
2. 自动识别厂家/品牌、型号/订货号、数量、设备代号/DT、变体、页面、位置等常见中英文列。
3. 对 BOM 型号去重；同一个型号只查找/下载/导入一次。
4. 优先检查 EPLAN 本地部件库与按需缓存。
5. 缺失型号才实时查厂家官网/WSCAD Universe；不复制整个部件库。
6. EDZ 导入成功并验证后，再进入设备分配阶段。
7. BOM 有准确 DT/设备代号时，精确匹配现有 EPLAN Function，并添加 ArticleReference。
8. 没有 DT 的行只导入/缓存部件，不擅自把符号摆到图纸里。
9. 先验证一条代表性记录，再顺序批量处理。
10. 最后输出每行的下载、导入、设备匹配和分配状态。

手工解析 BOM：

```powershell
python .\skill\eplan-development\scripts\parse-bom.py 'C:\project\BOM.xlsx' --out 'C:\temp\eplan-bom.json'
```

XLSX 需要 `openpyxl`：

```powershell
python -m pip install openpyxl
```

EPLAN 官方 API 的正确思路是：部件先存在于系统/项目部件库，然后给目标 Function 添加 ArticleReference。Skill 会要求写入后重新读取 `ArticleReferences` 核对，不能只凭“动作没报错”就算成功。

## 实时部件查找：不复制整个部件库

这套功能采用 **on-demand（按需）** 方式，不会把 WSCAD/EPLAN/厂家整个目录复制到电脑：

1. 你给 Codex 一个准确型号，例如 `Siemens 6ES7214-1AG40-0XB0`。
2. Codex 先检查本地是否已经缓存过这个型号。
3. 没有就实时查厂家官网和 WSCAD Universe。
4. 能正常直下的数据只下载这个型号；需要登录/网页确认的来源直接打开到对应入口。
5. 下载得到 EDZ 后，通过 EPLAN `partsmanagementapi` 导入，默认只追加新记录。

WSCAD Universe 目前公开说明提供 220 万+部件、457 家厂家以及 EDZ/DWG/STEP 等格式。它的公开开发接口可生成厂家 ID + 型号对应的预填 BOM 链接；实际 EDZ 下载可能需要正常登录网页，因此这里不做绕登录的抓取。

手工测试解析器：

```powershell
.\scripts\find-eplan-part.ps1 -Manufacturer Siemens -PartNumber '6ES7214-1AG40-0XB0'
```

直接打开最高优先级来源：

```powershell
.\scripts\find-eplan-part.ps1 -Manufacturer Siemens -PartNumber '6ES7214-1AG40-0XB0' -OpenBrowser
```

WSCAD 官方文档中明确示例的厂家 ID 已内置：

- ABB = `1`
- Schneider Electric = `2`
- Siemens = `77`

其他厂家 ID 不猜测，运行时再从当前 WSCAD 资料解析。

已加入的厂家优先入口：

- Phoenix Contact：官方 EPLAN P8 文件生成器，可按订货号生成 EDZ。
- Siemens：官方 CAx Download Manager，可获取 EPLAN Electric P8 宏/CAx 数据。
- WSCAD Universe：多厂家大库，作为通用 EDZ/宏数据来源。
- EPLAN Data Portal：只在账号具备正常授权访问时作为可选来源。

EDZ 默认导入动作：

```text
partsmanagementapi /TYPE:IMPORT /MODE:0 /FORMAT:IXPartsImportExportEdz /IMPORTFILE:C:\path\part.edz
```

如果安装的 EPLAN 版本/模块提示 EDZ converter 不可用，Skill 会直接报告，不会尝试绕过授权。

## EPLAN 端必须打开远程访问

在 EPLAN 中启用：

`File > Settings > Workstation > Interfaces > Remote access > Allow remote access via Remote Client`

然后重新启动 Codex，启动 EPLAN，再对 Codex 说例如：

- `连接 EPLAN，先只读检查当前工程。`
- `读取这个 BOM，把缺失部件按需下载并导入，再按设备代号分配到当前工程。先测试 1 行。`
- `检查所有电机设备编号和交叉引用，只报告问题不要修改。`
- `找 Siemens 6ES7214-1AG40-0XB0 的 EPLAN 部件，找到后导入本地部件库。`
- `找 Phoenix Contact 订货号 2904600 的 EDZ，只下载这个型号。`
- `把当前工程导出 PDF，执行前先确认输出路径。`
- `根据这个 IO 表生成 EPLAN C# 脚本。`

## 验证

```powershell
.\verify.ps1 -Scope Global
```

正常时应看到：

- `SKILL.md` 存在；
- `References: 10/10`；
- `parts-sources.md`、`bom-workflow.md`、`find-eplan-part.ps1`、`parse-bom.py` 存在；
- `codex mcp list` 中有 `eplan` 与 `eplan_rag`；
- EPLAN Platform 安装目录被检测到。

## 依赖

- Windows
- EPLAN Electric P8 2024/2025/2026/2027（上游 MCP 当前支持范围）
- Python 3.10+ 64-bit
- `openpyxl`（读取 XLSX BOM 时）
- Git
- Codex CLI

## 上游与许可

EPLAN 知识内容和 MCP 代码来自：`covagashi/eplan-rag-mcp`。
上游采用 MIT License。此迁移包没有修改上游 MCP 实现；它只增加 Codex Skill 元数据、安装/配置逻辑、按需部件来源策略、BOM 自动化流程和 Codex 使用规则。
