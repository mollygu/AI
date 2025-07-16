import logging
import os
import sys
import json
import subprocess
import tempfile
from pathlib import Path
import datetime

from mcp.server.fastmcp import FastMCP

# Setup logging to project directory
PROJECT_DIR = Path(os.getcwd())
CURRENT_DIR = Path(__file__).parent.absolute()
log_file = PROJECT_DIR / "ui_operator.log"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(log_file)),
        logging.StreamHandler()
    ]
)

# Create a logger for this module
logger = logging.getLogger("mcp_test.ui_operator")
logger.setLevel(logging.INFO)

# Initialize MCP
mcp = FastMCP("ui-operator")

# Add paths to import modules from main project
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", CURRENT_DIR.parent))
sys.path.append(str(PROJECT_ROOT))

logger.info(f"UI Operator initialized with PROJECT_ROOT: {PROJECT_ROOT}")
logger.info(f"Current directory: {os.getcwd()}")
logger.info(f"CURRENT_DIR from __file__: {CURRENT_DIR}")

@mcp.tool()
def login_ngc(user_role: str) -> dict:
    """
    Login to NGC with specified user role using the pytest fixture directly.
    
    Args:
        user_role (str): The user role to login with (e.g., 'org_admin', 'user01')
        
    Returns:
        Dict with login result information
    """
    logger.info(f"Logging in with user role: {user_role}")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"PROJECT_ROOT: {PROJECT_ROOT}")
    logger.info(f"PROJECT_ROOT exists: {PROJECT_ROOT.exists()}")
    logger.info(f"PROJECT_ROOT is dir: {PROJECT_ROOT.is_dir()}")
    logger.info(f"PROJECT_ROOT writable: {os.access(PROJECT_ROOT, os.W_OK)}")
    
    # Create a temporary pytest file IN THE PROJECT DIRECTORY to ensure it can access fixtures
    temp_file_path = PROJECT_ROOT / f"temp_login_{user_role}.py"
    logger.info(f"Creating temporary file at: {temp_file_path}")
    
    try:
        with open(temp_file_path, 'w') as f:
            logger.info(f"File opened for writing")
            f.write(f"""
import json
import os
import sys
import time
from pathlib import Path

import pytest
from playwright.sync_api import expect

# Run a test that uses the get_user_page fixture with extended timeout
@pytest.mark.parametrize('get_user_page', ['{user_role}'], indirect=True)
def test_login(get_user_page):
    # After successful login, do operations with the page
    page_title = get_user_page.title()
    current_url = get_user_page.url
    
    # Print information for debugging
    print(f"\\nLogged in successfully as {user_role}")
    print(f"Page title: {{page_title}}")
    print(f"Current URL: {{current_url}}\\n")
    
    # Create screenshots directory if it doesn't exist
    os.makedirs('screenshots', exist_ok=True)
    
    # Take a screenshot
    screenshot_path = f'screenshots/{user_role}_login.png'
    get_user_page.screenshot(path=screenshot_path)
    
    # Save result to file
    result = {{
        'success': True,
        'user_role': '{user_role}',
        'page_title': page_title,
        'current_url': current_url,
        'screenshot_path': screenshot_path
    }}
    
    with open('login_result.json', 'w') as f:
        json.dump(result, f)
    
    # Keep browser open for a while for debugging if needed
    print("Login successful. Keeping browser open for 3 seconds for inspection...")
    time.sleep(3)
            """)
        logger.info(f"File content written successfully")
        
        # Verify the file was created
        if temp_file_path.exists():
            logger.info(f"Verified: File exists at {temp_file_path}")
            logger.info(f"File size: {temp_file_path.stat().st_size} bytes")
            logger.debug(f"File permissions: {oct(temp_file_path.stat().st_mode)}")
        else:
            logger.error(f"File creation failed! File does not exist at {temp_file_path}")
            return {
                "success": False,
                "error": f"Failed to create temporary test file at {temp_file_path}",
                "log_file": str(log_file)
            }
    
    except Exception as e:
        logger.error(f"Exception while creating file: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to create test file: {str(e)}",
            "log_file": str(log_file)
        }
    
    try:
        # Run pytest with the temporary file directly in the project directory
        # Add higher timeout value to allow more time for login
        # Run in headed mode to see the browser during the login process
        # Add slow motion to better visualize the process
        cmd = [
            "poetry", "run", "pytest", 
            str(temp_file_path), 
            "-v", 
            "--timeout=300", 
            "--headed", 
            "--slowmo=500",  # Add 500ms delay between actions for better visibility
            "-s"  # Allow print statements to be shown in output
        ]
        
        logger.info(f"Running command: {' '.join(cmd)}")
        logger.info(f"Working directory for subprocess: {PROJECT_ROOT}")
        
        # Log environment variables that might affect the execution
        env_vars = {k: v for k, v in os.environ.items() if k in ['PATH', 'PYTHONPATH', 'PROJECT_ROOT']}
        logger.debug(f"Environment variables: {env_vars}")
        
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        
        logger.info(f"Command completed with return code: {result.returncode}")
        logger.debug(f"Pytest stdout: {result.stdout}")
        logger.debug(f"Pytest stderr: {result.stderr}")
        
        if result.returncode != 0:
            logger.error(f"Pytest error: {result.stderr}")
            
            # Try to extract detailed error information
            error_detail = "Unknown error"
            if "Error at setup of test_login" in result.stdout:
                # Extract the specific error message
                error_start = result.stdout.find("Error at setup of test_login")
                if error_start != -1:
                    error_end = result.stdout.find("==", error_start)
                    if error_end != -1:
                        error_detail = result.stdout[error_start:error_end].strip()
            
            # Try checking if we already have a stored session for this user
            stored_session_path = PROJECT_ROOT / f"{user_role}.json"
            if stored_session_path.exists():
                logger.info(f"Found existing session for {user_role}, returning partial success")
                return {
                    "success": True,
                    "user_role": user_role,
                    "message": "Using stored session, login process failed but found existing session",
                    "stored_session": str(stored_session_path),
                    "error_detail": error_detail,
                    "log_file": str(log_file),
                    "temp_file_path": str(temp_file_path)  # Include temporary file path for debugging
                }
                
            # Check if any screenshots were taken that might help with debugging
            screenshots_dir = PROJECT_ROOT / "screenshots"
            if screenshots_dir.exists():
                screenshots = list(screenshots_dir.glob(f"*{user_role}*.png"))
                if screenshots:
                    latest_screenshot = max(screenshots, key=os.path.getctime)
                    logger.info(f"Found screenshot that might help with debugging: {latest_screenshot}")
                    return {
                        "success": False,
                        "error": f"Failed to login but captured debugging screenshot",
                        "error_detail": error_detail,
                        "debug_screenshot": str(latest_screenshot),
                        "temp_file_path": str(temp_file_path),
                        "log_file": str(log_file)
                    }
            
            return {
                "success": False,
                "error": f"Failed to login: {result.stderr}",
                "error_detail": error_detail,
                "temp_file_path": str(temp_file_path),
                "log_file": str(log_file)
            }
        
        # Read result from file
        result_file_path = PROJECT_ROOT / 'login_result.json'
        logger.info(f"Checking for result file at: {result_file_path}")
        logger.info(f"Result file exists: {result_file_path.exists()}")
        
        if result_file_path.exists():
            logger.info(f"Reading result file")
            with open(result_file_path, 'r') as f:
                login_result = json.load(f)
            
            # Clean up result file
            logger.info(f"Removing result file")
            os.remove(result_file_path)
            
            # Add log file path to result
            login_result["log_file"] = str(log_file)
            
            # Only remove the temporary file if login was successful
            logger.info(f"Login successful, removing temporary file")
            if temp_file_path.exists():
                os.remove(temp_file_path)
                logger.info(f"Temporary file removed")
            
            return login_result
        else:
            logger.error(f"Result file not found at {result_file_path}")
            return {
                "success": False,
                "error": "No result file found, login may have failed",
                "temp_file_path": str(temp_file_path),
                "log_file": str(log_file)
            }
            
    except Exception as e:
        logger.error(f"Failed to run pytest: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "temp_file_path": str(temp_file_path),
            "log_file": str(log_file)
        }
    finally:
        # Log the temporary file status regardless of success/failure
        logger.info(f"Temporary test file status: {temp_file_path}")
        logger.info(f"Temporary file exists: {temp_file_path.exists()}")
        # No longer deleting the temporary file here to preserve it for debugging

if __name__ == "__main__":
    logger.info("Starting UI Operator MCP Server")
    mcp.run(transport='stdio') 