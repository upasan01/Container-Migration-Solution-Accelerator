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
from utils.environment_validator import validate_environment


async def main():
    """Main entry point for single test execution"""
    
    parser = argparse.ArgumentParser(description='Run a single RAI test')
    parser.add_argument('test_content', help='The test content to embed in YAML.')
    parser.add_argument('--timeout', type=int, default=60, help='Timeout in minutes (default: 60).')
    parser.add_argument('--resource-type', default='pod', help='Kubernetes resource type (default: pod).')
    parser.add_argument('--include-full-response', action='store_true', help='Whether to include the full "error response" from the application in the results (default: False).')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging.')
    
    args = parser.parse_args()
    
    # Validate environment configuration before proceeding
    if not validate_environment():
        sys.exit(1)
    
    today = datetime.now().strftime("%Y-%m-%d")
    log_path = Path(__file__).parent / "logs" / f"rai_single_tests_{today}.log"
    setup_logging(debug=args.debug, log_to_console=True, log_to_file=str(log_path))
    
    try:
        logger = logging.getLogger("main")

        # Run the test using core testing library
        result = await run_single_test(
            test_content=args.test_content,
            timeout_minutes=args.timeout,
            resource_type=args.resource_type
        )
        
        # Display prominent test result before JSON output
        test_result = result.get("test_result", "unknown").upper()
        process_id = result.get("process_id", "N/A")
        error_reason = result.get("error_reason", "")
        
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
        
        # log off raw results
        logger.info(f"Result: {test_result} | Reason: {error_reason} | Process ID: {process_id}")

        # Print pretty results 
        # Includes status line to stderr so it doesn't interfere with JSON parsing
        print(f"\n{status_line}", file=sys.stderr)
        print(f"Process ID: {process_id}", file=sys.stderr)
        
        if error_reason and error_reason.strip():
            print(f"Error Reason: {error_reason}", file=sys.stderr)

        if args.include_full_response:
            print(f"Full response:\n{result.get("error_message", "")}")
        
        print("-" * 50, file=sys.stderr)
        
        if args.debug:
            logger.info(f"\n{json.dumps(result, indent=2)}")
            print("-" * 50, file=sys.stderr)
            
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
