import re
import os
import git
import logging
import asyncio
from pydantic import Field
from fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Git Repo
repo: git.Repo = None
# FastMCP instance
mcp: FastMCP = FastMCP("remote-git-mcp")

# parameter description
branch_param_description = "目标分支名称, 不包含 origin/ 前缀, **必填**"
range_param_description = (
    "{}, list[int] 格式, 默认 {}(推荐使用默认值), 左闭右开区间, 下标从0开始"
)


class ResultParseUtil:
    @staticmethod
    def truncate_output(text: str, max_length: int = 50000) -> str:
        """
        当输出文本超过指定长度时, 会在合适的位置(换行符处)截断, 并添加截断信息说明

        Args:
            text: 需要处理的文本
            max_length: 最大允许长度

        Returns:
            处理后的文本, 如果原文本超长则包含截断信息说明
        """
        if len(text) <= max_length:
            return text

        # Calculate how much space we need for the truncation message
        truncation_msg_length = 200
        available_length = max_length - truncation_msg_length

        # Try to find a good breaking point (end of a line) near the limit
        truncated = text[:available_length]
        last_newline = truncated.rfind("\n", available_length - 500, available_length)

        if last_newline > 0:
            truncated = text[:last_newline]

        # Add truncation message
        truncation_msg = f"""
{'=' * 60}
[OUTPUT TRUNCATED]
Original length: {len(text):,} characters
Showing length: {len(truncated):,} characters
Truncated: {len(text) - len(truncated):,} characters
{'=' * 60}"""

        return truncated + truncation_msg

    @staticmethod
    def check_num_range(num_range: list[int]) -> bool:
        if (
            not num_range
            or not isinstance(num_range, list)
            or len(num_range) != 2
            or num_range[0] < 0
            or num_range[0] > num_range[1]
        ):
            return False
        return True

    @staticmethod
    def parse_result_range(total_num: int, num_range: list[int]) -> list[int]:
        """
        解析目标范围
        传入的范围为目标切片区间
        返回的范围为实际返回区间
        """
        if not ResultParseUtil.check_num_range(num_range) or num_range[0] >= total_num:
            return [0, 0]
        num_range[1] = min(total_num, num_range[1])
        return num_range

    @staticmethod
    def parse_git_grep_result(
        grep_output: str, num_range: list[int], file_chunk_limit: int = 0
    ) -> dict:
        """
        解析'git grep -W -n --heading'命令的输出, 将其转换为结构化的数据
        支持按文件限制匹配数量, 支持按字符长度分割代码块

        Args:
            grep_output: git grep 命令的原始输出
            num_range: 结果范围, 格式为 [start, end], 左闭右开区间, 下标从0开始
            file_chunk_limit: 每个文件的最大匹配数量限制, 0表示无限制

        Returns:
            包含搜索结果的字典, 格式如下:
            {
                "total": 总结果数量,
                "num_range": [实际返回的范围]
                "results": [
                    {
                        "file_path": "文件路径",
                        "line_range": [起始行号, 结束行号],
                        "content": "文件内容"
                    },
                    ...
                ]
            }
        """
        if not grep_output.strip():
            return {"total": 0, "results": []}

        # git grep --heading使用"--"作为代码段之间的分隔符
        blocks = grep_output.split("--\n")
        results = []
        current_file_path = None
        current_file_match_count = 0  # 当前文件的匹配计数

        # 遍历每个代码块进行处理
        for block in blocks:
            if not block.strip():
                continue

            lines = block.strip().split("\n")
            if not lines:
                continue

            # 匹配文件路径行, 格式: origin/branch:file_path
            first_line = lines[0]
            file_path_match = re.match(r"^origin/[^:]+:(.+)$", first_line)

            if file_path_match:
                # 新文件开始,重置计数器
                current_file_path = file_path_match.group(1)
                current_file_match_count = 0
                start_line_idx = 1  # 跳过文件路径行
            else:
                # 继续处理同一文件的后续匹配块
                if current_file_path is None:
                    logger.warning(f"No file path found for block: {first_line}")
                    continue
                current_file_match_count += 1
                start_line_idx = 0  # 从第一行开始处理

            # 如果超过单文件匹配数量限制,跳过此块
            if file_chunk_limit > 0 and current_file_match_count >= file_chunk_limit:
                continue

            code_lines = []
            line_numbers = []
            code_content_length = 0

            def try_add_code(max_length: int = 0):
                """尝试添加当前收集的代码行到结果中。

                Args:
                    max_length: 最大字符长度限制, 0表示无限制 强制添加
                """
                nonlocal code_lines, line_numbers, code_content_length
                # 只有在有内容且满足长度条件时才添加代码块
                # max_length=0 时强制添加, 否则需要达到长度阈值
                if (
                    code_lines
                    and line_numbers
                    and (max_length == 0 or code_content_length >= max_length)
                ):
                    min_line, max_line = min(line_numbers), max(line_numbers)
                    code_content = "\n".join(code_lines)
                    results.append(
                        {
                            "file_path": current_file_path,
                            "line_range": [min_line, max_line],
                            "content": code_content,
                        }
                    )
                    # 清空缓存,准备处理下一个代码块
                    code_lines.clear()
                    line_numbers.clear()
                    code_content_length = 0

            for line in lines[start_line_idx:]:
                # 匹配不同格式的代码行
                # 格式1: line_number:content (匹配行)
                # 格式2: line_number-content (上下文行)
                # 格式3: line_number=content (函数开始行)
                line_match = re.match(r"^(\d+)[-:=](.*)$", line)
                if line_match:
                    line_num = int(line_match.group(1))
                    content = line_match.group(2)
                    line_numbers.append(line_num)
                    code_lines.append(content)
                    code_content_length += len(content)
                # 当代码块超过20k字符时进行分割
                try_add_code(max_length=20000)

            # 处理剩余的代码行
            try_add_code(max_length=0)

        # 计算分页边界
        total_count = len(results)
        result_range = ResultParseUtil.parse_result_range(total_count, num_range)
        return {
            "total": total_count,
            "num_range": result_range,
            "results": results[result_range[0] : result_range[1]],
        }


