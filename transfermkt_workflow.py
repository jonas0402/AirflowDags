from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator
from datetime import datetime
from airflow.hooks.base import BaseHook

# Fetch AWS credentials from Airflow connection
aws_conn = BaseHook.get_connection('aws_default')

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 2,  # Increased retries since we have smart recovery
}

def slack_notify(context, status):
    """Send Slack notifications for task status with additional details."""
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
    schedule_interval='0 14 * * 6',  # Every Saturday at 2:00 PM
    start_date=datetime(2024, 12, 6),
    catchup=False,
    tags=['transfermkt', 'smart', 'watermark'],
) as dag:

    # Task 1: Smart data loading (replaces the old players script)
    # This will check what's missing and only fetch those data sources
    smart_data_loading = DockerOperator(
        task_id='smart_data_loading',
        image='jonasandata/transfermkt_app:latest',
        command="python /app/smart_transfer_mkt_loader.py {{ ds }}",  # Pass execution date
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

    # Task 2: Data transformation (with fixed transfers processing)
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

    # Task 3: Data loading to final destination
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

    # Task 4: Generate completeness report (optional but useful for monitoring)
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
        trigger_rule='all_done',  # Run regardless of upstream success/failure
    )

    # Define task dependencies
    smart_data_loading >> run_transform_script >> run_loader_script >> generate_completeness_report
