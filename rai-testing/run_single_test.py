#!/usr/bin/env python3
"""
RAI Single Test Script

Runs a single RAI test with provided test content and returns the results.

Usage:
    python run_single_test.py "harmful test content here"
    
Output (JSON):
    {
        "process_id": "uuid-string",
        "blob_path": "path/to/uploaded/file", 
        "result": "passed|failed|error|timeout",
        "details": {...}
    }
"""

import os
import sys
import json
import uuid
import asyncio
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import argparse

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Import framework components
from config import RAITestConfig
from utils.core_testing import run_single_test
from utils.logging_config import setup_logging


async def main():
    """Main entry point for single test execution"""
    
    parser = argparse.ArgumentParser(description='Run a single RAI test')
    parser.add_argument('test_content', help='The test content to embed in YAML')
    parser.add_argument('--timeout', type=int, default=60, help='Timeout in minutes (default: 60)')
    parser.add_argument('--resource-type', default='pod', help='Kubernetes resource type (default: pod)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Setup centralized logging
    setup_logging(debug=args.debug)
    
    try:
        # Run the test using core testing library
        result = await run_single_test(
            test_content=args.test_content,
            timeout_minutes=args.timeout,
            resource_type=args.resource_type
        )
        
        # Display prominent test result before JSON output
        test_result = result.get("test_result", "unknown").upper()
        
        if test_result == "PASSED":
            status_line = "🟢 TEST PASSED ✅"
        elif test_result == "FAILED":
            status_line = "🔴 TEST FAILED ❌"
        elif test_result == "TIMEOUT":
            status_line = "🟡 TEST TIMEOUT ⏰"
        elif test_result == "ERROR":
            status_line = "🟠 TEST ERROR ⚠️"
        else:
            status_line = f"🔵 TEST STATUS: {test_result}"
        
        # Print status line to stderr so it doesn't interfere with JSON parsing
        print(f"\n{status_line}", file=sys.stderr)
        print(f"Process ID: {result.get('process_id', 'N/A')}", file=sys.stderr)
        
        error_reason = result.get("error_reason", "")
        if error_reason and error_reason.strip():
            print(f"Error Reason: {error_reason}", file=sys.stderr)
        
        print("-" * 50, file=sys.stderr)
        
        if args.debug:
            print(json.dumps(result, indent=2))
            
        # Exit with appropriate code
        if test_result in ["PASSED", "FAILED"]:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print(json.dumps({"error": "Test interrupted by user"}))
        sys.exit(130)
    except Exception as e:
        print(json.dumps({"error": f"Unexpected error: {str(e)}"}))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
