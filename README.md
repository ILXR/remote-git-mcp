# Remote Git MCP

一个基于 MCP (Model Context Protocol) 的远程 Git 仓库访问工具，支持通过多种传输协议远程查询和访问 Git 仓库内容。

## 前置要求

- **Python 3.10+**: 基础运行环境
- **uv**: 现代 Python 包和项目管理器

## 功能特性

- 🔍 **文本搜索**: 使用 `git grep` 在指定分支中搜索文本模式，支持正则表达式
- 📁 **文件列表**: 使用 `git ls-tree` 查询指定分支的文件列表，支持正则表达式过滤
- 📖 **文件内容**: 使用 `git show` 获取指定分支中文件的完整内容
- 🌿 **分支查询**: 获取所有远程分支列表
- 🚀 **多协议支持**: 支持 `stdio`、`sse`、`streamable-http` 等传输协议
- 📊 **分页支持**: 所有查询结果支持分页，避免数据过载
- 🔄 **自动同步**: 支持定时从远程仓库拉取最新代码

## 安装与配置

### 1. 安装方式

#### 方式一：使用 uvx 直接运行（推荐）

从 Git 仓库直接安装并运行 stdio 模式 (需要在 mcp.json 中设置环境变量 GIT_REPO_URL 和 WORKSPACE)：

```bash
uvx --from git+https://github.com/your-repo/remote-git-mcp.git remote-git-mcp --transport stdio --quiet
```

#### 方式二：使用 uv 本地安装

克隆仓库后本地安装：

```bash
git clone https://github.com/your-repo/remote-git-mcp.git
cd remote-git-mcp
uv sync
uv pip install -e .
remote-git-mcp -h
```

### 2. 环境变量配置

创建 `.env` 文件或设置以下环境变量：

```bash
# Git 仓库 URL（可以包含认证信息）
GIT_REPO_URL=https://username:token@github.com/user/repo.git
# 本地工作目录
WORKSPACE=/path/to/local/workspace
```

## 使用方法

### 启动服务

### 命令行参数

```bash
remote-git-mcp [选项]

选项:
  --transport {stdio,sse,streamable-http}  传输协议 (默认: stdio)
  --host HOST                            服务器地址 (默认: 0.0.0.0)
  --port PORT                            服务器端口 (默认: 8999)
  --path PATH                            MCP 路径 (默认: /mcp)
  -q, --quiet                            静默模式，只记录到文件
```

## MCP 工具说明

### 1. git_grep - 文本搜索

在指定分支中搜索文本模式，返回匹配的代码块。

**参数**:

- `branch` (必填): 目标分支名称，不包含 `origin/` 前缀
- `text_pattern` (必填): 搜索模式，支持正则表达式（不能包含空格）
- `file_path_pattern` (可选): 文件路径过滤，使用 shell 通配符，默认 `*`
- `num_range` (可选): 结果范围 `[start, end]`，默认 `[0, 100]`

**示例**:

```json
{
  "branch": "main",
  "text_pattern": "AvatarType",
  "file_path_pattern": "*.cpp",
  "num_range": [0, 50]
}
```

### 2. git_ls_tree - 文件列表

查询指定分支的文件列表，支持正则表达式过滤。

**参数**:

- `branch` (必填): 目标分支名称，不包含 `origin/` 前缀
- `pattern` (必填): 文件路径的 Python 正则表达式
- `num_range` (可选): 结果范围 `[start, end]`，默认 `[0, 100]`

**示例**:

```json
{
  "branch": "main",
  "pattern": ".*.proto",
  "num_range": [0, 100]
}
```

### 3. git_show - 文件内容

获取指定分支中某个文件的内容。

**参数**:

- `branch` (必填): 目标分支名称，不包含 `origin/` 前缀
- `file_path` (必填): 文件路径
- `line_range` (可选): 行号范围 `[start, end]`，默认 `[0, 500]`

**示例**:

```json
{
  "branch": "main",
  "file_path": "src/main.cpp",
  "line_range": [0, 100]
}
```

### 4. git_remote_branches - 分支列表

获取所有远程分支列表。

**示例**:

```json
{}
```

## 返回格式

### 成功响应

所有工具都返回结构化的 JSON 数据：

```json
{
  "total": 100,
  "num_range": [0, 50],
  "results": [...] // 或 "files": [...] 或 "branches": [...]
}
```

### 错误响应

```json
{
  "message": "错误描述信息"
}
```

## 项目结构

```text
remote-git-mcp/
├── remote_git_mcp/
│   ├── __init__.py          # 包初始化
│   ├── main.py              # 主程序入口
│   ├── tools.py             # MCP 工具实现
│   └── log.py               # 日志配置
├── pyproject.toml           # 项目配置
├── uv.lock                  # 依赖锁定文件
└── README.md                # 项目说明文档
```

## 特性说明

- **分页查询**: 所有查询结果支持 `num_range` 参数进行分页，格式为 `[起始索引, 结束索引]`，左闭右开区间
- **结果截断**: 超长输出会自动截断，并显示截断信息
- **错误处理**: 完善的错误处理机制，返回结构化的错误信息
- **日志系统**: 支持文件日志和控制台日志，日志文件按天轮转
- **自动同步**: 后台定时任务每 5 分钟从远程仓库拉取最新代码
