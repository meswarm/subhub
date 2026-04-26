"""SubHub 主入口。默认启动 HTTP API，并在同一进程中处理 webhook 提醒。"""

import argparse
import sys

from subhub.config import load_config
from subhub.store import SubscriptionStore


def _run_api_server(config, store, host: str, port: int):
    """启动 HTTP API 服务。"""
    import uvicorn

    from subhub.api import create_app

    app = create_app(config=config, store=store)
    uvicorn.run(app, host=host, port=port)


def main():
    parser = argparse.ArgumentParser(description="SubHub API 服务")
    parser.add_argument("--config", "-c", default=None,
                        help="配置文件路径（默认自动查找）")
    parser.add_argument("--api", action="store_true",
                        help="兼容参数：显式启动 HTTP API 服务")
    parser.add_argument("--host", default=None,
                        help="API 服务监听地址（默认读取 config.toml 的 [server].host）")
    parser.add_argument("--port", type=int, default=None,
                        help="API 服务端口（默认读取 config.toml 的 [server].port）")
    args = parser.parse_args()

    try:
        config = load_config(config_path=args.config)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    store = SubscriptionStore(
        config.data.filepath,
        dismissed_filepath=config.data.dismissed_filepath,
    )
    host = args.host or config.server.host
    port = args.port or config.server.port
    _run_api_server(config, store, host, port)


if __name__ == "__main__":
    main()