class GitRepoUtil:
    @staticmethod
    def init_server_code_repo():
        """
        如果本地仓库不存在则从远程克隆, 如果已存在则拉取最新代码, 需要设置以下环境变量:
        - GIT_REPO_URL: Git仓库URL (包含认证信息)
        - WORKSPACE: 本地仓库路径

        Returns:
            git.Repo: 初始化后的Git仓库实例
        """
        global repo

        # 检查并获取必要的环境变量
        git_repo_url = os.getenv("GIT_REPO_URL")
        workspace = os.getenv("WORKSPACE")

        if not all([git_repo_url, workspace]):
            raise ValueError(
                "Missing required environment variables: GIT_REPO_URL, WORKSPACE"
            )

        # 构建包含认证信息的完整仓库URL
        repo_url = f"{git_repo_url}"
        # 检查本地仓库是否已存在
        if os.path.exists(workspace):
            logger.info(f"Git repo already exists at {workspace}")
            repo = git.Repo(workspace)
            repo.git.fetch("--all")
            return repo

        # 本地仓库不存在, 从远程克隆
        logger.info(f"Cloning git repo to {workspace}")
        repo = git.Repo.clone_from(repo_url, workspace)
        return repo

    @staticmethod
    async def git_fetch_task(interval: int = 300):
        """定时拉取git仓库的后台任务"""
        global repo
        while True:
            await asyncio.sleep(interval)
            if repo:
                repo.git.fetch("--all")


@mcp.tool()
async def git_grep(
    branch: str = Field(..., description=branch_param_description),
    text_pattern: str = Field(
        ...,
        description="要搜索的文本, 支持正则表达式(不能带有空格), 例如: 'AvatarType' 或 'proto::AvatarType.*'",
    ),
    file_path_pattern: str = Field(
        default="*",
        description="文件路径过滤, 使用shell正则, 例如: '*gameserver*.cpp' 或 '*.proto', 默认 * 表示所有文件",
    ),
    num_range: list[int] = Field(
        default=[0, 100],
        description=range_param_description.format("结果数量范围", "[0, 100]"),
    ),
) -> dict:
    """
    使用 `git grep` 命令在指定分支中搜索文本模式, 支持文本正则表达式和文件路径正则表达式

    返回匹配的代码块, 包含文件路径、行号范围和代码内容

    Returns:

        成功时返回:
        {
            "total": 总匹配数量,
            "num_range": [实际返回数量范围],
            "results": [
                {
                    "file_path": "文件路径",
                    "line_range": [起始行号, 结束行号],
                    "content": "完整代码块内容"
                },
                ...
            ]
        }

        失败时返回:
        {
            "message": "错误信息"
        }
    """
    global repo
    try:
        target_remote_branch = f"origin/{branch}"
        remote_branches = [ref.name for ref in repo.remote().refs]

        if target_remote_branch not in remote_branches:
            return {
                "message": f"Branch '{target_remote_branch}' not found in remote repository"
            }
        if not ResultParseUtil.check_num_range(num_range):
            return {"message": "Invalid num_range"}

        # 执行 git grep 搜索, 使用以下参数:
        # -W: 显示整个函数/代码块上下文
        # -H: 显示文件名
        # -n: 显示行号
        # -i: 忽略大小写
        # -I: 忽略二进制文件
        # -E: 启用扩展正则表达式语法
        # -C 3: 显示3行上下文 (防止某些临近的单行匹配的代码被截断)
        # --heading: 将文件名作为标题显示 (只显示一次)
        result = repo.git.grep(
            "-W",
            "-H",
            "-n",
            "-i",
            "-I",
            "-E",
            "-C",
            "3",
            "--heading",
            f"{text_pattern}",
            target_remote_branch,
            "--",
            f"{file_path_pattern}",
        )

        parsed_result = ResultParseUtil.parse_git_grep_result(result, num_range)
        if not parsed_result["results"]:
            return {
                "message": f"No matches found for pattern '{text_pattern}' in branch '{branch}'"
            }

        return parsed_result

    except Exception as e:
        error_msg = f"Error when git grep: {str(e)}"
        logger.error(error_msg)
        return {"message": error_msg}


