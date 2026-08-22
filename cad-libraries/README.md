# 免登录 CAD / STEP 元件库

这一目录专门解决“给 BOM 型号自动找 3D 元件，但不要求人工登录第三方 CAD 网站”的问题。

## 收集策略

- **开源库**：可以直接从 GitHub 拉取的模型，保留上游许可文件。
- **公共 API**：通过 `step.parts` 公共 API 搜索并下载 STEP。
- **厂家匿名直链**：厂家官网可以不登录直接下载的 ZIP/STP，只进入本地/Actions 缓存，不默认提交到 Git 历史。
- **登录型门户**：不作为本功能的必需来源。

## 当前集合

### FreeCAD/FreeCAD-library — Electrical Parts

只稀疏拉取 `Electrical Parts`，避免把整个大型 FreeCAD Parts Library 全部复制下来。

适合作为：通用电气元件、机箱/开关、电源、连接件等兜底模型。

### Canela-san/PanelCC — Parts

这是现成的 FreeCAD 电柜项目元件目录，包含 DIN 导轨、线槽、接触器、断路器、电源、母排等，并带有 STEP/FCStd 模型。

### FreeCAD_PartsToolbox — ObjModels

补充 FreeCAD 可复用零件模型。

### step.parts 公共 API

用于按关键词/型号建立一个可搜索的 STEP 缓存。默认 `starter` 每类只下载少量高相关模型，`expanded` 会增加数量。

### 厂家匿名直链

当前已加入：

- Inovance / 汇川：MD520 官方 3D STP 包；
- Mean Well / 明纬：NDR-240 官方 3D 包。

这类文件不会自动提交到仓库，只会出现在本地缓存或 GitHub Actions artifact 中。

## 本地一键收集

```powershell
.\scripts\collect-cad-libraries.ps1 -Mode starter -IncludeVendor yes
```

结果默认写入 `.cad-cache/`。

## GitHub Actions 收集

仓库里的 `Collect no-login CAD libraries` 工作流会在 GitHub runner 上完成同样的收集，并上传：

`cad-libraries-no-login-<run number>`

这样无需在本机逐个访问网站，也不需要上游账号。

## 许可原则

开源库跟随各自上游许可并保留 LICENSE/README。厂家匿名下载的 CAD 文件不因为“能直接下载”就自动获得再分发许可，所以它们只进入临时缓存/artifact，不回写 Git 历史；需要对外发布时再按厂家许可确认。
