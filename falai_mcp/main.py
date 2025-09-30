from __future__ import annotations

from .config import get_settings
from .server import get_server


def main() -> None:
    settings = get_settings()
    server = get_server()
    if settings.enable_http:
        server.run(transport="http", host=settings.http_host, port=settings.http_port)
    else:
        server.run()


if __name__ == "__main__":
    main()
