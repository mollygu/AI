from aide.mcp_tools import initialize_tools
import asyncio
import argparse
import re

def get_devtest_client():
    # Initialize MCP tools with stdio transport
    mcp_servers = initialize_tools("stdio")
    # Get the devtest group of tools
    return mcp_servers["devtest"]

def format_test_details(details) -> str:
    """Format the test details into a readable structure"""
    if not details or not details[0].text:
        return "No test details found"
    
    text = details[0].text
    
    # Extract sections using regex
    template_id = re.search(r'Template ID: (\d+)', text)
    title = re.search(r'Title: (.*?)\n', text)
    test_steps = re.search(r'Test Steps:(.*?)(?=Expected Result:)', text, re.DOTALL)
    expected_result = re.search(r'Expected Result:(.*?)$', text, re.DOTALL)
    
    formatted = []
    formatted.append("=" * 80)
    if template_id:
        formatted.append(f"Template ID: {template_id.group(1)}")
    if title:
        formatted.append(f"\nTitle: {title.group(1).strip()}")
    if test_steps:
        formatted.append("\nTest Steps:")
        steps = test_steps.group(1).strip().split('\n')
        formatted.extend(f"  {step.strip()}" for step in steps if step.strip())
    if expected_result:
        formatted.append("\nExpected Result:")
        results = expected_result.group(1).strip().split('\n')
        formatted.extend(f"  {result.strip()}" for result in results if result.strip())
    formatted.append("=" * 80)
    
    return '\n'.join(formatted)
async def get_test_details(template_id: int) -> str:
    """Get test steps and expected results for a template"""
    mcp = get_devtest_client()
    params = {"template_id": template_id}
    return await mcp.call_tool("fetch_test_details", params)

async def get_user_tasks(project_id: int, username: str, status: str = "") -> list[int]:
    """Get task IDs for a user
    Args:
        project_id: DevTest project ID
        username: Username to get tasks for
        status: Optional filter - can be "", "Open", "InProgress", or "Closed"
    """
    mcp = get_devtest_client()
    params = {
        "project_id": project_id,
        "username": username,
        "status_filter": status
    }
    return await mcp.call_tool("fetch_user_tasks", params)

async def get_task_details(project_id: int, task_ids: list[int]) -> list[dict]:
    """Get details for specific tasks
    Args:
        project_id: DevTest project ID
        task_ids: List of task IDs to get details for
    """
    mcp = get_devtest_client()
    params = {
        "project_id": project_id,
        "task_ids": task_ids
    }
    return await mcp.call_tool("fetch_task_details", params)

async def main(template_id: int):
    try:
        # Get test details for a template
        print(f"\nTesting get_test_details() with template_id={template_id}")
        test_details = await get_test_details(template_id)
        print(format_test_details(test_details))
        
        # # Get user's tasks
        # print(f"\nTesting get_user_tasks() with project_id={project_id}, username={username}")
        # tasks = await get_user_tasks(project_id, username, status="Open")
        # print("Open tasks:")
        # print(tasks)
        
        # # Get details for those tasks
        # if tasks:
        #     print(f"\nTesting get_task_details() with tasks={tasks[:3]}")  # Limiting to first 3 tasks for readability
        #     task_details = await get_task_details(project_id, tasks[:3])
        #     print("Task details:")
        #     for task in task_details:
        #         print(f"Task: {task}")
    except Exception as e:
        print(f"Error occurred: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='DevTest Client')
    parser.add_argument('template_id', type=int, help='Template ID to fetch details for')
    args = parser.parse_args()
    
    asyncio.run(main(args.template_id)) 