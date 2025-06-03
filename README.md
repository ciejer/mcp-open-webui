# OpenWebUI MCP Server

An external Multi-Agent Control Plane (MCP) server that integrates with OpenWebUI to expose LLM models as MCP agents.

## Features

- Agent Discovery: Dynamically list available agents from an OpenWebUI instance
- Task Execution: Perform one-off tasks using a specified OpenWebUI model
- Configurable filtering with whitelist/blacklist
- Caching support for better performance
- Support for both stdio and SSE transports

## Configuration

The server is configured via environment variables (or a `.env` file):
