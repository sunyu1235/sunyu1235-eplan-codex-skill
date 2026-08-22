# EPLAN Development for Codex

这是把 `covagashi/eplan-rag-mcp` 中的 `eplan-development` Claude Code Skill 迁移到 Codex 的 Windows 安装包。

## 迁移内容

- Codex 原生 `SKILL.md`，支持 Codex CLI / IDE 扩展 / Codex app 的 Skill 发现机制。
- `agents/openai.yaml`，声明 EPLAN 文档 RAG 的 MCP 依赖。
- 保留上游 8 个 EPLAN reference 文件；安装时从上游仓库拉取最新版本，避免复制后长期过期。
- `setup-eplan-mcp.ps1`：安装/更新上游本地 EPLAN MCP，并注册到 Codex。
- `verify.ps1`：检查 Skill、reference、EPLAN 安装目录和 Codex MCP 状态。

## 一键安装（推荐）

PowerShell 在本目录运行：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install.ps1 -Scope Global -SetupMcp
```

它会：

1. 把 Skill 安装到 `%USERPROFILE%\.codex\skills\eplan-development`。
2. 下载最新 8 个上游 reference 文件。
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

## EPLAN 端必须打开远程访问

在 EPLAN 中启用：

`File > Settings > Workstation > Interfaces > Remote access > Allow remote access via Remote Client`

然后重新启动 Codex，启动 EPLAN，再对 Codex 说例如：

- `连接 EPLAN，先只读检查当前工程。`
- `检查所有电机设备编号和交叉引用，只报告问题不要修改。`
- `把当前工程导出 PDF，执行前先确认输出路径。`
- `根据这个 IO 表生成 EPLAN C# 脚本。`

## 验证

```powershell
.\verify.ps1 -Scope Global
```

正常时应看到：

- `SKILL.md` 存在；
- `References: 8/8`；
- `codex mcp list` 中有 `eplan` 与 `eplan_rag`；
- EPLAN Platform 安装目录被检测到。

## 依赖

- Windows
- EPLAN Electric P8 2024/2025/2026/2027（上游 MCP 当前支持范围）
- Python 3.10+ 64-bit
- Git
- Codex CLI

## 上游与许可

EPLAN 知识内容和 MCP 代码来自：`covagashi/eplan-rag-mcp`。
上游采用 MIT License。此迁移包没有修改上游 MCP 实现；它只增加 Codex Skill 元数据、安装/配置逻辑和 Codex 使用规则。
