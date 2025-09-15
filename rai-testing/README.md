# RAI Testing Framework for Container Migration Solution

## Overview

This framework provides comprehensive Responsible AI (RAI) testing capabilities for the Container Migration Solution Accelerator. It tests the multi-agent system's response to potentially harmful, malicious, or inappropriate content embedded within Kubernetes configuration files.

## Architecture

The RAI testing framework follows the same pattern as the main application:

1. **Test Content Generation**: Creates YAML files with embedded harmful content
2. **Blob Storage Upload**: Uploads test files to Azure Storage Blob with unique GUID folder names
3. **Queue Message Trigger**: Sends messages to Azure Storage Queue to initiate processing
4. **Agent Response Monitoring**: Tracks how the AI agents handle the malicious content
5. **Results Analysis**: Provides comprehensive reporting on RAI compliance

## Directory Structure

```
rai-testing/
├── README.md                 # This documentation
├── config.py                # Configuration settings
├── requirements.txt         # Python dependencies
├── run_rai_tests.py        # Main test execution script
├── test-cases/             # Test case definitions
│   ├── harmful_content.py  # Harmful content patterns
│   └── test_scenarios.py   # Test scenario configurations
├── utils/                  # Utility modules
│   ├── __init__.py
│   ├── yaml_generator.py   # YAML file generation utilities
│   ├── blob_helper.py      # Azure Blob Storage operations
│   ├── queue_helper.py     # Azure Storage Queue operations
│   └── monitoring.py       # Test execution monitoring
└── results/                # Test results and reports
    └── (generated at runtime)
```

## Test Categories

### 1. Content Safety Tests
- Hate speech detection
- Violence and harm prevention
- Discriminatory language identification
- Harassment and bullying content

### 2. Security Tests
- Malicious code injection attempts
- System vulnerability exploits
- Social engineering patterns
- Credential harvesting attempts

### 3. Legal Compliance Tests
- Copyright infringement content
- Privacy violation patterns
- Regulatory compliance violations
- Illegal activity promotion

### 4. Operational Safety Tests
- Resource exhaustion attempts
- Service disruption patterns
- Data corruption scenarios
- System overload triggers

## Usage

### Prerequisites

1. Azure Storage Account with appropriate permissions
2. Azure Storage Queue configured
3. Python 3.8+ environment
4. Required Azure credentials configured

### Configuration

1. Copy `config.example.py` to `config.py`
2. Update Azure Storage connection details
3. Configure test parameters and thresholds

### Running Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run all RAI tests
python run_rai_tests.py

# Run specific test category
python run_rai_tests.py --category content-safety

# Run with specific test count
python run_rai_tests.py --test-count 50

# Generate report only
python run_rai_tests.py --report-only
```

## Test Workflow

1. **Test Case Selection**: Framework selects test cases from defined categories
2. **File Generation**: Creates Kubernetes YAML files with embedded test content
3. **Storage Upload**: Uploads files to blob storage with unique GUID folders
4. **Queue Triggering**: Sends process_id messages to trigger agent processing
5. **Response Monitoring**: Tracks agent responses and processing results
6. **Safety Validation**: Validates that harmful content is properly handled
7. **Report Generation**: Creates comprehensive compliance reports

## Monitoring and Alerting

The framework provides real-time monitoring of:

- Agent response patterns
- Content filtering effectiveness
- Processing time anomalies
- Error handling consistency
- Safety measure activation

## Compliance Reporting

Generated reports include:

- Test execution summary
- Safety measure effectiveness
- Agent response analysis
- Compliance violation alerts
- Improvement recommendations

## Best Practices

1. **Isolated Testing**: Run RAI tests in isolated environments
2. **Regular Execution**: Schedule regular RAI testing cycles
3. **Content Updates**: Keep harmful content patterns up-to-date
4. **Response Analysis**: Regularly analyze agent response patterns
5. **Threshold Monitoring**: Monitor and adjust safety thresholds

## Security Considerations

- Test content is designed for safety validation only
- All harmful content is synthetic and controlled
- Test environments should be isolated from production
- Results should be securely stored and access-controlled
- Regular security reviews of test framework components

## Contributing

When adding new test cases:

1. Follow the established pattern in `test-cases/`
2. Ensure content is appropriate for testing purposes
3. Document the expected behavior and validation criteria
4. Test the framework with your additions before committing

## Support

For questions or issues with the RAI testing framework:

1. Check existing documentation and examples
2. Review the main application architecture
3. Consult the troubleshooting guide
4. Contact the development team for assistance
