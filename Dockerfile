FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir mcp>=1.4.1 httpx>=0.28.1 starlette>=0.46.1 uvicorn>=0.34.0 python-dotenv>=1.0.0

# Copy application files
COPY server.py config.py openwebui_client.py ./

# Default command - run with SSE transport
CMD ["python", "server.py", "--transport", "sse", "--host", "0.0.0.0", "--port", "8080"]