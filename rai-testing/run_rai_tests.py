#!/usr/bin/env python3
"""
RAI Testing Framework - Batch CSV Processing

Run RAI tests from a CSV file using the core testing library.
Provides rich console interface for progress tracking and result reporting.

Usage:
    python run_rai_tests.py --csv-file test_cases.csv
    python run_rai_tests.py --csv-file test_cases.csv --test-count 10
    python run_rai_tests.py --csv-file test_cases.csv --debug
"""

import asyncio
import logging
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel

from config import RAITestConfig
from utils.test_manager import TestManager, TestCase
from utils.core_testing import run_batch_tests
from utils.logging_config import setup_logging


class RAITestOrchestrator:
    """Main orchestrator for RAI testing workflow using core testing library"""
    
    def __init__(self, config: RAITestConfig = None):
        self.config = config or RAITestConfig()
        self.console = Console()
        self.logger = logging.getLogger(__name__)
        
        # Test manager will be initialized when CSV file is provided
        self.test_manager: Optional[TestManager] = None

    async def run_tests(self, csv_file: str, test_count: Optional[int] = None, debug: bool = False) -> Dict[str, Any]:
        """
        Run RAI tests from CSV file using core testing library
        
        Args:
            csv_file: Path to CSV file with test cases
            test_count: Optional limit on number of tests to run
            debug: Enable debug logging
        
        Returns:
            Dictionary containing test results and summary
        """
        setup_logging(debug=debug, log_to_console=False, log_to_file=f"/logs/rai_csv_test_{str(uuid.uuid4())[:8]}.log")
            
        try:
            # Load test cases from CSV
            self.test_manager = TestManager(csv_file)
            test_cases = self.test_manager.load_test_cases()
            
            self.console.print(f"✅ CSV file loaded: {len(test_cases)} test cases found")
            
            # Limit test count if specified
            if test_count and test_count < len(test_cases):
                test_cases = test_cases[:test_count]
                
            # Display test configuration
            config_table = Table()
            config_table.add_column("Setting", style="cyan")
            config_table.add_column("Value", style="white")
            config_table.add_row("CSV File", str(csv_file))
            config_table.add_row("Test Count", str(len(test_cases)))
            config_table.add_row("Timeout", f"{self.config.TEST_TIMEOUT_MINUTES} minutes")
            
            self.console.print(Panel(config_table, title="🧪 Test Configuration"))
            
            # Run tests using core testing library
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=self.console
            ) as progress:
                task = progress.add_task("Running tests...", total=len(test_cases))
                
                # Use the core testing library to run all tests
                results = await run_batch_tests(
                    test_cases=test_cases,
                    config=self.config,
                    progress_callback=lambda: progress.advance(task, 1)
                )
            
            # Update CSV with results
            await self._update_csv_with_results(results, file_path=csv_file)
            
            # Generate summary
            summary = self._generate_summary(results, test_cases)
            
            # Display results
            self._display_results(summary)
            
            return summary
            
        except Exception as e:
            error_msg = f"Test execution failed: {e}"
            self.console.print(f"❌ {error_msg}", style="red")
            return {
                "success": False,
                "error": error_msg,
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "errors": 1
            }

    async def _update_csv_with_results(self, results: List[Dict[str, Any]], file_path: str) -> None:
        """Update CSV file with test results"""
        for result in results:
            self.test_manager.update_test_result(
                row_id=result["row_id"],
                process_id=result.get("process_id"),
                blob_path=result.get("blob_path"),
                result=result.get("test_result", "error"),
                reason=result.get("error_reason", "")
            )
        
        # Save updated CSV
        self.test_manager.save_updated_csv(output_path=file_path)
        
    def _generate_summary(self, results: List[Dict[str, Any]], test_cases: List[TestCase]) -> Dict[str, Any]:
        """Generate test results summary"""
        passed = sum(1 for r in results if r.get("test_result") == "passed")
        failed = sum(1 for r in results if r.get("test_result") == "failed")
        errors = sum(1 for r in results if r.get("test_result") in ["error", "timeout"])
        
        return {
            "success": True,
            "total_tests": len(test_cases),
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "pass_rate": f"{(passed / len(test_cases) * 100):.1f}%",
            "results": results,
            "csv_file": str(self.test_manager.csv_file_path),
            "timestamp": datetime.now().isoformat()
        }
    
    def _display_results(self, summary: Dict[str, Any]) -> None:
        """Display test results in a formatted table"""
        results_table = Table()
        results_table.add_column("Metric", style="cyan")
        results_table.add_column("Value", style="white")
        
        results_table.add_row("Total Tests", str(summary["total_tests"]))
        results_table.add_row("Passed", f"[green]{summary['passed']}[/green]")
        results_table.add_row("Failed", f"[red]{summary['failed']}[/red]")
        results_table.add_row("Errors", f"[yellow]{summary['errors']}[/yellow]")
        results_table.add_row("Pass Rate", summary["pass_rate"])
        
        self.console.print(Panel(results_table, title="📊 Test Results"))
        self.console.print(f"✅ Results saved to: {summary['csv_file']}")


@click.command()
@click.option('--csv-file', required=True, help='Path to CSV file containing test cases')
@click.option('--test-count', type=int, help='Maximum number of tests to run')
@click.option('--debug', is_flag=True, help='Enable debug logging')
def main(csv_file: str, test_count: Optional[int], debug: bool):
    """Run RAI tests from CSV file"""
    asyncio.run(run_async_main(csv_file, test_count, debug))


async def run_async_main(csv_file: str, test_count: Optional[int], debug: bool):
    """Async main function for running RAI tests"""
    orchestrator = RAITestOrchestrator()
    result = await orchestrator.run_tests(csv_file, test_count, debug)
    
    # Exit with appropriate code
    if result.get("success", False):
        exit(0)
    else:
        exit(1)


if __name__ == "__main__":
    main()
