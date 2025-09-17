# Transparency

The Container Migration GSA leverages AI agents as the main focus for the solution; however, it does not have a traditional "chat" interface or equivalent "user text in, AI generated content out" process. There is no "endpoint" to send user text and receive a response that indicates an RAI pass or fail.

## Overview
 
Instead this application has complex layers and a background processing unit that leverages the AI agent work. The frontend application calls an API that places a message on a queue for the background processing unit to pull and start working. The user does not directly input text that is sent to an AI agent; instead, the input comes in the form of uploading YAML files to the solution which are then placed in blob storage. The background processing unit then utilizes MCP server and AI Agents to pull those files down for processing. The output is then a new collection of files for the user to download.  This processing unit periodically saves status updates to a Cosmos DB that is polled from the frontend to provide a UX that shows the end user processing is happening behind the scenes. 

## RAI
 
The RAI component of the solution exists in the prompt for the initializing agent. That agent is in charge of assessing each file that has been uploaded to determine if it's valid and part of the prompt includes explicit instructions to reject malicious things. That agent terminates the process when this happens.
 
## Automation

In order to streamline testing RAI with this application architecture, the testing process will automate the following steps:

1. User provides malicious input text (the test)
2. Text is piped to a YAML file that mirrors traditional Kubernetes manifest file
3. YAML file is uploaded to blob storage
4. Message is placed on a queue for the background process to start
5. CosmosDB is polled periodically checking for status updates
6. Once process is determined to have failed, test is marked as passed.
7. If process succeeds, the test is marked as failed.

## Testing Flexibility

Two testing options exist for the end user:

1. Command to execute a single test
2. Command to execute a batch of tests via reading and updating a CSV file

This automation takes all the pieces the user will have to do via the front end and streamline them via a command and quick assessment of the results.