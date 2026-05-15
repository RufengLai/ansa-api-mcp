# ANSA API MCP Server

基于 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) 的 ANSA Python API 智能搜索服务。让 Claude Code 能够直接搜索和理解 ANSA API 文档，辅助用户编写 ANSA 脚本。

## 项目介绍

ANSA 是业界广泛使用的 CAE 前处理软件，其 Python API 包含 **2379 个函数**，分布在 **20 个模块**中。面对如此庞大的 API 体系，开发者往往难以快速找到所需的函数。

本项目将 ANSA API 文档构建为结构化索引，并通过 MCP 协议暴露给 Claude Code，使 AI 能够：

- 理解用户的自然语言意图（中英文均可）
- 精准定位对应的 ANSA API 函数
- 返回函数签名、参数说明和代码示例

### 覆盖的模块

| 模块 | 说明 |
|------|------|
| `ansa.base` | 基础操作（查询、创建、修改、删除实体） |
| `ansa.mesh` | 网格操作（划分、质量检查、编辑） |
| `ansa.morph` | 形状变形（映射、变形控制） |
| `ansa.connections` | 连接管理（焊点、螺栓等） |
| `ansa.dm` | 数据管理 |
| `ansa.calc` | 计算工具 |
| `ansa.kinetics` | 运动学分析 |
| `ansa.batchmesh` | 批量网格处理 |
| `ansa.report` | 报告生成 |
| `ansa.cad` | CAD 导入导出 |
| 以及 10 个其他模块... | |

## 功能特性

### 三层搜索策略

```
用户查询 → Layer 1: 关键词匹配
              ↓ (结果不足)
         Layer 2: 模糊子串搜索
              ↓ (结果不足)
         Layer 3: TXT 文档全文兜底
```

1. **关键词匹配** — 基于预生成的中英文关键词索引，精确匹配最相关的函数
2. **模糊搜索** — 在函数签名和描述中进行子串匹配，补充关键词未覆盖的结果
3. **TXT 文档兜底** — 在完整的 API 文档全文中搜索，确保不遗漏

### 中英文双语支持

内置中英文关键词映射，支持用中文描述需求：

```
用户: "删除网格"  →  ansa.mesh.DeleteElements
用户: "delete mesh" →  ansa.mesh.DeleteElements
```

### 智能结果排序

- 关键词命中数越多，排名越靠前
- 返回函数签名、模块、分类、参数列表和代码示例
- 支持按 `module` 和 `category` 过滤

## 安装教程

### 前置条件

- Python 3.10+
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 已安装

### 第一步：安装 MCP Server

```bash
pip install git+https://github.com/RufengLai/ansa-api-mcp.git
```

### 第二步：注册到 Claude Code

```bash
ansa-api-mcp install
```

输出示例：

```
Successfully registered ansa-api MCP server in Claude Code!
  Config: C:\Users\XXX\.claude\settings.json
  Command: C:\...\Scripts\ansa-api-mcp.EXE

Restart Claude Code to start using it.
```

### 第三步：重启 Claude Code

重启后即可使用 `search_ansa_api` 工具搜索 ANSA API。

## 使用示例

在 Claude Code 中直接用自然语言描述需求，AI 会自动调用搜索工具：

```
你: 帮我写一个删除所有 shell 单元的脚本
AI: [调用 search_ansa_api("删除 shell")]
    → 找到 ansa.mesh.DeleteElements()
    → 生成完整脚本
```

```
你: 如何获取某个 PID 下的所有单元？
AI: [调用 search_ansa_api("get elements by pid", module="ansa.base")]
    → 找到 ansa.base.CollectEntities()
    → 生成查询代码
```

### 搜索工具参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `query` | string | 搜索关键词，支持中英文 |
| `module` | string | 按模块过滤，如 `"ansa.mesh"` |
| `category` | string | 按分类过滤，如 `"mesh_edit"` |
| `top_n` | int | 返回结果数量，默认 5 |

## 技术架构

```
ansa-api-mcp/
├── tools/
│   ├── mcp_server.py          # MCP Server (FastMCP) + 三层搜索引擎
│   ├── parse_html.py          # Sphinx HTML 文档解析器
│   ├── generate_keywords.py   # AI 关键词生成 (Anthropic SDK)
│   ├── generate_index.py      # 索引构建流水线
│   ├── ansa_api_index.json    # 预构建索引 (2379 函数)
│   └── txt_docs/              # ANSA API 全量 TXT 文档 (26 文件)
├── tests/                     # 测试套件 (26 个测试)
├── pyproject.toml             # 包配置
└── demo/                      # 示例 ANSA 脚本
```

### 索引构建

索引通过以下流水线生成：

1. **HTML 解析** — 从 ANSA Sphinx 文档中提取函数签名、参数、描述、示例
2. **分类标注** — 根据函数名和模块自动分类（mesh_edit、base_query 等）
3. **关键词生成** — 调用 AI 为每个函数生成中英文搜索关键词
4. **输出索引** — 生成 `ansa_api_index.json`，供运行时搜索使用

### MCP 协议

本项目使用 [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) 的 FastMCP 框架，通过 stdio 协议与 Claude Code 通信。Claude Code 在需要查询 ANSA API 时自动调用 `search_ansa_api` 工具。

## 高级配置

### 自定义 TXT 文档路径

如果你有更新版本的 ANSA TXT 文档，可通过环境变量覆盖内置文档：

```json
{
  "mcpServers": {
    "ansa-api": {
      "command": "ansa-api-mcp",
      "env": {
        "ANSA_TXT_DOCS_PATH": "C:/path/to/your/txt_docs"
      }
    }
  }
}
```

### 重新生成索引

如果需要为不同版本的 ANSA 重新生成索引：

```bash
# 需要 Anthropic API Key 用于关键词生成
export ANTHROPIC_API_KEY="your-key"
python -m tools.generate_index
```

## 开发

```bash
# 克隆仓库
git clone https://github.com/RufengLai/ansa-api-mcp.git
cd ansa-api-mcp

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/ -v
```

## License

MIT
