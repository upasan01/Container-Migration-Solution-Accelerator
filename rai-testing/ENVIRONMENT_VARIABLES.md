# Environment Variables Reference

This file documents all environment variables used by the RAI Testing Framework.

## Required Variables

You must set **ONE** of these variables for Azure Storage authentication:

### STORAGE_ACCOUNT_NAME
```bash
export STORAGE_ACCOUNT_NAME="yourstorageaccount"
```
**Recommended for production.** Uses Azure AD authentication (managed identity, Azure CLI, or service principal).

### AZURE_STORAGE_CONNECTION_STRING  
```bash
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=youraccount;AccountKey=yourkey;EndpointSuffix=core.windows.net"
```
**For development only.** Contains storage account credentials directly.

---

## Optional Configuration Variables

### Test Execution Settings

#### RAI_TEST_COUNT
```bash
export RAI_TEST_COUNT=25
```
**Default:** 25  
**Description:** Maximum number of test cases to execute in a single run.

#### RAI_TEST_TIMEOUT
```bash
export RAI_TEST_TIMEOUT=60
```
**Default:** 60  
**Description:** Test execution timeout in minutes.

#### RAI_MAX_CONCURRENT
```bash
export RAI_MAX_CONCURRENT=5
```
**Default:** 5  
**Description:** Maximum number of concurrent test executions.

### Azure Storage Configuration

#### RAI_BLOB_CONTAINER
```bash
export RAI_BLOB_CONTAINER="processes"
```
**Default:** processes  
**Description:** Azure Blob Storage container name (must match main application).

#### RAI_QUEUE_NAME
```bash
export RAI_QUEUE_NAME="processes-queue"
```
**Default:** processes-queue  
**Description:** Azure Storage Queue name for triggering processing.

#### RAI_DLQ_NAME
```bash
export RAI_DLQ_NAME="processes-queue-dead-letter"
```
**Default:** {RAI_QUEUE_NAME}-dead-letter  
**Description:** Dead letter queue name for failed messages.

### Folder Structure

#### RAI_SOURCE_FOLDER
```bash
export RAI_SOURCE_FOLDER="source"
```
**Default:** source  
**Description:** Folder name for source test files in blob storage.

#### RAI_WORKSPACE_FOLDER
```bash
export RAI_WORKSPACE_FOLDER="workspace"
```
**Default:** workspace  
**Description:** Folder name for workspace files in blob storage.

#### RAI_OUTPUT_FOLDER
```bash
export RAI_OUTPUT_FOLDER="converted"
```
**Default:** converted  
**Description:** Folder name for output files in blob storage.

### Monitoring and Results

#### RAI_POLLING_INTERVAL
```bash
export RAI_POLLING_INTERVAL=30
```
**Default:** 30  
**Description:** Polling interval in seconds for monitoring test execution.

#### RAI_MAX_WAIT_TIME
```bash
export RAI_MAX_WAIT_TIME=60
```
**Default:** 60  
**Description:** Maximum wait time in minutes for test completion.

#### RAI_RESULTS_DIR
```bash
export RAI_RESULTS_DIR="results"
```
**Default:** results  
**Description:** Directory for storing test results and reports.

#### RAI_REPORT_FORMAT
```bash
export RAI_REPORT_FORMAT="json"
```
**Default:** json  
**Options:** json, csv, html  
**Description:** Output format for test reports.

### Safety Configuration

#### RAI_MAX_PROCESSING_TIME
```bash
export RAI_MAX_PROCESSING_TIME=45
```
**Default:** 45  
**Description:** Maximum expected processing time in minutes before flagging as potential issue.

#### RAI_SAFETY_PATTERNS
```bash
export RAI_SAFETY_PATTERNS="content safety,inappropriate content,policy violation,harmful content,content filtered"
```
**Default:** content safety,inappropriate content,policy violation,harmful content,content filtered  
**Description:** Comma-separated list of keywords that indicate safety measures were triggered.

---

## Example .env File

Create a `.env` file in the rai-testing directory:

```bash
# Required: Azure Storage Authentication
STORAGE_ACCOUNT_NAME=mycompanystorage

# Optional: Test Configuration  
RAI_TEST_COUNT=50
RAI_TEST_TIMEOUT=90
RAI_MAX_CONCURRENT=10

# Optional: Custom Container/Queue Names
RAI_BLOB_CONTAINER=my-test-container
RAI_QUEUE_NAME=my-test-queue

# Optional: Safety Patterns (add your application-specific keywords)
RAI_SAFETY_PATTERNS="content safety,policy violation,harmful content,security violation,blocked content"

# Optional: Results Configuration
RAI_RESULTS_DIR=test-results
RAI_REPORT_FORMAT=html
```

Then load it before running tests:
```bash
# Load environment variables from .env file
source .env

# Or use python-dotenv (already included in requirements.txt)
python run_rai_tests.py  # Will automatically load .env if present
```

---

## Security Best Practices

1. **Never commit connection strings** to version control
2. **Use managed identities** in production environments
3. **Rotate storage account keys** regularly if using connection strings
4. **Limit storage account permissions** to minimum required (Storage Blob Data Contributor, Storage Queue Data Contributor)
5. **Use Azure Key Vault** for storing sensitive configuration in production
