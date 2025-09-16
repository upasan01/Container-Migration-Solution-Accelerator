"""
Test content management for RAI testing.
Handles reading test content from user-provided CSV files and updating results.
"""

import csv
import os
import uuid
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TestCase:
    """Represents a test case from CSV file"""
    row_id: int
    test_content: str
    process_id: Optional[str] = None
    blob_path: Optional[str] = None
    result: Optional[str] = None


class TestManager:
    """Manages test content from CSV files"""
    
    def __init__(self, csv_file_path: str):
        self.csv_file_path = Path(csv_file_path)
        self.test_cases = []
        self.fieldnames = []
        
        if not self.csv_file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_file_path}")
    
    def load_test_cases(self) -> List[TestCase]:
        """Load test cases from CSV file"""
        test_cases = []
        
        with open(self.csv_file_path, 'r', encoding='utf-8') as csvfile:
            # Detect delimiter
            sample = csvfile.read(1024)
            csvfile.seek(0)
            delimiter = ',' if ',' in sample else ';' if ';' in sample else '\t'
            
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            self.fieldnames = reader.fieldnames
            
            # Validate required columns
            required_columns = ['test_content']
            missing_columns = [col for col in required_columns if col not in self.fieldnames]
            if missing_columns:
                raise ValueError(f"CSV missing required columns: {missing_columns}")
            
            for row_id, row in enumerate(reader, 1):
                test_case = TestCase(
                    row_id=row_id,
                    test_content=row.get('test_content', '').strip(),
                    process_id=row.get('process_id', '').strip() or None,
                    blob_path=row.get('blob_path', '').strip() or None,
                    result=row.get('result', '').strip() or None
                )
                
                # Skip empty test_content rows
                if test_case.test_content:
                    test_cases.append(test_case)
        
        self.test_cases = test_cases
        return test_cases
    
    def update_test_result(
        self, 
        row_id: int, 
        process_id: str,
        blob_path: str,
        result: str
    ) -> None:
        """Update test result for a specific row"""
        
        # Find the test case
        test_case = None
        for case in self.test_cases:
            if case.row_id == row_id:
                test_case = case
                break
        
        if not test_case:
            raise ValueError(f"Test case with row_id {row_id} not found")
        
        # Update the test case
        test_case.process_id = process_id
        test_case.blob_path = blob_path
        test_case.result = result
    
    def save_updated_csv(self, output_path: str = None) -> str:
        """Save updated CSV file with test results"""
        
        if output_path is None:
            # Create output filename with timestamp
            base_name = self.csv_file_path.stem
            timestamp = str(uuid.uuid4())[:8]
            output_path = self.csv_file_path.parent / f"{base_name}_results_{timestamp}.csv"
        
        output_path = Path(output_path)
        
        # Determine fieldnames for output
        output_fieldnames = ['row_id', 'test_content', 'process_id', 'blob_path', 'result']
        
        # Add any additional fields from original CSV
        for field in self.fieldnames:
            if field not in output_fieldnames:
                output_fieldnames.append(field)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=output_fieldnames)
            writer.writeheader()
            
            for test_case in self.test_cases:
                row_data = {
                    'row_id': test_case.row_id,
                    'test_content': test_case.test_content,
                    'process_id': test_case.process_id or '',
                    'blob_path': test_case.blob_path or '',
                    'result': test_case.result or ''
                }
                writer.writerow(row_data)
        
        return str(output_path)
    
    def get_test_summary(self) -> Dict[str, Any]:
        """Get summary statistics of test cases"""
        
        total_tests = len(self.test_cases)
        completed_tests = len([case for case in self.test_cases if case.result])
        passed_tests = len([case for case in self.test_cases if case.result == 'passed'])
        failed_tests = len([case for case in self.test_cases if case.result == 'failed'])
        
        return {
            'total_tests': total_tests,
            'completed_tests': completed_tests,
            'pending_tests': total_tests - completed_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'pass_rate': (passed_tests / completed_tests * 100) if completed_tests > 0 else 0
        }
    
    @classmethod
    def validate_csv_file_path(cls, csv_file_path: str) -> bool:
        """Validate that the CSV file exists and is accessible"""
        csv_path = Path(csv_file_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_file_path}")
        if not csv_path.is_file():
            raise ValueError(f"Path is not a file: {csv_file_path}")
        return True
    
    def validate_csv_format(self) -> List[str]:
        """Validate CSV format and return any issues"""
        issues = []
        
        # Check for required columns
        if 'test_content' not in self.fieldnames:
            issues.append("Missing required 'test_content' column")
        
        # Check for empty test_content
        empty_content_rows = []
        for case in self.test_cases:
            if not case.test_content.strip():
                empty_content_rows.append(case.row_id)
        
        if empty_content_rows:
            issues.append(f"Rows with empty test_content: {empty_content_rows}")
        
        # Check for duplicate content
        content_counts = {}
        for case in self.test_cases:
            content = case.test_content.strip().lower()
            if content in content_counts:
                content_counts[content].append(case.row_id)
            else:
                content_counts[content] = [case.row_id]
        
        duplicates = {content: rows for content, rows in content_counts.items() if len(rows) > 1}
        if duplicates:
            issues.append(f"Duplicate test_content found: {duplicates}")
        
        return issues
