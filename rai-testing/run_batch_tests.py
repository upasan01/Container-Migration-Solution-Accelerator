#!/usr/bin/env python3
"""
RAI Testing Framework - Batch CSV Processing

Run RAI tests from a CSV file using the core testing library.
Provides rich console interface for progress tracking and result reporting.

Usage:
    python run_batch_tests.py --csv-file test_cases.csv
    python run_batch_tests.py --csv-file test_cases.csv --debug
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

    async def run_tests(self, csv_file: str, no_wait: bool = False, include_full_response: bool = False, debug: bool = False) -> Dict[str, Any]:
        """
        Run RAI tests from CSV file using core testing library
        
        Args:
            csv_file: Path to CSV file with test cases
            no_wait: Do not wait for all tests to complete. This will queue all tests to run. Execute "update_batch_results.py" after all tests complete to update the CSV.
            include_full_response: Whether to include full error response in results
            debug: Enable debug logging
        
        Returns:
            Dictionary containing test results and summary
        """
        today = datetime.now().strftime("%Y-%m-%d")
        log_path = Path(__file__).parent / "logs" / f"rai_csv_test_{today}_{str(uuid.uuid4())[:8]}.log"
        setup_logging(debug=debug, log_to_console=False, log_to_file=str(log_path))
            
        try:
            start_time = asyncio.get_event_loop().time()

            # Load test cases from CSV
            self.test_manager = TestManager(csv_file)
            test_cases = self.test_manager.load_test_cases()
            
            self.console.print(f"✅ CSV file loaded: {len(test_cases)} test cases found.")
                
            # Display test configuration
            estimated_minutes = len(test_cases) * (0.1 if no_wait else 1.2)
            estimated_time = f"{int(estimated_minutes // 60)}h {int(estimated_minutes % 60)}m" if estimated_minutes >= 60 else f"{int(estimated_minutes)}m"
            
            config_table = Table()
            config_table.add_column("Setting", style="cyan")
            config_table.add_column("Value", style="white")
            config_table.add_row("CSV File", str(csv_file))
            config_table.add_row("Wait for each result?", "No" if no_wait else "Yes")
            config_table.add_row("Test Count", str(len(test_cases)))
            config_table.add_row("Estimated Time to Complete", estimated_time)
            config_table.add_row("Timeout per Test", str(self.config.TEST_TIMEOUT_MINUTES))
            
            self.console.print(Panel(config_table, title="🧪 Test Configuration"))
            
            # Run tests using core testing library
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description} ({task.completed}/{task.total}) ..."),
                BarColumn(),
                TaskProgressColumn(text_format="[progress.percentage]{task.percentage:>3.0f}%"),
                console=self.console
            ) as progress:
                task = progress.add_task("Running tests", total=len(test_cases))
                
                # Use the core testing library to run all tests
                results = await run_batch_tests(
                    test_cases=test_cases,
                    config=self.config,
                    progress_callback=lambda: progress.advance(task, 1)
                )
            
            # Update CSV with results
            await self._update_csv_with_results(results, file_path=csv_file, include_full_response=include_full_response)
            
            elapsed_time = asyncio.get_event_loop().time() - start_time

            # Generate summary
            summary = self._generate_summary(results, test_cases, total_time=elapsed_time)
            
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

    async def _update_csv_with_results(self, results: List[Dict[str, Any]], file_path: str, include_full_response: bool) -> None:
        """Update CSV file with test results"""
        for result in results:
            self.test_manager.update_test_result(
                row_id=result["row_id"],
                process_id=result.get("process_id"),
                blob_path=result.get("blob_path"),
                result=result.get("test_result", "error"),
                reason=result.get("error_reason", ""),
                error_message=result.get("error_message", "")
            )
        
        self.test_manager.save_updated_csv(output_path=file_path,include_full_response=include_full_response)
        
    def _generate_summary(self, results: List[Dict[str, Any]], test_cases: List[TestCase], total_time: float) -> Dict[str, Any]:
        """Generate test results summary"""
        passed = sum(1 for r in results if r.get("test_result") == "passed")
        failed = sum(1 for r in results if r.get("test_result") == "failed")
        errors = sum(1 for r in results if r.get("test_result") in ["error", "timeout"])
        
        # Calculate average execution time
        execution_times = [r.get("execution_time", 0) for r in results if r.get("execution_time")]
        avg_time = sum(execution_times) / len(execution_times) if execution_times else 0
        avg_time_formatted = f"{avg_time:.1f}s" if avg_time > 0 else "N/A"
        
        # Format total time
        total_minutes = int(total_time // 60)
        if total_minutes >= 60:
            hours = total_minutes // 60
            minutes = total_minutes % 60
            total_time_formatted = f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
        else:
            total_time_formatted = f"{total_minutes}m"
        
        return {
            "success": True,
            "total_tests": len(test_cases),
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "pass_rate": f"{(passed / len(test_cases) * 100):.1f}%",
            "avg_time_per_test": avg_time_formatted,
            "total_execution_time": total_time_formatted,
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
        results_table.add_row("Execution Time", summary["total_execution_time"])
        results_table.add_row("Avg Time Per Test", summary["avg_time_per_test"])
        
        
        self.console.print(Panel(results_table, title="📊 Test Results"))
        self.console.print(f"✅ Results saved to: {summary['csv_file']}")


@click.command()
@click.option('--csv-file', required=True, help='Path to CSV file containing test cases.')
@click.option('--no-wait', is_flag=True, help='Do not wait for all tests to complete. This will queue all tests to run. Execute "update_batch_results.py" after all tests complete to update the CSV with the results.')
@click.option('--include-full-response', is_flag=True, help='Include full error response in CSV results.')
@click.option('--debug', is_flag=True, help='Enable debug logging')
def main(csv_file: str, no_wait: bool, include_full_response: bool, debug: bool):
    """Run RAI tests from CSV file"""
    asyncio.run(run_async_main(csv_file, no_wait, include_full_response, debug))


async def run_async_main(csv_file: str, no_wait: bool, include_full_response: bool, debug: bool):
    """Async main function for running RAI tests"""
    orchestrator = RAITestOrchestrator()
    result = await orchestrator.run_tests(csv_file, no_wait, include_full_response, debug)

    # Exit with appropriate code
    if result.get("success", False):
        exit(0)
    else:
        exit(1)


if __name__ == "__main__":
    main()
