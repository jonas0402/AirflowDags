"""
TransferMkt Smart Workflow DAG

This Airflow DAG orchestrates a complete ETL pipeline for TransferMkt football data.
It implements a smart, watermark-based incremental loading system that:
- Extracts data from TransferMkt using Docker containers
- Transforms raw data into analytics-ready format
- Loads data to final destination (e.g., S3, database)
- Monitors data completeness and quality

Schedule: Every Saturday at 2:00 PM UTC
Author: Airflow
Tags: transfermkt, smart, watermark
"""

from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator
from datetime import datetime
from airflow.hooks.base import BaseHook

# Fetch AWS credentials from Airflow connection
# These credentials are passed to Docker containers as environment variables
aws_conn = BaseHook.get_connection('aws_default')

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 2,  # Increased retries since we have smart recovery
}

def slack_notify(context, status):
    """
    Send detailed Slack notifications for Airflow task status updates.

    This callback function is triggered on task success or failure and sends
    a formatted message to Slack with execution details, duration, and logs.

    Args:
        context (dict): Airflow context dictionary containing task instance,
                       DAG, execution date, and other runtime information.
        status (str): Task status - either "SUCCESS" or "FAILURE".

    Returns:
        None: Executes the SlackWebhookOperator to send the notification.

    Notification includes:
        - DAG and task identification
        - Execution date and timestamp
        - Task status (SUCCESS/FAILURE)
        - Retry attempt number
        - Execution duration
        - Link to task logs
        - Exception details (for failures)
    """
    ti = context.get("task_instance")
    dag = context.get("dag")
    execution_date = context.get("execution_date")
    
    # Calculate duration if possible
    duration = "N/A"
    if ti and ti.start_date and ti.end_date:
        duration_seconds = (ti.end_date - ti.start_date).total_seconds()
        duration = f"{duration_seconds:.1f} seconds"
    
    # Get log URL if available
    log_url = ti.log_url if ti else "N/A"
    
    # Get try number
    try_number = ti.try_number if ti else "N/A"
    
    # Capture exception message if available (for failures)
    exception_msg = context.get("exception", "")
    
    slack_msg = f"""
*DAG:* {dag.dag_id if dag else 'N/A'}
*Task:* {ti.task_id if ti else 'N/A'}
*Execution Date:* {execution_date}
*Status:* {status}
*Try Number:* {try_number}
*Duration:* {duration}
*Log URL:* {log_url}
"""
    if status == "FAILURE" and exception_msg:
        slack_msg += f"\n*Exception:* {exception_msg}"
    
    SlackWebhookOperator(
        task_id=f"slack_notify_{status.lower()}",
        http_conn_id="slack_webhook",
        message=slack_msg,
        channel="#general",
        username="Airflow",
    ).execute(context=context)

