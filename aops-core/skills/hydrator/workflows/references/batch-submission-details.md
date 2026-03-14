# External Batch Submission Details

Detailed procedures for tool selection and management of external batch prediction jobs.

## Tool Selection Criteria

Select the appropriate tool based on the target API and job requirements:

- **LiteLLM**: For cross-provider LLM batch jobs (OpenAI, Anthropic, etc.)
- **Boto3 (Sagemaker)**: For AWS-native batch transforms
- **Custom Scripts**: For APIs requiring specialized authentication or data formats

## Batch Management

### Data Preparation

- Ensure input files are correctly formatted (e.g., JSONL for LiteLLM).
- Validate data against the target schema.
- Upload to a secure storage location (e.g., S3) if required.

### Job Submission

- Use the selected tool to submit the job.
- Capture the Job ID and record it in the task body.

### Status Monitoring

- Poll the job status at appropriate intervals.
- Update the task progress with the current job state (Pending, Processing, Completed, Failed).

### Output Retrieval

- Download results after job completion.
- Verify output completeness and format.
- Store results in the designated project directory.
