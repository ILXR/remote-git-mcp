import argparse
import asyncio
import logging

from dotenv import load_dotenv

from remote_git_mcp.log import init_log
from remote_git_mcp.tools import GitRepoUtil, mcp

logger = logging.getLogger(__name__)

# load .env
load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Remote Git MCP",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        type=str,
        default="stdio",
        help="Transport Protocol",
    )
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Host (sse/streamable-http only)"
    )
    parser.add_argument(
        "--port", type=int, default=8999, help="Port (sse/streamable-http only)"
    )
    parser.add_argument(
        "--path", type=str, default="/mcp", help="Mcp Path (sse/streamable-http only)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Debug Mode (decide log level, default is INFO)",
    )
    return parser.parse_args()


async def main():
    try:
        args = parse_args()
        is_stdio = args.transport == "stdio"
        init_log(
            level=logging.DEBUG if args.debug else logging.INFO,
            handle_stdout=not is_stdio,
            handle_stderr=True,
        )

        logger.info(f"{'=' * 50}\nInitializing git repo ...")
        GitRepoUtil.init_server_code_repo()
        asyncio.create_task(GitRepoUtil.git_fetch_task(interval=300))

        logger.info(f"Starting mcp server ...")
        if is_stdio:
            await mcp.run_async(
                transport=args.transport,
            )
        else:
            await mcp.run_async(
                transport=args.transport,
                host=args.host,
                port=args.port,
                path=args.path,
            )
    except Exception:
        logging.exception("Error when running mcp server")
        exit(1)


def cli_main():
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
