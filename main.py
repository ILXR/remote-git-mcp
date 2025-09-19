import os
import asyncio
from log import *
from dotenv import load_dotenv

logger = logging.getLogger("main")

# 读取 .env
load_dotenv()
# 导入 mcp 工具
from tools import mcp, GitRepoUtil


async def main():
    logger.info("=" * 100)
    logger.info("Initializing server_code repo ...")
    GitRepoUtil.init_server_code_repo()
    asyncio.create_task(GitRepoUtil.git_fetch_task(interval=300))

    logger.info("Starting server-code-mcp ...")
    transport = os.getenv("MCP_TRANSPORT")
    if transport == "stdio":
        await mcp.run_async(
            transport=transport,
        )
    else:
        await mcp.run_async(
            transport=os.getenv("MCP_TRANSPORT"),
            host=os.getenv("MCP_HOST"),
            port=int(os.getenv("MCP_PORT")),
            path=os.getenv("MCP_PATH"),
        )


if __name__ == "__main__":
    asyncio.run(main())
