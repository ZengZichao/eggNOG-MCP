# eggNOG-MCP

[![版本](https://img.shields.io/badge/版本-0.1.0-blue.svg)](https://eggnogdb.org/)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue.svg)](https://www.python.org/)
[![许可证: MIT](https://img.shields.io/badge/许可证-MIT-green.svg)](./LICENSE)
[![数据库: eggNOG 7](https://img.shields.io/badge/数据库-eggNOG%207-orange.svg)](https://eggnogdb.org/)

> **中文** | **[English](./README.md)**

> ⚠️ **免责声明：** 这是一个由社区维护的**非官方** MCP 服务器，用于访问 eggNOG 数据库。本项目与 eggNOG 团队或 EMBL 无关，也未获得其认可或维护。eggNOG 官方数据库请访问 [https://eggnogdb.org/](https://eggnogdb.org/)。

一个 [模型上下文协议（MCP）](https://modelcontextprotocol.io/) 服务器，为 AI 助手提供访问 [eggNOG 7 数据库](https://eggnogdb.org/) 的能力——eggNOG 是一个用于比较基因组学的直系同源关系和功能预测的综合数据库。

---

## 目录

- [项目概述](#项目概述)
- [功能特性](#功能特性)
- [快速开始](#快速开始)
- [安装方式](#安装方式)
- [配置方法](#配置方法)
- [可用工具](#可用工具)
- [可用资源](#可用资源)
- [使用示例](#使用示例)
- [项目结构](#项目结构)
- [开发指南](#开发指南)
- [许可证](#许可证)
- [致谢](#致谢)

---

## 项目概述

[eggNOG](https://eggnogdb.org/)（evolutionary genealogy of genes: Non-supervised Orthologous Groups，基因进化谱系：非监督直系同源群）是一个包含直系同源关系、功能注释和系统发育树的数据库，覆盖 **12,000+ 已注释物种**、**5,900万+ 蛋白质序列**和 **310万+ 直系同源群**。

**eggNOG-MCP** 将 eggNOG 数据库与大语言模型（LLM）连接起来，实现了模型上下文协议。配置完成后，任何兼容 MCP 的 AI 助手（如 Claude Desktop、Cursor 或自定义 Agent）都可以通过自然语言直接查询 eggNOG 数据库。

服务器通过 eggNOG 原生 JSON API（`/e7api/`）进行通信，确保数据访问的可靠性和结构化——无需 HTML 解析。

### 使用 eggNOG-MCP 可以做什么？

- 🔬 通过 eggNOG 蛋白质 ID 查询蛋白质，获取其功能注释
- 🧬 查询直系同源群（OG），了解进化关系
- 📋 列出 OG 中的所有蛋白质，按物种分组
- 🔗 获取蛋白质在所有物种中的 pairwise 直系同源
- 🔍 按蛋白质名称、UniProt ID 或家族名称搜索 eggNOG 数据库
- 📊 获取数据库统计信息（物种数、蛋白质数、树数、OG 数）
- 📥 列出所有可下载的批量数据文件
- 🏷️ 获取蛋白质的 KEGG KO 术语和 GO 术语注释（含置信度分数）
- 🧫 浏览蛋白质家族的所有成员

---

## 功能特性

| 功能 | 描述 |
|------|------|
| **蛋白质查询** | 通过 eggNOG 蛋白质 ID 获取蛋白质家族、预测功能和直系同源群信息 |
| **直系同源群查询** | 查询 OG 详情，包括进化来源、成员数量和功能注释 |
| **OG 内容** | 列出 OG 中的所有蛋白质，按物种分组 |
| **直系同源** | 获取蛋白质在所有物种中的 pairwise 直系同源 |
| **蛋白质家族** | 浏览蛋白质家族簇中的所有物种和蛋白质 |
| **数据库搜索** | 按蛋白质名称、UniProt ID 或家族名称搜索 |
| **功能注释** | 获取结构化的 KEGG KO 和 GO 术语注释，含置信度分数 |
| **数据库统计** | 访问当前 eggNOG 7 版本的统计数据 |
| **下载文件索引** | 列出所有可批量下载的数据文件及其 URL 和描述 |
| **分类单元查询** | 通过 NCBI 分类 ID 查询分类信息 |
| **MCP 资源** | 将版本信息、统计信息和下载列表作为 MCP 资源暴露 |
| **JSON API** | 使用 eggNOG 原生 `/e7api/` JSON 端点，确保数据访问可靠性 |
| **异步 HTTP** | 基于 `httpx` 实现高效的异步 HTTP 请求 |
| **容错设计** | 所有工具返回结构化的错误信息，不会因网络问题崩溃 |

---

## 快速开始

```bash
# 安装
pip install eggnog-mcp

# 运行（使用 stdio 传输——适用于 MCP 客户端）
eggnog-mcp
```

或直接使用 Python 运行：

```bash
python -m eggnog_mcp.server
```

---

## 安装方式

### 方式一：从源码安装（推荐用于开发）

```bash
git clone https://github.com/ZengZichao/eggNOG-MCP.git
cd eggNOG-MCP
pip install -e .
```

### 方式二：仅安装依赖

```bash
pip install -r requirements.txt
```

### 环境要求

- Python ≥ 3.10
- `mcp` ≥ 2.0.0（模型上下文协议 SDK）
- `httpx` ≥ 0.27.0（异步 HTTP 客户端）

---

## 配置方法

### Claude Desktop

将以下内容添加到你的 `claude_desktop_config.json` 文件中：

```json
{
  "mcpServers": {
    "eggnog-mcp": {
      "command": "eggnog-mcp",
      "args": []
    }
  }
}
```

如果从源码安装且未添加到 PATH，请使用完整路径：

```json
{
  "mcpServers": {
    "eggnog-mcp": {
      "command": "python",
      "args": ["-m", "eggnog_mcp.server"],
      "env": {
        "PYTHONPATH": "/path/to/eggNOG-MCP/src"
      }
    }
  }
}
```

### Cursor IDE

添加到 Cursor MCP 设置中：

```json
{
  "mcpServers": {
    "eggnog-mcp": {
      "command": "eggnog-mcp"
    }
  }
}
```

### 通用 MCP 客户端

服务器默认使用 **stdio 传输**。启动方式：

```bash
eggnog-mcp
```

服务器通过 stdin/stdout 使用 MCP 协议进行通信。

### TLS / 网络问题

如果在连接 `https://eggnogdb.org` 时遇到 TLS 错误，可以修改 `src/eggnog_mcp/client.py` 中的客户端初始化配置，使用 HTTP 或禁用 SSL 验证：

```python
# 方式一：使用 HTTP
_global_client = eggNOGClient(base_url="http://eggnogdb.org")

# 方式二：禁用 SSL 验证（HTTPS）
_global_client = eggNOGClient(verify_ssl=False)
```

---

## 可用工具

### 1. `get_protein`（查询蛋白质）

查询 eggNOG 数据库中蛋白质的详细信息。

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `protein_id` | `str` | 是 | eggNOG 蛋白质 ID，格式为 `taxid.seqid` |

**示例：**
```
protein_id = "9606.ENSP00000269305"
```

**返回内容：** 蛋白质名称、物种、分类 ID、UniProt ID、Pfam 结构域、KEGG KO 术语、直系同源群列表、预测功能（KEGG KO + GO 术语及置信度）、所选 OG 详情。

---

### 2. `get_orthologous_group`（查询直系同源群）

查询直系同源群（OG）的信息。

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `og_id` | `str` | 是 | OG ID，格式为 `family@taxid\|level` |

**示例：**
```
og_id = "P53@33154|A-1"
```

**返回内容：** OG ID、蛋白质家族、进化来源、分类谱系、蛋白质数量、物种数量、功能注释（KEGG KO + GO slim）、同家族所有 OG 列表。

---

### 3. `get_og_content`（获取 OG 内容）

获取直系同源群中的蛋白质列表。

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `og_id` | `str` | 是 | OG ID，格式为 `family@taxid\|level` |
| `max_species` | `int` | 否 | 最大返回物种数（默认：50） |

**示例：**
```
og_id = "P53@33154|A-1", max_species = 10
```

**返回内容：** 物种总数、蛋白质总数、按物种分组的蛋白质 ID 列表。

---

### 4. `get_orthologs`（获取直系同源）

获取蛋白质的 pairwise 直系同源。

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `protein_id` | `str` | 是 | eggNOG 蛋白质 ID，格式为 `taxid.seqid` |
| `max_species` | `int` | 否 | 最大返回物种数（默认：50） |

**示例：**
```
protein_id = "9606.ENSP00000269305", max_species = 10
```

**返回内容：** 直系同源物种总数、按物种分组的直系同源蛋白质 ID。

---

### 5. `search_eggnog`（搜索数据库）

搜索 eggNOG 数据库中的蛋白质或直系同源群。

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `query` | `str` | 是 | 搜索查询（≥ 3 个字符） |

**示例：**
```
query = "P53"
query = "P04637"
query = "TP53"
```

**返回内容：** 匹配的蛋白质和 OG 列表，包含类型、ID、标签和 URL。

---

### 6. `annotate_protein`（蛋白质功能注释）

获取蛋白质的功能注释信息（KEGG KO + GO 术语）。

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `protein_id` | `str` | 是 | eggNOG 蛋白质 ID，格式为 `taxid.seqid` |

**示例：**
```
protein_id = "9606.ENSP00000269305"
```

**返回内容：** 结构化注释，包含 KEGG KO 术语、GO slim 术语、KEGG 基因符号、蛋白质家族、Pfam 结构域、直系同源群和所选 OG 详情。

---

### 7. `get_protein_family`（获取蛋白质家族）

获取蛋白质家族（簇）的内容。

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `family_name` | `str` | 是 | 蛋白质家族 / 簇名称 |
| `max_species` | `int` | 否 | 最大返回物种数（默认：50） |

**示例：**
```
family_name = "P53", max_species = 10
```

**返回内容：** 物种总数、蛋白质总数、按物种分组的蛋白质 ID、物种摘要。

---

### 8. `get_database_stats`（获取数据库统计）

获取 eggNOG 7 数据库的摘要统计信息。

**参数：** 无

**返回内容：** 已注释物种数、蛋白质序列数、系统发育树数、直系同源群数。

---

### 9. `list_downloads`（列出下载文件）

列出所有可批量下载的数据文件。

**参数：** 无

**返回内容：** 文件列表，包含文件名、URL 和描述（蛋白质序列、OG 信息、系统发育树、分类信息等）。

---

### 10. `get_taxid_info`（查询分类信息）

通过 NCBI 分类 ID 查询分类信息。

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `taxid` | `int` | 是 | NCBI 分类 ID |

**示例：**
```
taxid = 9606（智人）
```

**返回内容：** 分类查询指引、分类信息 TSV 文件下载 URL 和列格式描述。

---

## 可用资源

| 资源 URI | 描述 |
|----------|------|
| `eggnog://version` | 服务器版本和数据库信息 |
| `eggnog://database/stats` | 缓存的数据库统计信息 |
| `eggnog://database/downloads` | 可下载文件列表 |

---

## 使用示例

### 示例 1：注释人类 P53 蛋白

```
用户：    "在 eggNOG 中查询人类 P53 的功能注释"
助手：    [调用 annotate_protein，protein_id="9606.ENSP00000269305"]
```

**返回结果包含：**
- 蛋白质家族：`P53`
- KEGG KO 术语：`K04451`（TP53，11.47%）、`K10148`（TP73，14.34%）、`K10149`（TP63，19.80%）
- GO 术语：`GO:0006355`（转录调控，68.83%）、`GO:0006351`（转录，68.83%）
- Pfam 结构域：`P53_TAD`、`TAD2`、`P53`、`P53_tetramer`
- 35 个直系同源群，覆盖 438 个物种

### 示例 2：搜索 P53

```
用户：    "在 eggNOG 中搜索 P53"
助手：    [调用 search_eggnog，query="P53"]
```

**返回结果：** 10 个匹配项，包括蛋白质（如 `PPP5_HUMAN`）和 OG（如 `P53@33154|A-1`）。

### 示例 3：查询直系同源群

```
用户：    "告诉我关于后生动物级别的 P53 直系同源群的信息"
助手：    [调用 get_orthologous_group，og_id="P53@33154|A-1"]
```

**返回结果：** 进化来源（Opisthokonta）、1,081 个蛋白质、438 个物种、KEGG KO 和 GO 注释、完整家族 OG 列表。

### 示例 4：列出 OG 中的蛋白质

```
用户：    "显示后生动物级别 P53 OG 中的蛋白质"
助手：    [调用 get_og_content，og_id="P53@33154|A-1"，max_species=5]
```

### 示例 5：获取直系同源

```
用户：    "人类 P53 的直系同源有哪些？"
助手：    [调用 get_orthologs，protein_id="9606.ENSP00000269305"]
```

### 示例 6：数据库统计

```
用户：    "eggNOG 数据库中有多少个物种？"
助手：    [调用 get_database_stats]
```

**返回结果：** 12k+ 已注释物种、59M+ 蛋白质序列、1.1M+ 系统发育树、3.1M+ 直系同源群。

---

## 项目结构

```
eggNOG-MCP/
├── pyproject.toml              # 项目配置和依赖
├── requirements.txt            # pip 依赖
├── LICENSE                     # MIT 许可证
├── .gitignore                  # Git 忽略规则
├── README.md                   # 英文文档
├── README_zh.md                # 中文文档（本文件）
├── src/
│   └── eggnog_mcp/
│       ├── __init__.py         # 包初始化
│       ├── version.py          # 版本信息
│       ├── client.py           # eggNOG API 客户端（异步 HTTP，JSON API）
│       └── server.py           # MCP 服务器和工具定义（10 个工具）
└── tests/
    └── test_client.py          # API 客户端单元测试
```

---

## 开发指南

### 环境搭建

```bash
# 克隆并以开发模式安装
git clone https://github.com/ZengZichao/eggNOG-MCP.git
cd eggNOG-MCP
pip install -e ".[dev]"
```

### 代码检查

```bash
ruff check src/
ruff format src/
```

### 运行测试

```bash
# 运行完整测试套件
pytest tests/ -v
```

### 测试服务器

```bash
# 运行服务器并验证启动
eggnog-mcp

# 或使用 MCP 检查器测试
npx @modelcontextprotocol/inspector eggnog-mcp
```

### 使用的 API 端点

客户端与 eggNOG 原生 JSON API 通信：

| 端点 | 描述 |
|------|------|
| `/e7api/protein/{id}/` | 蛋白质详情 + OG + 功能 |
| `/e7api/og/{id}/` | 直系同源群详情 |
| `/e7api/og_content/{id}/` | OG 中的蛋白质 |
| `/e7api/clu_content/{name}/` | 蛋白质家族簇中的蛋白质 |
| `/e7api/orthologs/{id}/` | 蛋白质的 pairwise 直系同源 |
| `/e7api/suggest_entries/{query}/` | 搜索 / 自动补全 |
| `/stats/` | 数据库统计（HTML） |

---

## 许可证

本项目基于 [MIT 许可证](./LICENSE) 开源。

eggNOG 数据库本身由 EMBL 的 eggNOG 团队维护。请访问 [https://eggnogdb.org/](https://eggnogdb.org/) 了解数据库使用条款和引用要求。

> **注意：** 这是一个非官方的社区维护项目，与 eggNOG 团队或 EMBL 无关，也未获得其认可。

---

## 致谢

- **eggNOG 团队** — 创建和维护 eggNOG 数据库。请访问 [https://eggnogdb.org/](https://eggnogdb.org/) 获取更多信息。
- **Anthropic** — 提供模型上下文协议规范和 SDK。
- **Huerta-Cepas J, 等** — *eggNOG 7.0：12,000+ 基因组规模的比较基因组学。* 在研究中使用本工具时，请引用原始 eggNOG 论文。

### 主要参考文献

- Huerta-Cepas, J., 等 (2023). eggNOG 7.0: comparative genomics at the scale of 12,000+ genomes. *Briefings in Bioinformatics*, 24(1), bbac483.
- 模型上下文协议规范：[https://modelcontextprotocol.io/](https://modelcontextprotocol.io/)

---

<div align="center">
  <sub>为生物信息学和 AI 社区而构建。</sub>
</div>
