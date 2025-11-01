# TransferMkt Airflow DAG

A smart, watermark-based data pipeline for extracting, transforming, and loading football transfer market data from TransferMkt.

## Overview

This project implements an Apache Airflow DAG that orchestrates a complete ETL pipeline for TransferMkt data. The pipeline uses Docker containers to execute data processing tasks and implements intelligent watermark-based incremental loading to efficiently process only new or missing data.

## Features

- **Smart Incremental Loading**: Watermark-based system ensures only new or missing data is processed
- **Dockerized Tasks**: All data processing runs in isolated Docker containers for consistency and reproducibility
- **Slack Notifications**: Real-time alerts for task success/failure with detailed execution metrics
- **Automatic Recovery**: Built-in retry mechanism (2 retries per task) for handling transient failures
- **Data Completeness Monitoring**: Automated reporting to track data pipeline health

## Architecture

### DAG Structure

```
smart_data_loading
    ↓
run_transform_script
    ↓
run_loader_script
    ↓
generate_completeness_report
```

### Tasks

1. **smart_data_loading**
   - Checks for missing data using watermark tracking
   - Fetches only required data sources
   - Runs: `smart_transfer_mkt_loader.py`

2. **run_transform_script**
   - Processes and transforms raw data
   - Handles transfer data processing
   - Runs: `transfer_mkt_transform.py`

3. **run_loader_script**
   - Loads transformed data to final destination
   - Runs: `transfer_mkt_loader.py`

4. **generate_completeness_report**
   - Generates data quality report
   - Runs regardless of upstream task status
   - Provides JSON-formatted completeness metrics

## Schedule

The DAG runs **every Saturday at 2:00 PM UTC** (`0 14 * * 6`).

## Prerequisites

### Airflow Connections

This DAG requires the following Airflow connections to be configured:

1. **aws_default** (Amazon Web Services)
   - Type: Amazon Web Services
   - AWS Access Key ID (login)
   - AWS Secret Access Key (password)
   - Used for: S3 storage and AWS service access

2. **slack_webhook** (Slack Incoming Webhook)
   - Type: HTTP
   - Host: Your Slack webhook URL
   - Used for: Task status notifications

3. **docker_registry** (Docker)
   - Type: Docker
   - Used for: Pulling Docker images from registry

### Docker Image

The pipeline uses the Docker image: `jonasandata/transfermkt_app:latest`

This image must contain:
- `/app/smart_transfer_mkt_loader.py`
- `/app/transfer_mkt_transform.py`
- `/app/transfer_mkt_loader.py`
- `transfermkt.watermark_utils` module
- `transfermkt.logger` module

### Airflow Providers

Required Airflow provider packages:
- `apache-airflow-providers-docker`
- `apache-airflow-providers-slack`

Install with:
```bash
pip install apache-airflow-providers-docker apache-airflow-providers-slack
```

## Configuration

### DAG Configuration

```python
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 2,
}
```

### Docker Configuration

- **Docker URL**: `unix://var/run/docker.sock`
- **Network Mode**: `bridge`
- **Auto Remove**: `True` (containers are removed after completion)
- **Force Pull**: `True` (always pulls latest image)

### Slack Notifications

Notifications are sent to `#general` channel and include:
- DAG and task names
- Execution date
- Status (SUCCESS/FAILURE)
- Try number
- Duration
- Log URL
- Exception details (on failure)

## Setup Instructions

1. **Copy the DAG file**
   ```bash
   cp transfermkt_workflow.py $AIRFLOW_HOME/dags/
   ```

2. **Configure Airflow connections** (via Airflow UI or CLI)
   ```bash
   # AWS credentials
   airflow connections add aws_default \
     --conn-type aws \
     --conn-login <YOUR_AWS_ACCESS_KEY> \
     --conn-password <YOUR_AWS_SECRET_KEY>

   # Slack webhook
   airflow connections add slack_webhook \
     --conn-type http \
     --conn-host <YOUR_SLACK_WEBHOOK_URL>

   # Docker registry
   airflow connections add docker_registry \
     --conn-type docker
   ```

3. **Verify Docker is accessible**
   ```bash
   docker ps
   ```

4. **Enable the DAG** in the Airflow UI

5. **Trigger a test run** (optional)
   ```bash
   airflow dags test transfermkt_smart_workflow $(date +%Y-%m-%d)
   ```

## Monitoring

### Airflow UI

Monitor DAG execution, task status, and logs through the Airflow web interface:
- DAG runs: `http://<airflow-host>:8080/dags/transfermkt_smart_workflow`
- Task logs: Available via the Graph or Tree view

### Slack Notifications

Real-time notifications are sent to your configured Slack channel for each task completion or failure.

### Completeness Reports

The final task generates a detailed JSON report showing:
- Data sources processed
- Watermark status
- Missing data gaps
- Overall pipeline health

## Troubleshooting

### Common Issues

**Task fails with "Docker connection refused"**
- Ensure Docker daemon is running
- Verify Airflow has permission to access `/var/run/docker.sock`
- Check `docker_registry` connection configuration

**AWS credentials error**
- Verify `aws_default` connection has correct credentials
- Check IAM permissions for S3 access

**Slack notifications not working**
- Verify `slack_webhook` connection URL is correct
- Check Slack workspace webhook is active
- Review Airflow task logs for specific errors

**Image pull failures**
- Verify Docker image `jonasandata/transfermkt_app:latest` exists
- Check network connectivity to Docker registry
- Ensure sufficient disk space for image

## Tags

- `transfermkt`
- `smart`
- `watermark`

## Version History

- Initial implementation with watermark-based smart loading
- Enhanced Slack notifications with detailed metrics
- Added data completeness reporting

## Contributing

When modifying this DAG:
1. Test changes locally using `airflow dags test`
2. Ensure all tasks have appropriate retry logic
3. Update Slack notification format if adding new context
4. Document any new configuration requirements

## License

[Add your license information here]

## Support

For issues or questions:
- Review Airflow task logs in the UI
- Check Docker container logs: `docker logs <container_id>`
- Consult the TransferMkt app documentation
