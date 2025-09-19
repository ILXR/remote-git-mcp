import logging
import asyncio
import argparse
from log import init_log
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# load .env
load_dotenv()
# import mcp tools
from tools import mcp, GitRepoUtil


def parse_args():
    parser = argparse.ArgumentParser(description="Remote Git MCP")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        type=str,
        default="stdio",
        help="Transport Protocol",
    )
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host")
    parser.add_argument("--port", type=int, default=8999, help="Port")
    parser.add_argument("--path", type=str, default="/mcp", help="Mcp Path")
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        default=False,
        help="Quiet Mode, only log to file",
    )
    return parser.parse_args()


async def main():
    try:
        args = parse_args()
        init_log(enable_stdout=not args.quiet)

        logger.info("=" * 100)
        logger.info("Initializing git repo ...")
        GitRepoUtil.init_server_code_repo()
        asyncio.create_task(GitRepoUtil.git_fetch_task(interval=300))

        logger.info("Starting mcp server ...")
        if args.transport == "stdio":
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
    except KeyboardInterrupt:
        logger.info("Shutting down mcp server ...")
        exit(0)
    except Exception:
        logging.exception("Error when starting mcp server")
        exit(1)


def cli_main():
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
