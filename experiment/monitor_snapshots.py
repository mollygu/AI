#!/usr/bin/env python3
"""
Playwright Snapshot Monitor

This script monitors Playwright test files and their corresponding snapshot directories,
automatically creating a new file with comments about snapshots after each Playwright action.

Usage:
    python monitor_snapshots.py <case_number>

Example:
    python monitor_snapshots.py 3574602
"""

import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import glob
import re
import sys
from pathlib import Path
import shutil

class PlaywrightSnapshotHandler(FileSystemEventHandler):
    def __init__(self, record_dir, snapshot_dir, case_number):
        self.record_dir = record_dir
        self.snapshot_dir = snapshot_dir
        self.case_number = str(case_number)
        self.last_known_snapshots = {}
        self.last_known_actions = {}
        self.last_known_assertions = {}
        self.output_file = os.path.join(record_dir, f"{self.case_number}_with_snapshots.py")
        
        # Initialize tracking for this case number
        self._initialize_tracking()
        
        # Create initial output file
        self._create_initial_output_file()
    
    def _create_initial_output_file(self):
        """Create initial output file by copying the original - always start fresh"""
        source_file = os.path.join(self.record_dir, f"{self.case_number}.py")
        if os.path.exists(source_file):
            shutil.copy2(source_file, self.output_file)
            print(f"Created initial output file: {self.output_file}")
    
    def _initialize_tracking(self):
        """Initialize tracking for the specified case number"""
        record_file = os.path.join(self.record_dir, f"{self.case_number}.py")
        if os.path.exists(record_file):
            self.last_known_actions[self.case_number] = self._get_playwright_actions(record_file)
            self.last_known_assertions[self.case_number] = self._get_assertions(record_file)
        latest_session = self._get_latest_session()
        if latest_session:
            self.last_known_snapshots[self.case_number] = self._get_snapshot_files(latest_session)
    
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.py'):
            file_case_number = os.path.basename(event.src_path).replace('.py', '')
            if file_case_number == self.case_number:
                self._check_changes()
    
    def _get_playwright_actions(self, file_path):
        """Get all Playwright actions (page.*) from the file"""
        with open(file_path, 'r') as f:
            content = f.read()
        return re.findall(r'^\s*page\..*$', content, re.MULTILINE)

    def _get_assertions(self, file_path):
        """Get all assertions (expect.*) from the file"""
        with open(file_path, 'r') as f:
            content = f.read()
        return re.findall(r'^\s*expect\(.*$', content, re.MULTILINE)

    def _get_latest_session(self):
        """Get the latest session directory for the case"""
        case_dir = os.path.join(self.snapshot_dir, self.case_number)
        if not os.path.exists(case_dir):
            return None
        
        session_dirs = glob.glob(os.path.join(case_dir, "session-*"))
        if not session_dirs:
            return None
            
        return max(session_dirs, key=os.path.getctime)
    
    def _get_snapshot_files(self, session_dir):
        """Get all snapshot files in a session directory"""
        if not session_dir or not os.path.exists(session_dir):
            return []
            
        snapshot_files = []
        for root, _, files in os.walk(session_dir):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), session_dir)
                snapshot_files.append(rel_path)
        return sorted(snapshot_files)
    
    def _check_changes(self):
        source_file = os.path.join(self.record_dir, f"{self.case_number}.py")
        if not os.path.exists(source_file):
            print(f"Source file not found: {source_file}")
            return
        
        # Get current actions and assertions
        current_actions = self._get_playwright_actions(source_file)
        current_assertions = self._get_assertions(source_file)
        last_actions = self.last_known_actions.get(self.case_number, [])
        last_assertions = self.last_known_assertions.get(self.case_number, [])
        
        # Get new actions and assertions since last check
        new_actions = current_actions[len(last_actions):]
        new_assertions = current_assertions[len(last_assertions):]
        
        if new_actions:
            # Wait up to 10 seconds for new snapshots
            max_retries = 10
            retry_interval = 1.5  # seconds
            
            for retry in range(max_retries):
                # Get current snapshots
                latest_session = self._get_latest_session()
                if not latest_session:
                    print(f"Waiting for snapshot directory... (attempt {retry + 1}/{max_retries})")
                    time.sleep(retry_interval)
                    continue
                    
                current_snapshots = self._get_snapshot_files(latest_session)
                last_snapshots = self.last_known_snapshots.get(self.case_number, [])
                
                new_snapshots = [snap for snap in current_snapshots if snap not in last_snapshots]
                
                if new_snapshots:
                    # Write new actions and assertions with snapshots
                    self._update_output_file(new_actions, [], new_snapshots)
                    self.last_known_snapshots[self.case_number] = current_snapshots
                    self.last_known_actions[self.case_number] = current_actions
                    print(f"Successfully captured new action and {len(new_snapshots)} snapshots")
                    return
                
                print(f"Waiting for new snapshots... (attempt {retry + 1}/{max_retries})")
                time.sleep(retry_interval)
            print("Timeout waiting for snapshots. Will try again on next file change.")
        
        self.last_known_actions[self.case_number] = current_actions
            
        
        if new_assertions:
            self._update_output_file([], new_assertions, [])
        self.last_known_assertions[self.case_number] = current_assertions

    def _update_output_file(self, new_actions, new_assertions, new_snapshots):
        """
        Update the output file with new snapshots after each action/assertion.
        1. append new actions and assertions
        2. append new snapshots
        """
        # Write new actions and assertions to output file
        for action in new_actions:
            with open(self.output_file, 'a') as f:
                f.writelines(f"{action}\n")
                # Create comment block for new snapshots
            snapshot_comments = []
            for snapshot in new_snapshots:
                snapshot_comments.append(f"    # - {snapshot}\n")
            snapshot_comments.append("\n")

            # Write to output file
            with open(self.output_file, 'a') as f:
                f.writelines(snapshot_comments)

        for assertion in new_assertions:
            with open(self.output_file, 'a') as f:
                f.writelines(f"{assertion}\n")
        
        print(f"Updated output file for case {self.case_number} with new snapshots")

