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
    'retries': 1,
}

def slack_notify(context, status):
    """Send Slack notifications for task status."""
    slack_msg = f"""
    *DAG*: {context['dag'].dag_id}
    *Task*: {context['task_instance'].task_id}
    *Execution Date*: {context['execution_date']}
    *Status*: {status}
    """
    SlackWebhookOperator(
        task_id=f"slack_notify_{status.lower()}",
        http_conn_id="slack_webhook",  # Ensure this matches your Slack Webhook connection ID
        message=slack_msg,
        channel="#general",  # Update with your Slack channel
        username="Airflow",
    ).execute(context=context)

with DAG(
    'transfermkt_workflow',
    default_args=default_args,
    description='Run TransferMkt scripts in Docker containers',
    schedule_interval='0 14 * * 6',  # Every Saturday at 2:00 PM
    start_date=datetime(2024, 12, 6),
    catchup=False,
) as dag:

    # Task 1: Run transfer_mkt_players.py
    run_players_script = DockerOperator(
        task_id='run_players_script',
        image='jonasandata/transfermkt_app:latest',
        command="python /app/transfer_mkt_players.py",
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

    # Task 2: Run transfer_mkt_transform.py
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

    # Task 3: Run transfer_mkt_loader.py
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

    # Define task dependencies: players -> transform -> loader
    run_players_script >> run_transform_script >> run_loader_script
