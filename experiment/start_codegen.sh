#!/bin/bash

# Function to show usage
show_usage() {
    echo "Usage: $0 <template_id>"
    echo "Example: $0 3574602"
    echo ""
    echo "Optional environment variables:"
    echo "  project_path : Path to project directory"
    echo "                 Default: /Users/juagu/Documents/work_2025/ngc-ui-test"
}

# Check if template ID is provided as argument
if [ $# -ne 1 ]; then
    echo "Error: Template ID not provided"
    show_usage
    exit 1
fi

# Get template ID from argument
templateid=$1

# Validate template ID is numeric
if ! [[ "$templateid" =~ ^[0-9]+$ ]]; then
    echo "Error: Template ID must be a number"
    show_usage
    exit 1
fi

# Set default project path if not provided
if [ -z "$project_path" ]; then
    export project_path="/Users/juagu/Documents/work_2025/ngc-ui-test"
    echo "Using default project path: $project_path"
fi

/Users/juagu/Documents/GitHub/aide/.venv/bin/python "/Users/juagu/Documents/GitHub/aide/src/tests/devtest_client.py" "$templateid" > $project_path/input/testplans/testplan_$templateid.md

# Create directories if they don't exist
mkdir -p "$project_path/input/snapshot/$templateid"
mkdir -p "$project_path/input/records"

# Run playwright codegen
echo "Starting Playwright codegen for template ID: $templateid"
echo "Recording to: $project_path/input/records/"
echo "Snapshots will be saved to: $project_path/input/snapshot/$templateid"

cd /Users/juagu/Documents/work_2025/playwright
rm -rf $project_path/input/snapshot/$templateid
rm -f $project_path/input/records/${templateid}.py
npx playwright codegen \
    --target python-pytest \
    "https://catalog.stg.ngc.nvidia.com/" \
    --snapshots-dir "$project_path/input/snapshot/$templateid" \
    --output "$project_path/input/records/${templateid}.py"

# Check if codegen was successful
if [ $? -eq 0 ]; then
    echo "Recording completed successfully"
    echo "Test file saved as: $project_path/input/records/T${templateid}.py"
    echo "Snapshots saved in: $project_path/input/snapshot/$templateid"
else
    echo "Error: Playwright codegen failed"
    exit 1
fi

