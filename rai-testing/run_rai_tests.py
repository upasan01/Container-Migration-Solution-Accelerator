#!/usr/bin/env python3
"""
RAI Testing Framework - Main Execution Script

This script orchestrates the complete RAI testing workflow:
1. Generates harmful content test files
2. Uploads files to Azure Blob Storage
3. Sends queue messages to trigger processing
4. Monitors agent responses
5. Generates compliance reports

Usage:
    python run_rai_tests.py [options]
    
Examples:
    # Run all tests
    python run_rai_tests.py
    
    # Run specific category  
    python run_rai_tests.py --category content-safety
    
    # Run limited number of tests
    python run_rai_tests.py --test-count 10
    
    # Generate report only
    python run_rai_tests.py --report-only
"""

import os
import sys
import json
import uuid
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TaskID
from rich.panel import Panel
from rich.text import Text

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Import framework components
from config import RAITestConfig, TEST_CATEGORIES
from test_cases.harmful_content import HarmfulContentGenerator
from test_cases.test_scenarios import TestScenarioGenerator, TestStatus
from utils.yaml_generator import YamlFileGenerator
from utils.blob_helper import BlobStorageTestHelper
from utils.queue_helper import QueueTestHelper
from utils.monitoring import TestMonitor


class RAITestOrchestrator:
    """Main orchestrator for RAI testing workflow"""
    
    def __init__(self, config: RAITestConfig = None):
        self.config = config or RAITestConfig()
        self.console = Console()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.yaml_generator = YamlFileGenerator()
        self.blob_helper = BlobStorageTestHelper(self.config)
        self.queue_helper = QueueTestHelper(self.config)
        self.monitor = TestMonitor(self.config)
        
        # Test state
        self.test_executions = []
        self.temp_files = []
    
    def setup_logging(self, debug: bool = False) -> None:
        """Configure logging for the test framework"""
        
        log_level = logging.DEBUG if debug else logging.INFO
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(f'rai_tests_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
            ]
        )
        
        # Reduce Azure SDK logging noise
        logging.getLogger('azure').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    def validate_environment(self) -> bool:
        """Validate that the testing environment is properly configured"""
        
        self.console.print("[bold blue]Validating RAI testing environment...[/bold blue]")
        
        try:
            # Validate configuration
            self.config.validate_config()
            self.console.print("✅ Configuration validated")
            
            # Check Azure Storage connectivity
            if not self.blob_helper.check_container_exists():
                self.console.print("⚠️  Blob container does not exist, will create")
                if not self.blob_helper.ensure_container_exists():
                    raise RuntimeError("Failed to create blob container")
            self.console.print("✅ Blob storage accessible")
            
            # Check queue connectivity
            queue_status = self.queue_helper.check_queues_exist()
            if not all(queue_status.values()):
                self.console.print("⚠️  Queues do not exist, will create")
                if not all(self.queue_helper.ensure_queues_exist().values()):
                    raise RuntimeError("Failed to create queues")
            self.console.print("✅ Storage queues accessible")
            
            return True
            
        except Exception as e:
            self.console.print(f"❌ Environment validation failed: {e}")
            return False
    
    async def run_rai_tests(
        self,
        category: Optional[str] = None,
        test_count: Optional[int] = None,
        severity: Optional[str] = None,
        timeout_minutes: int = None
    ) -> Dict[str, Any]:
        """Run RAI tests with specified parameters"""
        
        timeout_minutes = timeout_minutes or self.config.MAX_WAIT_TIME_MINUTES
        test_count = test_count or self.config.DEFAULT_TEST_COUNT
        
        self.console.print(Panel(
            f"[bold green]Starting RAI Testing Session[/bold green]\\n"
            f"Category: {category or 'All'}\\n"
            f"Max Tests: {test_count}\\n"
            f"Severity: {severity or 'All'}\\n"
            f"Timeout: {timeout_minutes} minutes",
            title="RAI Test Configuration"
        ))
        
        try:
            # Get test cases
            test_cases = self._select_test_cases(category, severity, test_count)
            
            if not test_cases:
                self.console.print("[red]No test cases selected![/red]")
                return {"error": "No test cases found"}
            
            self.console.print(f"Selected {len(test_cases)} test cases for execution")
            
            # Execute tests with progress tracking
            with Progress() as progress:
                task = progress.add_task("Running RAI Tests...", total=len(test_cases))
                
                for i, test_case in enumerate(test_cases):
                    try:
                        await self._execute_single_test(test_case, timeout_minutes)
                        progress.update(task, advance=1)
                        
                    except Exception as e:
                        self.logger.error(f"Test {test_case.id} failed: {e}")
                        progress.update(task, advance=1)
            
            # Generate results
            results = await self._finalize_test_session()
            
            return results
            
        except Exception as e:
            self.logger.error(f"RAI test session failed: {e}")
            return {"error": str(e)}
        
        finally:
            # Cleanup
            self._cleanup_temp_files()
    
    def _select_test_cases(
        self,
        category: Optional[str],
        severity: Optional[str],
        max_count: int
    ) -> List:
        """Select test cases based on criteria"""
        
        # Get all test cases
        all_cases = HarmfulContentGenerator.get_all_test_cases()
        
        # Filter by category
        if category:
            all_cases = [case for case in all_cases if case.category == category]
        
        # Filter by severity  
        if severity:
            all_cases = [case for case in all_cases if case.severity == severity]
        
        # Limit count
        if len(all_cases) > max_count:
            all_cases = all_cases[:max_count]
        
        return all_cases
    
    async def _execute_single_test(self, test_case, timeout_minutes: int) -> None:
        """Execute a single RAI test case"""
        
        execution_id = str(uuid.uuid4())
        process_id = str(uuid.uuid4())
        
        self.console.print(f"\\n[bold cyan]Executing Test: {test_case.id}[/bold cyan]")
        self.console.print(f"Description: {test_case.description}")
        self.console.print(f"Process ID: {process_id}")
        
        try:
            # Start monitoring
            execution = self.monitor.start_monitoring_test(
                execution_id=execution_id,
                scenario_id=f"auto-{test_case.category}",
                test_case_id=test_case.id,
                process_id=process_id
            )
            
            # Generate test file
            temp_dir = Path(f"temp_test_files_{execution_id}")
            temp_dir.mkdir(exist_ok=True)
            self.temp_files.append(temp_dir)
            
            yaml_file = self.yaml_generator.generate_yaml_file(
                test_case=test_case,
                resource_type="pod",  # Default to pod
                output_dir=str(temp_dir)
            )
            
            self.console.print(f"✅ Generated test file: {Path(yaml_file).name}")
            
            # Create blob folder and upload file
            self.blob_helper.create_test_folder(process_id)
            
            uploaded_blob = self.blob_helper.upload_test_file(
                process_id=process_id,
                file_path=yaml_file,
                folder_type="source"
            )
            
            self.console.print(f"✅ Uploaded to blob: {uploaded_blob}")
            
            # Send queue message to trigger processing
            message_id = self.queue_helper.send_test_message(
                process_id=process_id,
                user_id="rai-test-framework",
                additional_data={
                    "test_case_id": test_case.id,
                    "test_category": test_case.category,
                    "execution_id": execution_id
                }
            )
            
            execution.queue_message_id = message_id
            self.console.print(f"✅ Sent queue message: {message_id}")
            
            # Monitor execution
            self.console.print(f"⏳ Monitoring test execution (timeout: {timeout_minutes}m)...")
            
            completed_execution = self.monitor.monitor_test_execution(
                execution_id, 
                timeout_minutes=timeout_minutes
            )
            
            # Report results
            self._report_test_result(completed_execution)
            self.test_executions.append(completed_execution)
            
        except Exception as e:
            self.console.print(f"❌ Test execution failed: {e}")
            self.monitor.update_test_status(execution_id, TestStatus.FAILED, str(e))
    
    def _report_test_result(self, execution) -> None:
        """Report the result of a single test execution"""
        
        status_colors = {
            TestStatus.COMPLETED: "green",
            TestStatus.FAILED: "red", 
            TestStatus.TIMEOUT: "yellow",
            TestStatus.SAFETY_TRIGGERED: "blue"
        }
        
        color = status_colors.get(execution.status, "white")
        
        self.console.print(f"\\n[bold {color}]Test Result: {execution.status.value.upper()}[/bold {color}]")
        self.console.print(f"Safety Triggers: {len(execution.safety_triggers)}")
        self.console.print(f"Agent Responses: {len(execution.agent_responses)}")
        self.console.print(f"Error Messages: {len(execution.error_messages)}")
        
        if execution.safety_triggers:
            self.console.print("[green]✅ Safety measures activated[/green]")
            for trigger in execution.safety_triggers[:3]:  # Show first 3
                self.console.print(f"  - Pattern: {trigger['pattern']}")
        else:
            self.console.print("[yellow]⚠️  No safety measures detected[/yellow]")
    
    async def _finalize_test_session(self) -> Dict[str, Any]:
        """Finalize test session and generate report"""
        
        self.console.print("\\n[bold blue]Generating final report...[/bold blue]")
        
        # Generate comprehensive report
        report = self.monitor.generate_test_report(self.test_executions)
        
        # Save detailed results
        results_dir = Path("results") / f"rai_test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        detailed_files = self.monitor.export_detailed_results(
            self.test_executions,
            str(results_dir)
        )
        
        # Display summary
        self._display_test_summary(report)
        
        return {
            "summary": report,
            "detailed_files": detailed_files,
            "test_count": len(self.test_executions)
        }
    
    def _display_test_summary(self, report: Dict[str, Any]) -> None:
        """Display test summary in a formatted table"""
        
        # Summary table
        table = Table(title="RAI Test Summary", show_header=True)
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")
        
        summary = report["summary"]
        table.add_row("Total Tests", str(summary["total_tests"]))
        table.add_row("Completed", str(summary["completed"]))
        table.add_row("Failed", str(summary["failed"]))
        table.add_row("Timed Out", str(summary["timed_out"]))
        table.add_row("Safety Triggered", str(summary["safety_triggered"]))
        table.add_row("Total Safety Triggers", str(summary["total_safety_triggers"]))
        
        effectiveness = report["safety_analysis"]["response_effectiveness"]
        table.add_row("Safety Effectiveness", f"{effectiveness:.1%}")
        
        compliance = report["compliance_status"]
        compliance_colors = {
            "HIGH_COMPLIANCE": "green",
            "MEDIUM_COMPLIANCE": "yellow", 
            "LOW_COMPLIANCE": "red"
        }
        color = compliance_colors.get(compliance, "white")
        table.add_row("Compliance Status", f"[{color}]{compliance}[/{color}]")
        
        self.console.print(table)
        
        # Recommendations
        if report["safety_analysis"]["recommendations"]:
            self.console.print("\\n[bold yellow]Recommendations:[/bold yellow]")
            for rec in report["safety_analysis"]["recommendations"]:
                self.console.print(f"• {rec}")
    
    def _cleanup_temp_files(self) -> None:
        """Clean up temporary files"""
        
        for temp_path in self.temp_files:
            try:
                if temp_path.exists():
                    for file in temp_path.rglob("*"):
                        if file.is_file():
                            file.unlink()
                    temp_path.rmdir()
            except Exception as e:
                self.logger.warning(f"Failed to cleanup {temp_path}: {e}")


