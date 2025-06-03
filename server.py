# server.py
import argparse
import logging
import json
from typing import List, Dict, Any
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from mcp.server import Server
import uvicorn
import httpx
# Import our custom modules
from config import settings
from openwebui_client import model_manager

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("openwebui_agents")

# Define list_agents tool to show available models
@mcp.tool()
async def list_agents() -> str:
    """
    List all available OpenWebUI agents (models).
    
    Returns:
        JSON string containing information about available agents.
    """
    logger.info("list_agents tool called")
    
    # Get the filtered agents through the model manager
    agents = await model_manager.get_available_agents()
    logger.info(f"Model manager returned {len(agents)} agents after filtering")
    
    # Process agents
    simplified_agents = []
    for agent in agents:
        # Create a simplified representation with just the essential details
        simplified = {
            "id": agent.get("id"),
            "name": agent.get("name", agent.get("id")),
            "description": agent.get("info", {}).get("meta", {}).get("description", "No description available")
        }
        simplified_agents.append(simplified)
    
    return json.dumps(simplified_agents, indent=2)

# Define the main chat tool
@mcp.tool()
async def openwebui_chat(agent_id: str, prompt: str) -> str:
    """
    Performs a chat completion using a specified OpenWebUI agent (model).
    
    Args:
        agent_id: The ID of the OpenWebUI model (agent) to use.
        prompt: The prompt for the agent.
        
    Returns:
        The textual response from the OpenWebUI agent, or an error message.
    """
    logger.info(f"openwebui_chat tool called for agent '{agent_id}'")
    
    # Truncate the prompt in logs to avoid excessive log entries
    if len(prompt) > 100:
        logger.debug(f"Prompt (truncated): {prompt[:100]}...")
    else:
        logger.debug(f"Prompt: {prompt}")
        
    try:
        # Get all available agents and verify this agent is available
        available_agents = await model_manager.get_available_agents()
        agent_ids = [agent.get("id") for agent in available_agents]
        
        if agent_id not in agent_ids:
            error_msg = f"Error: Agent '{agent_id}' is not available. Available agents are: {', '.join(agent_ids)}"
            logger.error(error_msg)
            return error_msg
            
        # Find the actual agent object for better logging
        agent_obj = next((agent for agent in available_agents if agent.get("id") == agent_id), None)
        if agent_obj:
            logger.info(f"Using agent: {agent_id} ({agent_obj.get('name', 'Unknown')})")
            
        # Prepare a simplified payload for OpenWebUI API
        url = f"{settings.OPENWEBUI_URL}/api/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.OPENWEBUI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": agent_id,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        # Make the request directly in the tool
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
                timeout=60.0
            )
            
            # If there's an error, get the detailed error message
            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    logger.error(f"API error: {error_data}")
                    return f"Error from OpenWebUI API: {error_data}"
                except:
                    logger.error(f"API error (non-JSON): {response.text}")
                    return f"Error from OpenWebUI API: {response.text}"
            
            # Process the successful response
            data = response.json()
            
            # Extract the completion text
            if "choices" in data and len(data["choices"]) > 0:
                message = data["choices"][0].get("message", {})
                content = message.get("content", "No content returned")
                logger.info("Successfully got response from OpenWebUI API")
                return content
            else:
                logger.error(f"Unexpected response format: {data}")
                return f"Error: Unexpected response format from OpenWebUI API: {data}"
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error: {e}")
        return f"HTTP error during chat completion: {e}"
        
    except httpx.RequestError as e:
        logger.error(f"Request error: {e}")
        return f"Request error during chat completion: {e}"
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return f"Unexpected error during chat completion: {str(e)}"

# Function to create Starlette app for SSE transport
def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can serve the provided MCP server with SSE."""
    # Create an SSE transport with a base path for messages
    sse = SseServerTransport("/messages/")
    async def handle_sse(request: Request) -> None:
        """Handler for SSE connections."""
        # Connect the SSE transport to the request
        async with sse.connect_sse(
                request.scope,
                request.receive,
                request._send,  # noqa: SLF001
        ) as (read_stream, write_stream):
            # Run the MCP server with the SSE streams
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )
    # Create and return the Starlette application with routes
    return Starlette(
        debug=debug,
        routes=[
            Route("/", endpoint=lambda request: JSONResponse({
                'status': 'ready',
                'server': 'OpenWebUI MCP Agent Server',
                'transport': 'SSE'
            })),
            Route("/sse", endpoint=handle_sse),  # Endpoint for SSE connections
            Mount("/messages/", app=sse.handle_post_message),  # Endpoint for posting messages
        ],
    )

if __name__ == "__main__":
    # Get the underlying MCP server from the FastMCP instance
    mcp_server = mcp._mcp_server  # noqa: WPS437
    
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description='Run MCP server for OpenWebUI agents')
    parser.add_argument('--transport', choices=['stdio', 'sse'], default='stdio', 
                        help='Transport mode (stdio or sse)')
    parser.add_argument('--host', default='0.0.0.0', 
                        help='Host to bind to (for SSE mode)')
    parser.add_argument('--port', type=int, default=8080, 
                        help='Port to listen on (for SSE mode)')
    args = parser.parse_args()
    
    # Log startup information
    logger.info("Config: Loaded environment variables:")
    logger.info(f"  OPENWEBUI_URL={settings.OPENWEBUI_URL}")
    logger.info(f"  OPENWEBUI_API_KEY={'sk-' + settings.OPENWEBUI_API_KEY[3:10] + '...' if settings.OPENWEBUI_API_KEY else 'None'}")
    logger.info(f"  AGENT_WHITELIST={settings.AGENT_WHITELIST}")
    logger.info(f"  AGENT_BLACKLIST={settings.AGENT_BLACKLIST}")
    logger.info(f"  LOG_LEVEL={settings.LOG_LEVEL}")
    
    if args.transport == 'sse':
        logger.info(f"Starting OpenWebUI MCP Agent Server with SSE transport on {args.host}:{args.port}")
    else:
        logger.info("Starting OpenWebUI MCP Agent Server with stdio transport")
        
    # Launch the server with the selected transport mode
    if args.transport == 'stdio':
        # Run with stdio transport (default)
        mcp.run(transport='stdio')
    else:
        # Run with SSE transport (web-based)
        starlette_app = create_starlette_app(mcp_server, debug=True)
        uvicorn.run(starlette_app, host=args.host, port=args.port)