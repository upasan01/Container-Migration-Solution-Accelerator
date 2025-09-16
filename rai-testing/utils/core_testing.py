"""
Core RAI testing utilities that can be shared between single tests and batch CSV processing.

This module contains the essential testing logic that can be reused across different
test execution modes.
"""

import os
import uuid
import asyncio
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from config import RAITestConfig
from utils.test_manager import TestCase
from utils.yaml_generator import YamlFileGenerator
from utils.blob_helper import BlobStorageTestHelper
from utils.queue_helper import QueueTestHelper
from utils.monitoring import TestMonitor


class CoreTestRunner:
    """Core test execution functionality shared between single and batch testing"""
    
    def __init__(self, config: RAITestConfig = None):
        self.config = config or RAITestConfig()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.yaml_generator = YamlFileGenerator()
        self.blob_helper = BlobStorageTestHelper(self.config)
        self.queue_helper = QueueTestHelper(self.config)
        self.monitor = TestMonitor(self.config)
        
        self.temp_files = []
    
    async def run_single_test_core(
        self,
        test_content: str,
        process_id: str = None,
        timeout_minutes: int = None,
        resource_type: str = "pod",
        row_id: int = 0
    ) -> Dict[str, Any]:
        """
        Core single test execution logic
        
        Args:
            test_content: The harmful/test content to embed in YAML
            process_id: Optional process ID (generated if not provided)
            timeout_minutes: How long to wait for test completion
            resource_type: Type of Kubernetes resource to generate
            row_id: Row identifier for tracking
            
        Returns:
            Dict with process_id, blob_path, result, and details
        """
        
        timeout_minutes = timeout_minutes or self.config.TEST_TIMEOUT_MINUTES
        process_id = process_id or str(uuid.uuid4())
        
        try:
            # Step 1: Create test case object
            test_case = TestCase(
                row_id=row_id,
                test_content=test_content,
                process_id=process_id
            )
            
            # Step 2: Generate YAML file
            temp_dir = Path(tempfile.gettempdir()) / "rai_test" / process_id
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            yaml_file_path = self.yaml_generator.generate_yaml_file(
                test_case=test_case,
                resource_type=resource_type,
                output_dir=str(temp_dir)
            )
            
            self.temp_files.append(yaml_file_path)
            self.logger.debug(f"Generated YAML file: {yaml_file_path}")
            
            # Step 3: Upload to blob storage
            blob_path = await self.blob_helper.upload_test_file(
                process_id=process_id,
                file_path=yaml_file_path,
                blob_name=f"rai-test-{row_id}-{process_id}.yaml"
            )
            
            self.logger.debug(f"Uploaded to blob: {blob_path}")
            
            # Step 4: Send queue message to trigger processing
            await self.queue_helper.send_test_message(process_id, time_to_live=60)
            self.logger.debug(f"Sent queue message for process_id: {process_id}")
            
            # Step 5: Monitor execution using Cosmos DB
            monitoring_result = await self.monitor.monitor_with_cosmos_db(
                process_id=process_id,
                timeout_minutes=timeout_minutes,
                polling_interval_seconds=self.config.COSMOS_POLLING_INTERVAL_SECONDS
            )
            
            # Step 6: Determine final result from Cosmos DB monitoring
            test_result = monitoring_result["result"]
            
            return {
                "process_id": process_id,
                "blob_path": blob_path,
                "result": test_result,
                "completed": monitoring_result["monitoring_status"] == "completed",
                "safety_triggered": False,  # Will be determined by agent analysis
                "execution_time": monitoring_result.get("elapsed_time_seconds"),
                "error_message": monitoring_result.get("error_message"),
                "details": {
                    "final_outcome": monitoring_result.get("final_outcome"),
                    "monitoring_status": monitoring_result["monitoring_status"],
                    "yaml_file": yaml_file_path,
                    "test_content_length": len(test_content),
                    "resource_type": resource_type,
                    "row_id": row_id
                }
            }
            
        except Exception as e:
            self.logger.exception(f"Error running test for process_id {process_id}: {e}")
            return {
                "process_id": process_id,
                "blob_path": "",
                "result": "error",
                "completed": False,
                "safety_triggered": False,
                "execution_time": None,
                "error_message": str(e),
                "details": {
                    "final_outcome": None,
                    "monitoring_status": "error",
                    "row_id": row_id,
                    "resource_type": resource_type
                }
            }
    
    async def run_batch_tests_core(
        self,
        test_cases: List[TestCase],
        timeout_minutes: int = None,
        resource_type: str = "pod",
        max_concurrent: int = None
    ) -> List[Dict[str, Any]]:
        """
        Core batch test execution logic
        
        Args:
            test_cases: List of test cases to run
            timeout_minutes: How long to wait for each test
            resource_type: Type of Kubernetes resource to generate
            max_concurrent: Maximum number of concurrent tests
            
        Returns:
            List of test results
        """
        
        timeout_minutes = timeout_minutes or self.config.TEST_TIMEOUT_MINUTES
        max_concurrent = max_concurrent or self.config.MAX_CONCURRENT_TESTS
        
        # Create semaphore to limit concurrent tests
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def run_single_with_semaphore(test_case: TestCase) -> Dict[str, Any]:
            async with semaphore:
                return await self.run_single_test_core(
                    test_content=test_case.test_content,
                    process_id=test_case.process_id,
                    timeout_minutes=timeout_minutes,
                    resource_type=resource_type,
                    row_id=test_case.row_id
                )
        
        # Run all tests concurrently with semaphore control
        tasks = [run_single_with_semaphore(test_case) for test_case in test_cases]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions that occurred
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Test {i} failed with exception: {result}")
                processed_results.append({
                    "process_id": test_cases[i].process_id or str(uuid.uuid4()),
                    "blob_path": "",
                    "result": "error",
                    "completed": False,
                    "error_message": str(result),
                    "details": {"row_id": test_cases[i].row_id}
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def cleanup_temp_files(self):
        """Clean up temporary files"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    self.logger.debug(f"Cleaned up temp file: {temp_file}")
            except Exception as e:
                self.logger.warning(f"Failed to clean up {temp_file}: {e}")
        
        # Clean up temp directories
        try:
            temp_base = Path(tempfile.gettempdir()) / "rai_test"
            if temp_base.exists():
                import shutil
                shutil.rmtree(temp_base, ignore_errors=True)
        except Exception as e:
            self.logger.warning(f"Failed to clean up temp directory: {e}")
        
        self.temp_files.clear()


# Convenience functions for easy import
async def run_single_test(
    test_content: str,
    timeout_minutes: int = None,
    resource_type: str = "pod",
    config: RAITestConfig = None
) -> Dict[str, Any]:
    """
    Convenience function to run a single test
    
    Args:
        test_content: The test content to run
        timeout_minutes: Test timeout
        resource_type: Kubernetes resource type
        config: Configuration object
        
    Returns:
        Test result dictionary
    """
    runner = CoreTestRunner(config)
    try:
        return await runner.run_single_test_core(
            test_content=test_content,
            timeout_minutes=timeout_minutes,
            resource_type=resource_type
        )
    finally:
        await runner.cleanup_temp_files()


async def run_batch_tests(
    test_cases: List[TestCase],
    timeout_minutes: int = None,
    resource_type: str = "pod",
    max_concurrent: int = None,
    config: RAITestConfig = None
) -> List[Dict[str, Any]]:
    """
    Convenience function to run multiple tests
    
    Args:
        test_cases: List of test cases
        timeout_minutes: Test timeout per test
        resource_type: Kubernetes resource type
        max_concurrent: Max concurrent tests
        config: Configuration object
        
    Returns:
        List of test results
    """
    runner = CoreTestRunner(config)
    try:
        return await runner.run_batch_tests_core(
            test_cases=test_cases,
            timeout_minutes=timeout_minutes,
            resource_type=resource_type,
            max_concurrent=max_concurrent
        )
    finally:
        await runner.cleanup_temp_files()
