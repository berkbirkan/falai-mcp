# falai-mcp-server

A FastMCP server that exposes core fal.ai model API operations (model catalogue, search, schema retrieval, inference, queue management, CDN uploads). The server can run locally over STDIO or remotely via the Streamable HTTP transport, and now ships with Docker support for easier deployment.

<video controls width="1920" height="512" src="https://github.com/user-attachments/assets/f8cfb202-3d69-4395-959d-76b2a11181e7">Your browser does not support the video tag.</video>

## Quick Start

### PyPI Installation (Recommended)

```bash
pip install falai-mcp-tools
```

After installation, you can run the server with:

```bash
falai-mcp
```

### Manual Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/berkbirkan/falai-mcp.git
   cd falai-mcp
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install the project in editable mode:
   ```bash
   pip install -e .
   ```

## Requirements

- Python 3.10 or newer
- A fal.ai API key: either `FAL_KEY` or the `FAL_KEY_ID`/`FAL_KEY_SECRET` pair
- Docker (optional, only if you prefer containerized execution)

## Configuration

Environment variables (prefixed with `FALAI_`) control runtime behaviour:

| Variable | Description |
| --- | --- |
| `FAL_KEY` or `FAL_KEY_ID`/`FAL_KEY_SECRET` | fal.ai credentials (required for live API calls) |
| `FALAI_ALLOWED_MODELS` | Comma-separated list of explicit model IDs to expose |
| `FALAI_MODEL_KEYWORDS` | Comma-separated keywords to pre-filter models when no explicit list is provided |
| `FALAI_REQUEST_TIMEOUT` | HTTP timeout (seconds) for fal.ai requests (default: `120`) |
| `FALAI_ENABLE_HTTP` | Set to `true` to run the server with the Streamable HTTP transport |
| `FALAI_HTTP_HOST` / `FALAI_HTTP_PORT` | Bind address and port when HTTP transport is enabled (defaults: `0.0.0.0` / `8080`) |

If you prefer a `.env` file, place it next to the project root (or mount it into the container) and load it before running the server.

> Clients can override credentials and model filters per MCP session through the `configure` tool. Environment variables supply defaults when the client does not set overrides.

## Usage

### Local STDIO usage

1. Ensure your virtual environment is active and credentials are exported:
   ```bash
   export FAL_KEY=sk_live_...
   ```

2. Run the server with the default STDIO transport:
   ```bash
   falai-mcp
   ```

3. Leave the process running; configure your MCP client (Claude, Cursor, etc.) to launch this command via STDIO (see the client integration section).

### Remote HTTP usage

1. Export credentials and enable the HTTP transport:
   ```bash
   export FAL_KEY=sk_live_...
   export FALAI_ENABLE_HTTP=true
   export FALAI_HTTP_PORT=8080  # optional override
   ```

2. Start the server so it listens on the configured host/port:
   ```bash
   falai-mcp
   ```

3. Confirm the HTTP transport is reachable (for example with `curl -I http://localhost:8080/mcp/`). Clients should connect to `http://<host>:<port>/mcp/`.

### Docker Usage

1. Build the container image:
   ```bash
   docker build -t falai-mcp .
   ```

2. Run the container with HTTP enabled and publish the port:
   ```bash
   docker run \
     --rm \
     -e FAL_KEY=sk_live_... \
     -e FALAI_ENABLE_HTTP=true \
     -e FALAI_HTTP_PORT=8080 \
     -p 8080:8080 \
     falai-mcp
   ```

3. The MCP endpoint is now available at `http://localhost:8080/mcp/`.

## Client integrations

Below are example configurations for popular MCP clients. Adjust paths, environment variables, and identifiers to match your setup.

### Claude Desktop

Claude Desktop keeps its configuration in `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or the equivalent path on your platform.

- **STDIO (local process)**
  ```json
  {
    "mcpServers": {
      "falai-local": {
        "command": "falai-mcp",
        "args": [],
        "env": {
          "FAL_KEY": "sk_live_..."
        }
      }
    }
  }
  ```
  Restart Claude Desktop after saving changes. Claude will spawn `falai-mcp` and communicate over STDIO.

- **Remote HTTP server**
  ```json
  {
    "mcpServers": {
      "falai-remote": {
        "transport": {
          "type": "http",
          "url": "http://localhost:8080/mcp/"
        }
      }
    }
  }
  ```

### Cursor

Cursor reads MCP configuration from `~/.cursor/mcp.json`.

- **STDIO (local process)**
  ```json
  {
    "clients": {
      "falai-local": {
        "command": "falai-mcp",
        "args": [],
        "env": {
          "FAL_KEY": "sk_live_..."
        }
      }
    }
  }
  ```

- **Remote HTTP server**
  ```json
  {
    "clients": {
      "falai-remote": {
        "transport": {
          "type": "http",
          "url": "http://localhost:8080/mcp/"
        }
      }
    }
  }
  ```

After editing `mcp.json`, restart Cursor (or reload MCP connections) to pick up the new configuration.

## Available tools

| Tool | Description |
| --- | --- |
| `configure(api_key=None, allowed_models=None, model_keywords=None)` | Override credentials and access scope for the active session |
| `models(page=None, total=None)` | List available models with optional pagination |
| `search(keywords)` | Search the model catalogue using space-separated keywords |
| `schema(model_id)` | Retrieve the OpenAPI schema for a model |
| `generate(model, parameters, queue=False)` | Run synchronous or queued inference |
| `result(url)` | Fetch the result of a queued request |
| `status(url)` | Check the status (optionally with logs) of a queued request |
| `cancel(url)` | Cancel a queued request |
| `upload(path)` | Upload a local file to fal.ai CDN |

All tools enforce any configured allow-list and respect per-session overrides from the `configure` tool.

## Development

### Building for PyPI

1. Install build tools:
   ```bash
   pip install build twine
   ```

2. Build the package:
   ```bash
   python -m build
   ```

3. Upload to PyPI (test first with TestPyPI):
   ```bash
   # Test upload
   python -m twine upload --repository testpypi dist/*
   
   # Production upload
   python -m twine upload dist/*
   ```

## Notes

- Schema retrieval and queue inspection require valid fal.ai credentials; errors appear as MCP tool errors if credentials are missing or invalid.
- Model discovery falls back to the bundled `fal-client` endpoint catalogue when fal.ai's public APIs are unavailable.
- When running remotely, ensure network access between the client and the MCP server (open firewall ports, configure TLS or reverse proxies if needed).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.