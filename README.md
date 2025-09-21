# Remote Git MCP

一个基于 MCP (Model Context Protocol) 的远程 Git 仓库访问工具，支持通过多种传输协议，检索任意远程分支的文件和内容。

## 前置要求

- **Python 3.10+**: 基础运行环境
- **uv**: 现代 Python 包和项目管理器

## 功能特性

- 🔍 **文本搜索**: 使用 `git grep` 在指定分支中搜索文本模式，支持正则表达式，对传统程序语言支持较好（返回整个函数/类定义的代码块）
- 📁 **文件列表**: 使用 `git ls-tree` 查询指定分支的文件列表，支持正则表达式过滤
- 📖 **文件内容**: 使用 `git show` 获取指定分支中文件的完整内容
- 🌿 **分支查询**: 获取所有远程分支列表
- 🚀 **多协议支持**: 支持 `stdio`、`sse`、`streamable-http` 等传输协议
- 📊 **分页支持**: 所有查询结果支持分页，避免数据过载
- 🔄 **自动同步**: 支持定时从远程仓库拉取最新代码

## 下载与运行

### 使用 uvx 直接运行

从 Git 仓库直接安装并运行 stdio 模式 (需要先设置环境变量 `GIT_REPO_URL` 和 `WORKSPACE`, 具体含义参考 `.env.example`)

```bash
uvx git+https://github.com/ILXR/remote-git-mcp.git --transport stdio
```

当使用 Agent 客户端时，可以这样配置 `mcp.json`：

```json
{
  "mcpServers": {
    "remote-git-mcp": {
      "command": "uvx git+https://github.com/ILXR/remote-git-mcp.git --transport stdio",
      "env": {
        "GIT_REPO_URL": "Git仓库URL(包含认证信息)",
        "WORKSPACE": "本地仓库绝对路径(已存在时 GIT_REPO_URL 可以填空字符串)"
      }
    }
  }
}
```

### 使用 uv 本地安装 (开发环境推荐)

克隆仓库后同步虚拟环境并配置 `.env` 文件


```bash
git clone https://github.com/ILXR/remote-git-mcp.git
cd remote-git-mcp
uv sync
# 复制后自行配置 .env 文件
cp .env.example .env
```

可以安装到当前目录的虚拟环境中 (使用 `uv` 管理, 不会污染全局环境):

```bash
./install_local.sh
uv run remote-git-mcp -h
```

如果不安装的话，也可以直接运行脚本

```bash
uv run python remote_git_mcp/main.py -h
```

在本地运行一般直接传入 streamable-http 模式:

```bash
uv run python remote_git_mcp/main.py --transport streamable-http
```

然后在 `mcp.json` 中配置:

```json
{
  "mcpServers": {
    "remote-git-mcp": {
      "url": "http://127.0.0.1:8999/mcp"
    }
  }
}
```

## MCP 工具说明

### 1. git_grep - 文本搜索

在指定分支中搜索文本模式，返回匹配的代码块。

**参数**:

- `branch` (必填): 目标分支
- `text_pattern` (必填): 搜索文本正则
- `file_path_pattern` (可选): 文件路径过滤通配符
- `num_range` (可选): 结果范围

**示例**:

```json
{
  "branch": "main",
  "text_pattern": "keywords",
  "file_path_pattern": "*.cpp",
  "num_range": [0, 50]
}
```

### 2. git_ls_tree - 文件列表

查询指定分支的文件列表，支持正则表达式过滤。

**参数**:

- `branch` (必填): 目标分支
- `pattern` (必填): 文件路径的 Python 正则表达式
- `num_range` (可选): 结果范围

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

- `branch` (必填): 目标分支
- `file_path` (必填): 文件路径
- `line_range` (可选): 行号范围

**示例**:

```json
{
  "branch": "main",
  "file_path": "path/to/file.cpp",
  "line_range": [0, 100]
}
```

### 4. git_remote_branches - 分支列表

获取所有远程分支列表, 无参数

## 项目结构

```shell
remote-git-mcp/
├── remote_git_mcp/
│   ├── __init__.py          # 包初始化
│   ├── main.py              # 主程序入口
│   ├── tools.py             # MCP 工具实现
│   └── log.py               # 日志配置
├── install_local.sh         # 本地安装脚本
├── pyproject.toml           # 项目配置
├── uv.lock                  # 依赖锁定文件
└── README.md                # 项目说明文档
```
