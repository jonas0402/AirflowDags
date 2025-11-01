# Configuration Guide

This document provides detailed configuration instructions for the TransferMkt Airflow DAG.

## Table of Contents

1. [Airflow Connections](#airflow-connections)
2. [Environment Variables](#environment-variables)
3. [Docker Configuration](#docker-configuration)
4. [DAG Parameters](#dag-parameters)
5. [Slack Notification Setup](#slack-notification-setup)

## Airflow Connections

### 1. AWS Default Connection

The `aws_default` connection provides AWS credentials for S3 access and other AWS services.

#### Via Airflow UI:

1. Navigate to **Admin → Connections**
2. Click **+** to add a new connection
3. Configure:
   - **Connection Id**: `aws_default`
   - **Connection Type**: `Amazon Web Services`
   - **AWS Access Key ID**: Your AWS access key
   - **AWS Secret Access Key**: Your AWS secret key
   - **Extra** (optional): JSON with additional AWS config
     ```json
     {
       "region_name": "us-east-1"
     }
     ```

#### Via Airflow CLI:

```bash
airflow connections add aws_default \
  --conn-type aws \
  --conn-login YOUR_AWS_ACCESS_KEY_ID \
  --conn-password YOUR_AWS_SECRET_ACCESS_KEY \
  --conn-extra '{"region_name": "us-east-1"}'
```

#### Via Environment Variable:

```bash
export AIRFLOW_CONN_AWS_DEFAULT='aws://YOUR_ACCESS_KEY:YOUR_SECRET_KEY@'
```

### 2. Slack Webhook Connection

The `slack_webhook` connection enables Slack notifications for task status updates.

#### Get Slack Webhook URL:

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps)
2. Create a new app or select existing app
3. Navigate to **Incoming Webhooks**
4. Activate Incoming Webhooks
5. Add New Webhook to Workspace
6. Select channel (e.g., #general)
7. Copy the webhook URL

#### Configure in Airflow UI:

1. Navigate to **Admin → Connections**
2. Click **+** to add a new connection
3. Configure:
   - **Connection Id**: `slack_webhook`
   - **Connection Type**: `HTTP`
   - **Host**: `https://hooks.slack.com/services/YOUR/WEBHOOK/URL`
   - **Schema**: `https`

#### Via Airflow CLI:

```bash
airflow connections add slack_webhook \
  --conn-type http \
  --conn-host 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
```

### 3. Docker Registry Connection

The `docker_registry` connection allows Airflow to authenticate with Docker registries.

#### For Public Docker Hub:

```bash
airflow connections add docker_registry \
  --conn-type docker
```

#### For Private Docker Registry:

```bash
airflow connections add docker_registry \
  --conn-type docker \
  --conn-login YOUR_DOCKER_USERNAME \
  --conn-password YOUR_DOCKER_PASSWORD \
  --conn-host registry.example.com
```

## Environment Variables

### Docker Container Environment

The following environment variables are passed to Docker containers:

- **AWS_ACCESS_KEY_ID**: Extracted from `aws_default` connection
- **AWS_SECRET_ACCESS_KEY**: Extracted from `aws_default` connection

### Optional Environment Variables

Add to Docker operator's `environment` parameter if needed:

```python
environment={
    'AWS_ACCESS_KEY_ID': aws_conn.login,
    'AWS_SECRET_ACCESS_KEY': aws_conn.password,
    'AWS_REGION': 'us-east-1',
    'S3_BUCKET': 'your-bucket-name',
    'LOG_LEVEL': 'INFO',
}
```

## Docker Configuration

### Docker Socket Access

Ensure Airflow has permission to access the Docker socket:

```bash
# Add airflow user to docker group
sudo usermod -aG docker airflow

# Verify permissions
ls -la /var/run/docker.sock

# Should show something like:
# srw-rw---- 1 root docker 0 Nov  1 12:00 /var/run/docker.sock
```

### Docker Image Pull Policy

The DAG uses `force_pull=True` to always pull the latest image. To change this behavior:

```python
smart_data_loading = DockerOperator(
    # ...
    force_pull=False,  # Use cached image if available
    # ...
)
```

### Docker Network Configuration

Current configuration uses `bridge` network mode. Alternative options:

```python
network_mode='host'        # Use host network
network_mode='none'        # No networking
network_mode='my_network'  # Custom Docker network
```

## DAG Parameters

### Schedule Configuration

Modify the schedule interval in the DAG definition:

```python
with DAG(
    'transfermkt_smart_workflow',
    schedule_interval='0 14 * * 6',  # Cron expression
    # ...
)
```

**Common Schedule Examples:**

- Daily at 2 AM: `'0 2 * * *'`
- Every hour: `'0 * * * *'`
- Every Monday at 8 AM: `'0 8 * * 1'`
- First day of month: `'0 0 1 * *'`
- None (manual only): `None`

### Retry Configuration

Adjust retry behavior in `default_args`:

```python
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),  # Wait 5 minutes between retries
    'retry_exponential_backoff': True,     # Exponential backoff
    'max_retry_delay': timedelta(minutes=30),
}
```

### Execution Timeout

Add timeout to prevent tasks from running indefinitely:

```python
from datetime import timedelta

smart_data_loading = DockerOperator(
    # ...
    execution_timeout=timedelta(hours=2),  # Kill task after 2 hours
    # ...
)
```

### Email Notifications

Add email alerts in addition to Slack:

```python
default_args = {
    # ...
    'email': ['your-email@example.com'],
    'email_on_failure': True,
    'email_on_retry': True,
    'email_on_success': False,
}
```

## Slack Notification Setup

### Customize Notification Channel

Change the Slack channel in `transfermkt_workflow.py:91`:

```python
SlackWebhookOperator(
    task_id=f"slack_notify_{status.lower()}",
    http_conn_id="slack_webhook",
    message=slack_msg,
    channel="#your-channel",  # Change this
    username="Airflow",
).execute(context=context)
```

### Customize Notification Format

Modify the `slack_notify` function to change message format:

```python
slack_msg = f"""
:rocket: *DAG Status Update*
*DAG:* {dag.dag_id if dag else 'N/A'}
*Task:* {ti.task_id if ti else 'N/A'}
*Status:* {':white_check_mark:' if status == 'SUCCESS' else ':x:'} {status}
*Execution Date:* {execution_date}
*Duration:* {duration}
"""
```

### Disable Slack Notifications

To disable Slack notifications for specific tasks:

```python
smart_data_loading = DockerOperator(
    # ...
    # Remove or comment out these lines:
    # on_success_callback=lambda context: slack_notify(context, "SUCCESS"),
    # on_failure_callback=lambda context: slack_notify(context, "FAILURE"),
)
```

## Advanced Configuration

### SLA (Service Level Agreement)

Set SLA to receive alerts if tasks take too long:

```python
default_args = {
    # ...
    'sla': timedelta(hours=1),  # Alert if task takes > 1 hour
}
```

### Task Concurrency

Limit concurrent task instances:

```python
smart_data_loading = DockerOperator(
    # ...
    max_active_tis_per_dag=1,  # Only 1 instance of this task at a time
)
```

### Pool Configuration

Use Airflow pools to limit resource usage:

```bash
# Create a pool
airflow pools set docker_pool 3 "Pool for Docker tasks"
```

```python
smart_data_loading = DockerOperator(
    # ...
    pool='docker_pool',
)
```

## Verification

### Test Connection

Test Airflow connections:

```bash
# Test AWS connection
airflow connections test aws_default

# Test Slack connection
airflow connections test slack_webhook
```

### Test DAG

Run the DAG in test mode:

```bash
# Test the entire DAG
airflow dags test transfermkt_smart_workflow $(date +%Y-%m-%d)

# Test individual task
airflow tasks test transfermkt_smart_workflow smart_data_loading $(date +%Y-%m-%d)
```

### Validate DAG

Check for configuration errors:

```bash
# Validate DAG syntax
python $AIRFLOW_HOME/dags/transfermkt_workflow.py

# List DAGs
airflow dags list

# Show DAG details
airflow dags show transfermkt_smart_workflow
```

## Troubleshooting

### Docker Permission Issues

If you get "Permission denied" errors:

```bash
sudo chmod 666 /var/run/docker.sock
```

### Connection Not Found

If Airflow can't find connections:

```bash
# List all connections
airflow connections list

# Export connections
airflow connections export connections.json
```

### Image Pull Failures

If Docker can't pull images:

```bash
# Login to Docker registry
docker login

# Manually pull image
docker pull jonasandata/transfermkt_app:latest

# Check disk space
df -h
```