@mcp.tool()
async def git_ls_tree(
    branch: str = Field(..., description=branch_param_description),
    pattern: str = Field(
        ...,
        description="文件路径的正则表达式, 使用python正则表达式, 例如: '.*.proto' 或 'dir_name/.*.cpp', 必填",
    ),
    num_range: list[int] = Field(
        default=[0, 100],
        description=range_param_description.format("结果数量范围", "[0, 100]"),
    ),
) -> dict:
    """
    使用 `git ls-tree` 命令查询指定分支的文件列表, 然后使用Python正则表达式进行过滤

    Returns:

        成功时返回:
        {
            "total": 匹配文件总数,
            "num_range": [实际返回范围],
            "files": [
                "path/to/file.proto",
                "path/to/file.cpp",
                ...
            ]
        }

        失败时返回:
        {
            "message": "错误信息"
        }
    """
    global repo
    try:
        target_remote_branch = f"origin/{branch}"
        remote_branches = [ref.name for ref in repo.remote().refs]

        if target_remote_branch not in remote_branches:
            return {
                "message": f"Branch '{target_remote_branch}' not found in remote repository",
            }
        if not ResultParseUtil.check_num_range(num_range):
            return {"message": "Invalid num_range"}

        # 获取指定分支的所有文件列表
        # -r: 递归列出所有文件
        # --name-only: 只显示文件名,不显示其他信息
        result = repo.git.ls_tree("-r", "--name-only", target_remote_branch)

        import re

        # 解析文件列表并使用正则表达式过滤
        file_list = result.split("\n") if result else []
        filtered_files = []

        for file_path in file_list:
            if file_path.strip() and re.search(pattern, file_path):
                filtered_files.append(file_path)
        if not filtered_files:
            return {
                "message": f"No files found for pattern '{pattern}' in branch '{branch}'",
            }

        # 计算分页
        total_count = len(filtered_files)
        result_count_range = ResultParseUtil.parse_result_range(total_count, num_range)
        return {
            "total": total_count,
            "num_range": result_count_range,
            "files": filtered_files[result_count_range[0] : result_count_range[1]],
        }
    except Exception as e:
        error_msg = f"Error when git ls-tree: {str(e)}"
        logger.error(error_msg)
        return {"message": error_msg}


@mcp.tool()
async def git_show(
    branch: str = Field(..., description=branch_param_description),
    file_path: str = Field(
        ...,
        description="要查看的文件路径, 例如: 'path/to/file.cpp', 必填",
    ),
    line_range: list[int] = Field(
        default=[0, 500],
        description=range_param_description.format("行号范围", "[0, 500]"),
    ),
) -> dict:
    """
    使用 `git show` 命令获取指定分支中某个文件的完整内容

    Returns:

        成功时返回:
        {
            "file_path": "文件路径",
            "total_lines": "总行数",
            "line_range": [实际返回范围],
            "content": "完整文件内容"
        }

        失败时返回:
        {
            "message": "错误信息"
        }
    """
    global repo
    try:
        target_remote_branch = f"origin/{branch}"
        remote_branches = [ref.name for ref in repo.remote().refs]

        if target_remote_branch not in remote_branches:
            return {
                "message": f"Branch '{target_remote_branch}' not found in remote repository",
            }
        if not ResultParseUtil.check_num_range(line_range):
            return {"message": "Invalid line_range"}

        # 使用git show命令获取文件内容
        # 格式: git show branch:file_path
        result = repo.git.show(f"{target_remote_branch}:{file_path}")
        lines = result.split("\n")
        if not lines:
            return {
                "message": f"No lines found for file '{file_path}' in branch '{branch}'",
            }

        # 计算分页
        total_lines = len(lines)
        result_line_range = ResultParseUtil.parse_result_range(total_lines, line_range)
        return {
            "file_path": file_path,
            "total_lines": total_lines,
            "line_range": result_line_range,
            "content": "\n".join(lines[result_line_range[0] : result_line_range[1]]),
        }
    except Exception as e:
        error_msg = f"Error when git show: {str(e)}"
        logger.error(error_msg)
        return {"message": error_msg}


@mcp.tool()
async def git_remote_branches():
    """
    使用 `git remote show` 命令获取所有远程分支

    Returns:

        成功时返回:
        {
            "total": 远程分支总数,
            "branches": [远程分支名称]
        }

        失败时返回:
        {
            "message": "错误信息"
        }
    """
    global repo
    try:
        remote_branches = [ref.name for ref in repo.remote().refs]
        # 过滤 origin/HEAD 分支
        remote_branches = [
            branch for branch in remote_branches if "origin/HEAD" not in branch
        ]
        # 清除 origin/ 前缀
        remote_branches = [branch.replace("origin/", "") for branch in remote_branches]
        return {"total": len(remote_branches), "branches": remote_branches}
    except Exception as e:
        error_msg = f"Error when git remote branches: {str(e)}"
        logger.error(error_msg)
        return {"message": error_msg}
