# MCP explore

## Install mcp 
    pip3 install mcp
## Develop mcp server
### Code sample, key structure as below
    from mcp.server.fastmcp import FastMCP
    
    mcp = FastMCP("LocalExecutor")
    
    @mcp.tool()
    def add(a: int, b: int) -> int:
        """Add two numbers"""
        return a + b
        
    if __name__ == "__main__":
        mcp.run(transport='stdio')
    
## Configure in cursor
Example, update the command and args based on :
```
    {
    "version": 1,
    "mcpServers": {
        "math-mcp": {
            "command": "python",
            "args": ["<path>/AI/mcp_test/mcpmath.py"]
        },
        "ui-operator": {
            "command": "/Users/juagu/Library/Caches/pypoetry/virtualenvs/ngc-ui-test-LAXCvaQS-py3.11/bin/python",
            "args": ["/Users/juagu/Documents/GitHub/AI/mcp_test/ui_operator.py"]
        }
    }
    }
```
