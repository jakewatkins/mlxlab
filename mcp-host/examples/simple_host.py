"""
Simple example of using MCP Host.

This demonstrates the basic usage of the MCP Host to manage multiple servers.
"""

import asyncio
import logging
from mcp_host import MCPHost

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """Main example function."""
    
    # Create MCP Host instance
    async with MCPHost(config_path="mcp.json") as host:
        logger.info("MCP Host initialized successfully")
        
        # Get all tools from all servers
        tools = await host.get_tools()
        logger.info(f"Available tools: {len(tools)}")
        for tool in tools:
            print(f"  - {tool['server']}.{tool['name']}: {tool.get('description', 'No description')}")
        
        # Get prompts
        prompts = await host.get_prompts()
        logger.info(f"Available prompts: {len(prompts)}")
        
        # Get resources
        resources = await host.get_resources()
        logger.info(f"Available resources: {len(resources)}")
        
        # Get metrics
        metrics = host.get_metrics()
        logger.info(f"Metrics: {metrics}")
        
        # Get server status
        servers = host.get_servers()
        logger.info(f"Servers: {servers}")

        # Example: Call the filesystem write_file tool
        logger.info("Testing filesystem write_file tool...")
        try:
            result = await host.call_tool("brave-search.brave_news_search", {
                "query": "what are today's top news headlines?"      
            })
            logger.info(f"Write file result: {result}")
        except Exception as e:
            logger.error(f"Error calling write_file: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