with DAG(
    'transfermkt_smart_workflow',
    default_args=default_args,
    description='Smart TransferMkt workflow with watermark-based incremental loading',
    schedule_interval='0 14 * * 6',  # Every Saturday at 2:00 PM UTC
    start_date=datetime(2024, 12, 6),
    catchup=False,  # Don't backfill historical runs
    tags=['transfermkt', 'smart', 'watermark'],
) as dag:

    # Task 1: Smart Data Loading
    # ------------------------------
    # Implements intelligent, watermark-based incremental data extraction.
    # - Checks watermark table to identify missing data sources for the execution date
    # - Only fetches data that hasn't been successfully loaded before
    # - Prevents redundant API calls and reduces execution time
    # - Passes execution date ({{ ds }}) to track which data period to load
    smart_data_loading = DockerOperator(
        task_id='smart_data_loading',
        image='jonasandata/transfermkt_app:latest',
        command="python /app/smart_transfer_mkt_loader.py {{ ds }}",  # {{ ds }} = YYYY-MM-DD execution date
        docker_url='unix://var/run/docker.sock',
        network_mode='bridge',
        auto_remove=True,  # Remove container after completion to save disk space
        mount_tmp_dir=False,
        force_pull=True,  # Always pull latest image to ensure code is up-to-date
        environment={
            'AWS_ACCESS_KEY_ID': aws_conn.login,
            'AWS_SECRET_ACCESS_KEY': aws_conn.password,
        },
        api_version='auto',
        docker_conn_id="docker_registry",
        on_success_callback=lambda context: slack_notify(context, "SUCCESS"),
        on_failure_callback=lambda context: slack_notify(context, "FAILURE"),
    )

    # Task 2: Data Transformation
    # ----------------------------
    # Transforms raw TransferMkt data into analytics-ready format.
    # - Cleans and standardizes player, club, and transfer data
    # - Handles data type conversions and null values
    # - Applies business logic and data quality rules
    # - Processes transfer records with enhanced logic for accurate tracking
    # - Outputs transformed data ready for loading to final destination
    run_transform_script = DockerOperator(
        task_id='run_transform_script',
        image='jonasandata/transfermkt_app:latest',
        command="python /app/transfer_mkt_transform.py",
        docker_url='unix://var/run/docker.sock',
        network_mode='bridge',
        auto_remove=True,
        mount_tmp_dir=False,
        force_pull=True,
        environment={
            'AWS_ACCESS_KEY_ID': aws_conn.login,
            'AWS_SECRET_ACCESS_KEY': aws_conn.password,
        },
        api_version='auto',
        docker_conn_id="docker_registry",
        on_success_callback=lambda context: slack_notify(context, "SUCCESS"),
        on_failure_callback=lambda context: slack_notify(context, "FAILURE"),
    )

    # Task 3: Data Loading
    # ---------------------
    # Loads transformed data to the final destination storage.
    # - Writes processed data to S3, database, or data warehouse
    # - Handles upsert logic to prevent duplicates
    # - Updates watermark table to mark successful data loads
    # - Ensures data is available for downstream analytics and reporting
    run_loader_script = DockerOperator(
        task_id='run_loader_script',
        image='jonasandata/transfermkt_app:latest',
        command="python /app/transfer_mkt_loader.py",
        docker_url='unix://var/run/docker.sock',
        network_mode='bridge',
        auto_remove=True,
        mount_tmp_dir=False,
        force_pull=True,
        environment={
            'AWS_ACCESS_KEY_ID': aws_conn.login,
            'AWS_SECRET_ACCESS_KEY': aws_conn.password,
        },
        api_version='auto',
        docker_conn_id="docker_registry",
        on_success_callback=lambda context: slack_notify(context, "SUCCESS"),
        on_failure_callback=lambda context: slack_notify(context, "FAILURE"),
    )

    # Task 4: Data Completeness Report
    # ---------------------------------
    # Generates a comprehensive data quality and completeness report.
    # - Queries watermark table to check which data sources were loaded
    # - Identifies any missing or incomplete data for the execution date
    # - Outputs JSON report with detailed status for each data source
    # - Useful for monitoring pipeline health and data coverage
    # - Runs regardless of upstream task status (trigger_rule='all_done')
    #   to ensure we always get visibility into data state
    generate_completeness_report = DockerOperator(
        task_id='generate_completeness_report',
        image='jonasandata/transfermkt_app:latest',
        command="""python -c "
from transfermkt.watermark_utils import WatermarkManager
from transfermkt.logger import setup_logging
import sys
import json

setup_logging()
wm = WatermarkManager()
date = sys.argv[1] if len(sys.argv) > 1 else '{{ ds }}'
report = wm.get_data_completeness_report(date)
print('=== DATA COMPLETENESS REPORT ===')
print(json.dumps(report, indent=2, default=str))
" {{ ds }}""",
        docker_url='unix://var/run/docker.sock',
        network_mode='bridge',
        auto_remove=True,
        mount_tmp_dir=False,
        force_pull=True,
        environment={
            'AWS_ACCESS_KEY_ID': aws_conn.login,
            'AWS_SECRET_ACCESS_KEY': aws_conn.password,
        },
        api_version='auto',
        docker_conn_id="docker_registry",
        trigger_rule='all_done',  # Run even if upstream tasks fail
    )

    # Define task dependencies (linear pipeline flow)
    # smart_data_loading: Extract raw data from TransferMkt
    #   ↓
    # run_transform_script: Transform and clean the data
    #   ↓
    # run_loader_script: Load to final destination
    #   ↓
    # generate_completeness_report: Monitor data quality
    smart_data_loading >> run_transform_script >> run_loader_script >> generate_completeness_report
