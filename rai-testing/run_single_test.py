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


async def main():
    """Main entry point for single test execution"""
    
    parser = argparse.ArgumentParser(description='Run a single RAI test')
    parser.add_argument('test_content', help='The test content to embed in YAML')
    parser.add_argument('--timeout', type=int, default=60, help='Timeout in minutes (default: 60)')
    parser.add_argument('--resource-type', default='pod', help='Kubernetes resource type (default: pod)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--pretty', action='store_true', help='Pretty print JSON output')
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format='%(levelname)s: %(message)s',
        handlers=[logging.StreamHandler()]
    )
    
    # Reduce Azure SDK logging noise
    logging.getLogger('azure').setLevel(logging.ERROR)
    logging.getLogger('urllib3').setLevel(logging.ERROR)
    logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.ERROR)
    
    try:
        # Run the test using core testing library
        result = await run_single_test(
            test_content=args.test_content,
            timeout_minutes=args.timeout,
            resource_type=args.resource_type
        )
        
        # Convert result to expected format
        output = {
            "process_id": result["process_id"],
            "blob_path": result["blob_path"], 
            "result": result["result"],
            "details": result.get("details", {})
        }
        
        # Add additional information to details
        output["details"].update({
            "completed": result.get("completed", False),
            "safety_triggered": result.get("safety_triggered", False),
            "execution_time": result.get("execution_time"),
            "error_message": result.get("error_message")
        })
        
        # Output results as JSON
        if args.pretty:
            print(json.dumps(output, indent=2))
        else:
            print(json.dumps(output))
            
        # Exit with appropriate code
        if result["result"] in ["passed", "failed"]:
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
