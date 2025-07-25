#!/usr/bin/env python3
"""
Working STDIO MCP Client for Math Server
A client that properly handles MCP protocol without file handling issues.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

class WorkingMathMCPClient:
    """Working STDIO client for the Math MCP server."""
    
    def __init__(self, server_path: str = "mcpmath.py"):
        """Initialize the client."""
        self.server_path = Path(server_path)
        self.base_dir = self.server_path.parent
    
    def _call_server(self, method: str, arguments: dict) -> dict:
        """Make a call to the MCP server."""
        try:
            # Create the command
            cmd = [sys.executable, str(self.server_path)]
            
            # Prepare all messages to send
            messages = []
            
            # 1. Initialize request
            init_request = {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "clientInfo": {
                        "name": "MathMCPClient",
                        "version": "1.0.0"
                    }
                }
            }
            messages.append(init_request)
            
            # 2. Initialized notification
            initialized_notification = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {}
            }
            messages.append(initialized_notification)
            
            # 3. Tool call request
            tool_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": method,
                    "arguments": arguments
                }
            }
            messages.append(tool_request)
            
            # Convert all messages to input string
            input_data = ""
            for msg in messages:
                input_data += json.dumps(msg) + "\n"
            
            # Start the server process and communicate
            process = subprocess.Popen(
                cmd,
                cwd=self.base_dir,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Send input and get response
            stdout, stderr = process.communicate(input=input_data)
            
            # Parse response
            if stdout.strip():
                lines = stdout.strip().split('\n')
                for line in reversed(lines):
                    if line.strip():
                        try:
                            response = json.loads(line.strip())
                            if response.get("id") == 1:  # Tool call response
                                return response.get("result", {})
                        except json.JSONDecodeError:
                            continue
                
                # If no tool call response found, return the last valid response
                for line in reversed(lines):
                    if line.strip():
                        try:
                            response = json.loads(line.strip())
                            return response.get("result", {})
                        except json.JSONDecodeError:
                            continue
                
                return {"success": False, "error": f"Invalid response: {stdout}"}
            else:
                return {"success": False, "error": f"Server error: {stderr}"}
                
        except Exception as e:
            return {"success": False, "error": f"Client error: {str(e)}"}
    
    def add(self, a: int, b: int) -> dict:
        """Add two numbers."""
        return self._call_server("add", {"a": a, "b": b})
    
    def subtract(self, a: int, b: int) -> dict:
        """Subtract two numbers."""
        return self._call_server("subtract", {"a": a, "b": b})
    
    def multiply(self, a: int, b: int) -> dict:
        """Multiply two numbers."""
        return self._call_server("multiply", {"a": a, "b": b})
    
    def divide(self, a: int, b: int) -> dict:
        """Divide two numbers."""
        return self._call_server("divide", {"a": a, "b": b})
    
    def power(self, a: int, b: int) -> dict:
        """Raise a to the power of b."""
        return self._call_server("power", {"a": a, "b": b})

# Test function
def test_working_math_client():
    """Test the working math MCP client."""
    print("Testing Working Math MCP Client")
    print("=" * 35)
    
    # Create client
    client = WorkingMathMCPClient()
    
    # Test operations
    operations = [
        ("add", 5, 3),
        ("subtract", 10, 4),
        ("multiply", 6, 7),
        ("divide", 15, 3),
        ("power", 2, 8)
    ]
    
    for op_name, a, b in operations:
        print(f"\nTesting {op_name}({a}, {b})...")
        
        if op_name == "add":
            result = client.add(a, b)
        elif op_name == "subtract":
            result = client.subtract(a, b)
        elif op_name == "multiply":
            result = client.multiply(a, b)
        elif op_name == "divide":
            result = client.divide(a, b)
        elif op_name == "power":
            result = client.power(a, b)
        
        print(f"Result: {json.dumps(result, indent=2)}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_working_math_client() 