def start_monitoring(workspace_root, case_number):
    """
    Start monitoring a specific test case for Playwright actions and snapshots.
    
    Args:
        workspace_root (str): Path to the project root directory
        case_number (str): The test case number to monitor
    """
    record_dir = os.path.join(workspace_root, "input", "records")
    snapshot_dir = os.path.join(workspace_root, "input", "snapshot")
    
    # Validate directories exist
    if not os.path.exists(record_dir):
        print(f"Error: Records directory not found: {record_dir}")
        return
    if not os.path.exists(snapshot_dir):
        print(f"Error: Snapshot directory not found: {snapshot_dir}")
        return
        
    # Validate source file exists
    source_file = os.path.join(record_dir, f"{case_number}.py")
    if not os.path.exists(source_file):
        print(f"Error: Source file not found: {source_file}")
        return
    
    event_handler = PlaywrightSnapshotHandler(record_dir, snapshot_dir, case_number)
    observer = Observer()
    
    observer.schedule(event_handler, record_dir, recursive=False)
    observer.schedule(event_handler, snapshot_dir, recursive=True)
    
    observer.start()
    print(f"Started monitoring case {case_number}")
    print(f"Source file: {source_file}")
    print(f"Output file: {os.path.join(record_dir, f'{case_number}_with_snapshots.py')}")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print(f"\nStopped monitoring case {case_number}")
    
    observer.join()

def main():
    """Main entry point for the script."""
    if len(sys.argv) != 2:
        print("Usage: python monitor_snapshots.py <case_number>")
        print("Example: python monitor_snapshots.py 3574602")
        sys.exit(1)
        
    # Get the project root directory
    workspace_root = Path(__file__).parent.resolve()
    case_number = sys.argv[1]
    
    # Start monitoring
    start_monitoring(workspace_root, case_number)

if __name__ == "__main__":
    main() 