# CLI Interface
@click.command()
@click.option('--category', 
              type=click.Choice(['content-safety', 'security', 'legal-compliance', 'operational-safety']),
              help='Test category to run')
@click.option('--test-count', type=int, 
              help=f'Maximum number of tests to run (default: {RAITestConfig.DEFAULT_TEST_COUNT})')
@click.option('--severity',
              type=click.Choice(['critical', 'high', 'medium', 'low']),
              help='Filter tests by severity level')
@click.option('--timeout', type=int,
              help=f'Test timeout in minutes (default: {RAITestConfig.MAX_WAIT_TIME_MINUTES})')
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.option('--report-only', is_flag=True, help='Generate report from existing results')
@click.option('--cleanup', is_flag=True, help='Clean up test data after execution')
def main(category, test_count, severity, timeout, debug, report_only, cleanup):
    """
    RAI Testing Framework - Test AI agents for responsible behavior
    
    This tool tests your multi-agent system's response to harmful content
    by creating test scenarios and monitoring safety measure activation.
    """
    
    # Initialize orchestrator
    orchestrator = RAITestOrchestrator()
    orchestrator.setup_logging(debug)
    
    try:
        # Validate environment
        if not report_only:
            if not orchestrator.validate_environment():
                orchestrator.console.print("[red]Environment validation failed. Exiting.[/red]")
                sys.exit(1)
        
        # Run tests or generate report
        if report_only:
            # TODO: Implement report-only mode
            orchestrator.console.print("[yellow]Report-only mode not yet implemented[/yellow]")
            sys.exit(1)
        else:
            # Run RAI tests
            results = asyncio.run(orchestrator.run_rai_tests(
                category=category,
                test_count=test_count,
                severity=severity, 
                timeout_minutes=timeout
            ))
            
            if "error" in results:
                orchestrator.console.print(f"[red]Test execution failed: {results['error']}[/red]")
                sys.exit(1)
        
        orchestrator.console.print("\\n[bold green]RAI testing completed successfully![/bold green]")
        
    except KeyboardInterrupt:
        orchestrator.console.print("\\n[yellow]Test execution interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        orchestrator.console.print(f"\\n[red]Unexpected error: {e}[/red]")
        if debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
