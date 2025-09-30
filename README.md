# fal.ai FastMCP server

A FastMCP server that exposes core fal.ai model API operations (listing, searching, schema retrieval, generation, queue management, and CDN uploads). The server can run either locally over STDIO or remotely via the Streamable HTTP transport.

## Features

- Runtime model catalogue derived from the packaged `fal-client` endpoint definitions
- Optional allow-list filtering or keyword-based scoping
- Tools for model listing/search, schema retrieval, queued generation, queue inspection, cancellation, and CDN uploads
- Works with STDIO (local tools) or Streamable HTTP transport (remote MCP server)

## Installation

Create and activate a virtual environment, then install in editable mode:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Ensure you have a valid fal.ai API key — either `FAL_KEY` _or_ the `FAL_KEY_ID`/`FAL_KEY_SECRET` pair.

## Configuration

Environment variables (prefixed with `FALAI_`) drive runtime behaviour:

| Variable | Description |
| --- | --- |
| `FAL_KEY` or `FAL_KEY_ID`/`FAL_KEY_SECRET` | fal.ai credentials (required for live API calls) |
| `FALAI_ALLOWED_MODELS` | Comma-separated list of explicit model IDs to expose |
| `FALAI_MODEL_KEYWORDS` | Comma-separated keywords to pre-filter models when no explicit list is provided |
| `FALAI_REQUEST_TIMEOUT` | HTTP timeout (seconds) for fal.ai requests (default: `120`)
| `FALAI_ENABLE_HTTP` | Set to `true` to run the server with the Streamable HTTP transport |
| `FALAI_HTTP_HOST` / `FALAI_HTTP_PORT` | Bind address and port when `ENABLE_HTTP` is enabled |

Example `.env` snippet:

```env
FAL_KEY=sk_live_...
FALAI_ENABLE_HTTP=true
FALAI_HTTP_HOST=0.0.0.0
FALAI_HTTP_PORT=8080
FALAI_ALLOWED_MODELS=fal-ai/flux/dev,fal-ai/flux-pro/v1.1-ultra
```

> 💡 Clients can override credentials and scoping per MCP session by calling the
> `configure` tool (e.g. provide their own API key or allowed model list) once
> the connection is established. Environment variables act as defaults when a
> client doesn’t supply overrides.

## Running locally (STDIO)

Use the default STDIO transport for local MCP integrations (e.g., Claude Desktop):

```bash
falai-mcp
```

## Running as a remote MCP server

Enable the HTTP transport to expose the server over the network:

```bash
FALAI_ENABLE_HTTP=true FALAI_HTTP_PORT=8080 falai-mcp
```

Clients should connect to `http://<host>:<port>/mcp/`.

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

All tools enforce the configured allow-list (if provided).

## Notes

- Schema retrieval and queue inspection require valid fal.ai credentials; errors are surfaced as MCP tool errors when credentials are missing or invalid.
- Model discovery falls back to the `fal-client` endpoint catalogue when fal.ai’s public APIs are unavailable.
