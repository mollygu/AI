import os
import sys
import logging
from mcp.server.fastmcp import FastMCP

# Set up logging to a file for debugging
log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_debug.log")
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()]
)

# Create MCP instance
mcp = FastMCP("LocalExecutor")

@mcp.tool()
def add(a, b):
    """Add two numbers"""
    logging.debug(f"Adding {a} + {b}")
    return a + b

@mcp.tool()
def subtract(a, b):
    """Subtract two numbers"""
    logging.debug(f"Subtracting {a} - {b}")
    return a - b

@mcp.tool()
def multiply(a, b):
    """Multiply two numbers"""
    logging.debug(f"Multiplying {a} * {b}")
    return a * b

@mcp.tool()
def divide(a, b):
    """Divide two numbers"""
    logging.debug(f"Dividing {a} / {b}")
    return a / b

@mcp.tool()
def power(a, b):
    """Raise a to the power of b"""
    logging.debug(f"Calculating {a} ** {b}")
    return a ** b

if __name__ == "__main__":
    try:
        logging.debug("Starting MCP server with stdio transport")
        sys.stderr.write("MCP server starting in stdio mode\n")
        sys.stderr.flush()
        # Start the MCP server
        mcp.run(transport='stdio')
    except Exception as e:
        logging.error(f"Error in MCP server: {e}")
        sys.stderr.write(f"MCP server error: {e}\n")
        sys.stderr.flush()
        sys.exit(1)
