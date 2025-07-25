import asyncio
import httpx
import json
from httpx_sse import aconnect_sse

async def run_client():
    try:
        print("Connecting to MCP server...")
        base_url = "http://localhost:8000"
        sse_endpoint = "/sse"  # This was the only endpoint that returned 200 OK
        
        # Connect to the server
        async with httpx.AsyncClient() as client:
            print(f"Connecting to SSE endpoint: {base_url}{sse_endpoint}")
            
            try:
                # Connect to the SSE endpoint
                async with aconnect_sse(client, "GET", f"{base_url}{sse_endpoint}") as event_source:
                    # Set up a JSON-RPC request to initialize the connection
                    initialize_msg = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "capabilities": {
                                "tools": {}
                            }
                        }
                    }
                    
                    # Send the initialize request
                    print("Sending initialize request...")
                    await client.post(f"{base_url}{sse_endpoint}", json=initialize_msg)
                    
                    # Wait for and process events
                    print("Waiting for events...")
                    async for event in event_source.aiter_sse():
                        print(f"Received event: {event.data}")
                        
                        # After getting initialization response, send a tool call
                        add_msg = {
                            "jsonrpc": "2.0",
                            "id": 2,
                            "method": "callTool",
                            "params": {
                                "tool": "add",
                                "arguments": {
                                    "a": 5, 
                                    "b": 3
                                }
                            }
                        }
                        
                        print("Sending add request...")
                        await client.post(f"{base_url}{sse_endpoint}", json=add_msg)
                        break  # Break after first event to wait for the tool response
                    
                    # Wait for add response
                    print("Waiting for add result...")
                    async for event in event_source.aiter_sse():
                        print(f"Received event: {event.data}")
                        # Try to parse the JSON response
                        try:
                            response = json.loads(event.data)
                            if "result" in response:
                                print(f"5 + 3 = {response.get('result', {}).get('result')}")
                                break
                        except json.JSONDecodeError:
                            print(f"Failed to parse JSON: {event.data}")
                
            except Exception as e:
                print(f"SSE connection error: {e}")
        
        print("All operations completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(run_client()) 